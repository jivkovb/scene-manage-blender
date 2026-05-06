# Scene Manager — Blender Add-on

A multi-setup render variant manager for Blender 4.2+, inspired by the workflow of Pulze Scene Manager for 3ds Max.

## What it does

Define multiple **Setups** inside a single `.blend` file. Each setup is a named bundle of:

| Module | What it controls |
|---|---|
| Camera | Active scene camera, optional focal-length/DOF override |
| Resolution | Width × height, percentage, pixel aspect |
| Output | File path (with token substitution), format, color mode |
| Frame Range | Single frame / range / explicit list |
| Engine | Cycles or EEVEE Next, samples, denoise, max bounces |
| Sun | Sun-light strength, rotation, optional mute of other lights |
| World / HDRI | Swap World datablock or load HDRI into environment node |
| Visibility | Per-collection hide-render / hide-viewport overrides |
| Color Mgmt | View transform, look, exposure, gamma |

Clicking **Activate Setup** applies all enabled modules to the scene in one step.
**Batch Render** iterates enabled setups, renders each one, then restores your original scene state.

## Installation

1. Download `scene_manager-0.1.0.zip`.
2. Open Blender → **Edit ▸ Preferences ▸ Add-ons ▸ Install…**
3. Select the zip file and enable **Scene Manager**.
4. Open the **N-Panel** (press `N` in the 3D Viewport) and click the **Scene Manager** tab.

## Quick start

1. Click **+** to add a setup.
2. Name it (e.g. `Hero_Day`).
3. Enable the Camera module, pick a camera.
4. Enable the Resolution module, set 1920 × 1080.
5. Set an output path: e.g. `//renders/{setup}/` — tokens are expanded at render time.
6. Click **Activate Setup** to apply immediately.
7. Add more setups for other shots/variants.
8. Click **Batch Render** to render them all.

## Output path tokens

| Token | Expands to |
|---|---|
| `{setup}` | Setup name (filesystem-safe) |
| `{camera}` | Active camera name |
| `{date}` | `YYYYMMDD` |
| `{time}` | `HHMMSS` |
| `{blend}` | `.blend` filename stem |
| `{frame}` | Current frame (zero-padded, 4 digits) |
| `{ext}` | File extension derived from format |
| `{view_layer}` | Active view layer name |

## Module behaviour

Each module has two toggles:

- **Use** (dot icon) — the module is part of this setup; data is never deleted when turned off.
- **Apply on Activate** (checkbox icon) — whether the module writes to the scene when activated.

This lets you temporarily disable a module without losing its stored values.

## Batch render

- Only **enabled** setups (checkbox in the list) are included.
- Press **Escape** to cancel — the current frame finishes, then the scene is restored.
- The scene is always restored to its pre-batch state, even if Blender crashes (via try/finally).
- Batch render refuses to start if any output path uses `//` and the file is unsaved.

## Running tests

```bash
blender --background --python scene_manager/tests/test_tokens.py
# or standalone:
python scene_manager/tests/test_tokens.py
```

## Phase roadmap

| Phase | Status |
|---|---|
| 1 — MVP (current) | ✅ shipped |
| 2 — Preview mode, thumbnails, JSON I/O, compositor, script | 🔜 |
| 3 — Color tags, sanity checker, asset collector, farm hooks | 🔜 |
