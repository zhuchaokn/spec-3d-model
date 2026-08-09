"""engine.py — spec-3d-model 构建引擎(纯调度器)。

读一份 JSON 注册表(常量 + 对象拓扑),做四件通用事,**不懂任何具体形状/操作**:
  1. 求值受限数学表达式(常量引用 + 四则/幂 + 白名单函数 sin/cos/sqrt...)
  2. resolve 坐标:沿 parent 链累加 offset → 绝对质心(绝对坐标从不存,只算)
  3. 拓扑排序:parent(坐标树) + target(装配/布尔 DAG)两种依赖边合并排序,检测环
  4. 逐节点组 ctx,调该节点 op 脚本的 run(ctx)

形状与操作全在 lib/ops/*.py。引擎词汇表只有:
  name / op / parent / offset / target / params  (其余字段透传)

用法(在 Blender 内,build 脚本里):
    from engine import run_model
    run_model("/abs/path/to/model.json")
"""
import ast
import json
import math
import os
import importlib.util


# ============ 1. 受限数学表达式求值 ============

# 允许的函数/常量(白名单)
_ALLOWED_FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "sqrt": math.sqrt, "abs": abs, "min": min, "max": max,
    "floor": math.floor, "ceil": math.ceil, "round": round,
    "radians": math.radians, "degrees": math.degrees,
}
_ALLOWED_CONSTS = {"pi": math.pi, "tau": math.tau, "e": math.e}


def _eval_ast(node, vars):
    """递归求值 AST,只允许数字/变量/四则/幂/一元负/白名单函数调用。"""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, vars)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"只允许数字常量,得到 {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in vars:
            return vars[node.id]
        if node.id in _ALLOWED_CONSTS:
            return _ALLOWED_CONSTS[node.id]
        raise ValueError(f"未知变量/常量: {node.id}")
    if isinstance(node, ast.BinOp):
        l, r = _eval_ast(node.left, vars), _eval_ast(node.right, vars)
        op = node.op
        if isinstance(op, ast.Add): return l + r
        if isinstance(op, ast.Sub): return l - r
        if isinstance(op, ast.Mult): return l * r
        if isinstance(op, ast.Div): return l / r
        if isinstance(op, ast.Pow): return l ** r
        if isinstance(op, ast.Mod): return l % r
        raise ValueError(f"不允许的运算符 {type(op).__name__}")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _eval_ast(node.operand, vars)
        return +v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise ValueError("只允许白名单函数调用")
        args = [_eval_ast(a, vars) for a in node.args]
        return _ALLOWED_FUNCS[node.func.id](*args)
    raise ValueError(f"不允许的表达式节点 {type(node).__name__}")


def evaluate(expr, vars):
    """求值一个表达式。数字原样返回;字符串按受限数学表达式解析。"""
    if isinstance(expr, (int, float)):
        return expr
    if isinstance(expr, str):
        return _eval_ast(ast.parse(expr, mode="eval"), vars)
    raise ValueError(f"无法求值 {expr!r}")


def eval_vec(vec, vars):
    """求值一个坐标/尺寸三元组(每个分量可为数字或表达式)。"""
    return tuple(evaluate(c, vars) for c in vec)


def resolve_constants(raw):
    """求值 constants 段。支持常量间引用(如 JOINT_R = JOINT_OD/2),按依赖顺序解析。"""
    resolved = {}
    pending = dict(raw)
    # 反复扫描:能算的先算,直到全部解析或卡住(循环引用)
    progress = True
    while pending and progress:
        progress = False
        for name in list(pending.keys()):
            try:
                resolved[name] = evaluate(pending[name], resolved)
                del pending[name]
                progress = True
            except ValueError:
                continue  # 依赖还没算出来,下一轮再试
    if pending:
        raise ValueError(f"常量无法解析(可能循环引用): {list(pending)}")
    return resolved


# ============ 2. 坐标 resolve ============

def resolve_center(node_name, nodes, vars, _cache=None):
    """沿 parent 链累加 offset → 绝对质心。记忆化。"""
    if _cache is None:
        _cache = {}
    if node_name in _cache:
        return _cache[node_name]
    n = nodes[node_name]
    off = eval_vec(n.get("offset", [0, 0, 0]), vars)
    parent = n.get("parent")
    if parent is None:
        center = off  # 根:offset 即绝对锚
    else:
        pc = resolve_center(parent, nodes, vars, _cache)
        center = (off[0] + pc[0], off[1] + pc[1], off[2] + pc[2])
    _cache[node_name] = center
    return center


# ============ 3. 拓扑排序(parent 树 + target DAG) ============

def topo_order(nodes):
    """合并 parent 与 target 两种依赖边,拓扑排序。返回节点名列表。检测环。"""
    # 依赖:parent(坐标)+ target(装配/布尔)+ after(纯排序,不注入 ctx)。
    # after 用于同一 target 上多个修改 op 的先后(如 cavity→hex→scallop→handle)。
    deps = {}
    for name, n in nodes.items():
        d = set()
        if n.get("parent"):
            d.add(n["parent"])
        for t in n.get("target", []) or []:
            d.add(t)
        for a in n.get("after", []) or []:
            d.add(a)
        deps[name] = d
    order, visiting, done = [], set(), set()

    def visit(name):
        if name in done:
            return
        if name in visiting:
            raise ValueError(f"依赖成环: {name}")
        visiting.add(name)
        for d in deps.get(name, ()):
            if d not in nodes:
                raise ValueError(f"{name} 依赖不存在的节点 {d}")
            visit(d)
        visiting.discard(name)
        done.add(name)
        order.append(name)

    for name in nodes:
        visit(name)
    return order


# ============ 4. 逐节点调度 op ============

def _load_op(op_path, base_dir):
    """加载 op 脚本模块(相对 base_dir 或绝对路径),返回其 run 函数。"""
    path = op_path if os.path.isabs(op_path) else os.path.join(base_dir, op_path)
    spec = importlib.util.spec_from_file_location(f"op_{os.path.basename(path)}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        raise ValueError(f"op 脚本缺少 run(ctx): {path}")
    return mod.run


class Ctx:
    """传给 op 脚本的上下文。op 只需读这些字段 + 用 s3d 原子。"""
    def __init__(self, node, center, params, targets):
        self.name = node["name"]
        self.node = node
        self.center = center        # 本节点绝对质心 (cm)
        self.params = params        # 已求值的参数 dict
        self.targets = targets      # { dep_name: {"object":obj, "center":c} }


def run_model(json_path, lib_dir=None):
    """主入口:读 JSON → 求值 → 拓扑排序 → 逐节点调 op。返回执行的节点名列表。"""
    lib_dir = lib_dir or os.path.dirname(os.path.abspath(__file__))
    with open(json_path, encoding="utf-8") as f:
        model = json.load(f)

    vars = resolve_constants(model.get("constants", {}))
    nodes = {n["name"]: n for n in model["nodes"]}
    order = topo_order(nodes)
    centers = {}
    built = []

    import bpy  # noqa: F401  仅施工阶段需要
    for name in order:
        n = nodes[name]
        center = resolve_center(name, nodes, vars, centers)
        op_path = n.get("op")
        if not op_path:
            continue  # 虚拟节点:无 op,只当参照系(坐标已 resolve)
        # 求值 params(每个值可为数字/表达式/三元组)
        params = {}
        for k, v in (n.get("params") or {}).items():
            if isinstance(v, list):
                params[k] = eval_vec(v, vars)
            elif isinstance(v, (int, float, str)):
                try:
                    params[k] = evaluate(v, vars)
                except (ValueError, SyntaxError):
                    params[k] = v  # 非表达式字符串(如面名"front")原样传
            else:
                params[k] = v
        # 收集 targets
        targets = {}
        for t in n.get("target", []) or []:
            targets[t] = {"object": bpy.data.objects.get(t),
                          "center": centers.get(t)}
        run = _load_op(op_path, lib_dir)
        run(Ctx(n, center, params, targets))
        built.append(name)
    return built
