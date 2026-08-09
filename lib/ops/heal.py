"""op: heal — 修网格(合并重复顶点+重算法线),修布尔/union 留下的非流形残边。

ctx.params: target_name(要修的对象), dist(可选,cm,默认0.001)。
在各半所有卡合件 union 完之后跑一次,消除缝处非流形边 → 水密可打印。
"""
import s3d


def run(ctx):
    name = ctx.params["target_name"]
    dist = ctx.params.get("dist", 0.001)
    s3d.heal(name, dist_cm=dist)
    d = s3d.manifold_report(name)
    # 边界边=真漏洞(必须0);非流形=柱穿墙的T形自交线(切片器可修,可容忍)
    ok = d["boundary"] == 0
    print(f"  [heal] {name} 边界边(漏洞)={d['boundary']} 非流形(T交线)={d['nonmanifold']} "
          f"{'✓无漏洞,切片器可修T交线' if ok else '✗有漏洞需修!'}")
