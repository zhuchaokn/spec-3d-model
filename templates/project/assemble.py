"""assemble.py — 按顺序逐个执行各组件 build.py,组合成完整成品。

原理:命名空间每次全新,组件间靠**场景里的具名对象**接力。本脚本按 ORDER
顺序把每个 build.py 读进来 exec,复用同一 Blender 会话的场景状态。
用法:execute_blender_code(file_path=此文件)。
"""
import os

PROJ = "/Users/zhuchao14/blender/projects/<name>"   # ← 改成本项目路径

# 组件构建顺序(相对 components/ 的目录名)
ORDER = [
    # "shell",
    # "honeycomb",
]


def run_component(part):
    path = os.path.join(PROJ, "components", part, "build.py")
    with open(path, encoding="utf-8") as f:
        code = f.read()
    ns = {"__name__": "__assembled__"}
    exec(compile(code, path, "exec"), ns)
    print(f"  [assembled] {part}")


def main():
    print(f"ASSEMBLE {PROJ} order={ORDER}")
    for part in ORDER:
        run_component(part)
    print(f"OK assembled {len(ORDER)} components")


main()
