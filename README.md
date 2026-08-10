<div align="center">

# spec-3d-model

**The discipline layer AI 3D modeling is missing.**

Spec-driven, parametric, data-verified geometry that's actually *watertight* and *printable* —
not another mesh blob that looks fine and prints broken.

</div>

---

## The problem

Everyone is racing to make AI *generate* 3D. The output is usually **unusable**:

- **Mesh generators** (Shap-E, DreamFusion, Rodin, Hunyuan3D, image-to-STL) give you a blob that *looks* right but is **non-manifold, not watertight, and impossible to edit**. A professional has to rebuild it from scratch.
- **Text-to-CAD / "vibe-CAD"** tools produce editable code, but openly admit their limits — "simple shapes only, the AI can't see the render, no self-correction yet" — and that **printability optimization is still on the backlog**.

The AI doesn't need to be smarter. **The geometry needs discipline.**

## What this is (and isn't)

spec-3d-model is **not** a "type a prompt, get a model" generator. It's an **engine + methodology**: you (or an AI agent) declare a model as **one JSON source of truth**, and a pure scheduling engine builds it in Blender — with the engineering discipline that makes parts *actually printable*:

- **One JSON = single source of truth.** Constants + object topology (size / parent / relative coords / which op builds it). Change a dimension in one place.
- **Data-verified, not eyeballed.** Every part is checked with `manifold_report` — the pass criterion is **boundary edges = 0** (truly watertight), not "looks closed."
- **Print-aware by construction.** Cutter-overhang discipline (no degenerate coplanar faces), FDM-friendly orientation (pointy-top hexes avoid horizontal bridging), keep-out bands around seams.
- **Auto-split for your print bed.** Parts larger than the bed (e.g. Bambu 256³mm) are split along the longest axis and rejoined with C-clip + pin snap-fits.

> It shines when you want a **functional part that actually prints**, not a pretty sculpture.

## How it compares

| | Mesh generators | vibe-CAD | **spec-3d-model** |
|---|---|---|---|
| Parametric / editable | ❌ black-box mesh | ✅ code | ✅ one JSON source of truth |
| Watertight / manifold check | ❌ | ❌ (eyeballed) | ✅ boundary edges = 0 |
| Printability-aware | ❌ | ❌ (on backlog) | ✅ overhang / keep-out / FDM |
| Auto-split for print bed | ❌ | ❌ | ✅ split + snap-fit joints |

## Quick start

**Prerequisites:** Blender ≥ 3.0, Python ≥ 3.10, [uv](https://github.com/astral-sh/uv).

1. **Install the Blender addon.** In Blender: *Edit > Preferences > Add-ons > Install...* and select `mcp/blender-mcp/addon.py`. Enable **"Interface: Blender MCP"**.
2. **Start the bridge.** In the 3D View sidebar (press `N`) → **BlenderMCP** tab → **Connect**.
3. **Point your MCP client at the bundled server** (see [`.mcp.json`](./.mcp.json)) and clone this repo.
4. **Build a model:**
   ```
   execute_blender_code(file_path="<repo>/projects/clip_tester/run_model.py")
   ```
   You'll see each part reported with `漏洞=0` (boundary edges = 0 → watertight), and STLs written to `projects/clip_tester/output/`.

No paths to configure — scripts locate themselves (see [Why we forked BlenderMCP](#why-we-forked-blendermcp)).

## Examples

| Project | What it demonstrates |
|---|---|
| [`projects/clip_tester`](./projects/clip_tester) | The smallest win: a snap-fit test coupon to dial in tolerances before committing to a full split. |
| [`projects/basket`](./projects/basket) | End-to-end: a 29×20×20cm bin, hex-cutout walls, split across the print bed and joined with C-clip + pin. |
| [`projects/basket_round`](./projects/basket_round) | A rounded variant — same JSON topology, different constants. |

New project? Copy [`templates/project`](./templates/project) and read [`lib/ENGINE.md`](./lib/ENGINE.md).

## How it works

```
projects/<name>/model.json  ──▶  engine.run_model()  ──▶  Blender scene + exported STL
```

- **`lib/engine.py`** — pure scheduler: evaluate expressions → resolve absolute coords → topological sort → call each op. Knows nothing about specific shapes.
- **`lib/s3d.py`** — business-free Blender atoms (boxes, booleans, coordinate helpers, diagnostics).
- **`lib/ops/*.py`** — one op = one "how to build" (box / subtract / frustum / mirror / export …).
- **`model.json`** — the only place project dimensions live.

Full manual: [`lib/ENGINE.md`](./lib/ENGINE.md).

## Credits — built on BlenderMCP

This project stands on the shoulders of **[BlenderMCP](https://github.com/MCPBlender/blender-mcp)** — the excellent bridge that connects Blender to any LLM over the Model Context Protocol. Without it, none of this exists; **it is the foundation this work is built on**, and we're grateful for it. If you find spec-3d-model useful, please go star BlenderMCP too.

### Why we forked BlenderMCP

We vendored a fork under [`mcp/blender-mcp`](./mcp/blender-mcp) for **one specific reason** — nothing is wrong with the upstream project:

Our whole approach is **multi-file engineering**. A model isn't one snippet — it's a run script that imports a shared engine and ops, plus a `model.json` source of truth: real files on disk that reference each other. Upstream BlenderMCP executes Python by taking the **code as a string inlined into the tool call**. That's a great fit for one-off scripts, but it can't express a project that lives across multiple files.

So we changed the code-execution tool to **take a file path instead of an inlined code string** — the server reads the script from disk and runs it. This is also far cheaper in tokens than pasting the whole engine into every call. One small follow-on: because Blender's `exec()` namespace has no `__file__`, we inject the script's resolved absolute path before execution, so every script can locate its own project/lib directories — **zero hardcoded paths**. We'd be happy to contribute this upstream.

## Contributing

New ops and new example projects are the most welcome contributions. See [CONTRIBUTING.md](./CONTRIBUTING.md) — it's short, and [`lib/ENGINE.md`](./lib/ENGINE.md) covers the mechanics.

## License

[MIT](./LICENSE). The vendored BlenderMCP fork under [`mcp/blender-mcp`](./mcp/blender-mcp) keeps its own upstream license.
