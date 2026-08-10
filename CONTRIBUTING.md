# Contributing to spec-3d-model

Thanks for your interest. The two most valuable contributions are **new ops** (reusable build logic) and **new example projects** (parts that prove the method). Both are small, self-contained, and reviewable.

First read [`lib/ENGINE.md`](./lib/ENGINE.md) — it's the engine manual and covers the mechanics this guide only points at.

## Setup

- Blender ≥ 3.0, Python ≥ 3.10, [uv](https://github.com/astral-sh/uv).
- Install the bundled addon (`mcp/blender-mcp/addon.py`) and connect (see [README](./README.md#quick-start)).
- Verify your setup by building an example — you should see `漏洞=0`:
  ```
  execute_blender_code(file_path="<repo>/projects/clip_tester/run_model.py")
  ```

## The two non-negotiables

1. **Data-verified, never eyeballed.** A part is correct only when `manifold_report` shows **boundary edges = 0** (watertight). Don't judge geometry by screenshots — verify with `scene_dump` / `manifold_report`. (Screenshots are for humans, and only when explicitly asked.)
2. **Honest positioning.** This is an *engine + methodology*, not a one-click generator. Keep docs and copy aligned with that — don't oversell.

## Adding a new op

An op is one file implementing `run(ctx)` — one "how to build" unit. Contract:

```python
def run(ctx):
    # ctx.name    : node name (= produced object name)
    # ctx.center  : absolute centroid (x,y,z) in cm (engine-resolved)
    # ctx.params  : evaluated params dict
    # ctx.targets : { dep_name: {"object": bpyObj, "center": (x,y,z)} }
    # ctx.proj_dir: project directory (for ops that write files)
```

- **Reusable & business-free** (chamfer, array, fillet …) → `lib/ops/<name>.py`, then add a row to [`lib/ops/README.md`](./lib/ops/README.md).
- **Encodes a specific product's intent** (e.g. a basket's hex array) → `projects/<name>/ops/`, not `lib/`.
- Use `s3d.py` atoms inside ops; keep dimensions out of `lib` (they belong in `model.json`).
- Mind the cutter rules in ENGINE.md §"常见坑" (cutters must overhang, order booleans with `after`).

## Adding an example project

1. Copy [`templates/project`](./templates/project) to `projects/<name>/`.
2. Write `spec/requirement.md`, then **hand-write** the orthographic three-view `spec/preview.html` — this is the design gate. Cheaper to fix HTML than 3D.
3. Fill `model.json`: constants + object topology (size / parent / relative coords / op). Reuse existing ops; write a new one only if needed.
4. Build with `run_model.py`, verify boundary edges = 0, export.
5. Keep paths relative — scripts self-locate via `__file__`; **never hardcode absolute paths.**

Small, printable, real-world parts make the best examples (hooks, holders, brackets).

## Pull requests

- One logical change per PR. Say what you built and paste the `manifold_report` (boundary edges = 0).
- Don't commit `output/` artifacts (STL/blend are gitignored); `screenshots/` may be committed.
- Be kind and specific in reviews. We compare to other tools *on the merits* — no trash talk.
