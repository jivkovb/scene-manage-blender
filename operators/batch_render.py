"""Batch render operator — renders all enabled setups in sequence.

Architecture:
  • SM_OT_BatchRender.execute() kicks off the queue and returns FINISHED immediately
    so no modal operator blocks the event loop.
  • A bpy.app.timers callback (_batch_tick) drives the queue at 0.2 s intervals.
  • Module-level _state dict holds all runtime state — no class-level mutable vars,
    no bound-method GC risk.
  • render_complete / render_cancel handlers use *args to survive across Blender
    versions that differ in whether depsgraph is passed.
"""

import bpy

from ..core.activation import apply_setup
from ..core.validators import check_setup


def _is_animation(scene, setup) -> bool:
    """Return True if this setup should use animation render, False for a single still.

    Checks the per-setup Frame Range module first (if active), then falls back
    to the universal frame_mode setting.
    """
    frame_mod = setup.frame_module
    if frame_mod.use and frame_mod.override:
        return frame_mod.mode in ("RANGE", "LIST")
    sm = getattr(scene, "scene_manager", None)
    if sm:
        return sm.settings.frame_mode in ("RANGE", "LIST")
    return scene.frame_start != scene.frame_end


# ---------------------------------------------------------------------------
# Module-level queue state
# ---------------------------------------------------------------------------

_state: dict = {}   # populated by SM_OT_BatchRender.execute()


# ---------------------------------------------------------------------------
# Render-event handlers  (module-level — safe from GC)
# ---------------------------------------------------------------------------

def _on_render_complete(scene, *args) -> None:
    _state["rendering"] = False
    _state["current"] += 1


def _on_render_cancel(scene, *args) -> None:
    _state["rendering"] = False
    # Jump past the queue to trigger cleanup on the next tick.
    _state["current"] = len(_state.get("indices", []))


# ---------------------------------------------------------------------------
# Timer callback
# ---------------------------------------------------------------------------

def _batch_tick() -> float | None:
    """Called every 0.2 s by bpy.app.timers while a batch is running.

    Returns the next interval (float) to keep the timer alive, or None to stop.
    """
    if _state.get("rendering"):
        return 0.2     # render in progress — check again shortly

    indices = _state.get("indices", [])
    current = _state.get("current", 0)

    if current >= len(indices):
        _finish_batch()
        return None    # stop timer

    scene = bpy.data.scenes.get(_state.get("scene_name", ""))
    if scene is None:
        _finish_batch()
        return None

    sm = getattr(scene, "scene_manager", None)
    if sm is None:
        _finish_batch()
        return None

    idx = indices[current]
    if not (0 <= idx < len(sm.setups)):
        _state["current"] += 1
        return 0.1

    setup = sm.setups[idx]
    warnings = apply_setup(scene, setup)
    for w in warnings:
        print(f"[Scene Manager] {w}")

    total = len(indices)
    print(f"[Scene Manager] Render All: {current + 1}/{total} — {setup.name}")

    anim = _is_animation(scene, setup)
    scene.render.use_single_layer = True
    _state["rendering"] = True
    try:
        bpy.ops.render.render(
            "INVOKE_DEFAULT",
            write_still=not anim,
            animation=anim,
        )
    except Exception as exc:
        print(f"[Scene Manager] Render launch failed for '{setup.name}': {exc}")
        _state["rendering"] = False
        _state["current"] += 1

    return 0.2


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _finish_batch() -> None:
    """Remove handlers, restore scene state, clear state dict."""
    _remove_handler(bpy.app.handlers.render_complete, _on_render_complete)
    _remove_handler(bpy.app.handlers.render_cancel,   _on_render_cancel)

    scene = bpy.data.scenes.get(_state.get("scene_name", ""))
    snap  = _state.get("snapshot")
    if scene and snap:
        try:
            _restore_snapshot(scene, snap)
        except Exception as exc:
            print(f"[Scene Manager] Could not restore pre-batch state: {exc}")

    done  = _state.get("current", 0)
    total = len(_state.get("indices", []))
    print(f"[Scene Manager] Render All finished: {done}/{total} setup(s).")
    _state.clear()


def _remove_handler(handler_list, fn) -> None:
    try:
        handler_list.remove(fn)
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class SM_OT_RenderSelected(bpy.types.Operator):
    """Apply the active setup and render it (single-shot, scene not restored)."""

    bl_idname = "scene_manager.render_selected"
    bl_label = "Render Selected"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        sm = context.scene.scene_manager
        return bool(sm.setups) and 0 <= sm.active_index < len(sm.setups)

    def execute(self, context):
        sm    = context.scene.scene_manager
        scene = context.scene
        setup = sm.setups[sm.active_index]

        warnings = apply_setup(scene, setup)
        for w in warnings:
            self.report({"WARNING"}, w)

        anim = _is_animation(scene, setup)
        scene.render.use_single_layer = True
        bpy.ops.render.render(
            "INVOKE_DEFAULT",
            write_still=not anim,
            animation=anim,
        )
        return {"FINISHED"}


class SM_OT_BatchRender(bpy.types.Operator):
    """Render every enabled setup in the list, one after another."""

    bl_idname = "scene_manager.batch_render"
    bl_label = "Render All"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        sm = context.scene.scene_manager
        return any(s.enabled for s in sm.setups)

    def execute(self, context):
        # Block re-entry if a batch is already running.
        if _state:
            self.report({"WARNING"}, "A batch render is already in progress.")
            return {"CANCELLED"}

        sm    = context.scene.scene_manager
        scene = context.scene

        indices = [i for i, s in enumerate(sm.setups) if s.enabled]
        if not indices:
            self.report({"WARNING"}, "No enabled setups found.")
            return {"CANCELLED"}

        # Pre-flight checks.
        problems: list[str] = []
        for i in indices:
            problems.extend(check_setup(scene, sm.setups[i]))
        if problems:
            for p in problems:
                self.report({"ERROR"}, p)
            return {"CANCELLED"}

        # Populate state.
        _state["scene_name"] = scene.name
        _state["indices"]    = indices
        _state["current"]    = 0
        _state["rendering"]  = False
        _state["snapshot"]   = _snapshot_scene(scene)

        # Wire up render handlers.
        bpy.app.handlers.render_complete.append(_on_render_complete)
        bpy.app.handlers.render_cancel.append(_on_render_cancel)

        # Kick off the timer queue.
        bpy.app.timers.register(_batch_tick, first_interval=0.1)

        self.report({"INFO"}, f"Render All started: {len(indices)} setup(s) queued.")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Scene snapshot helpers
# ---------------------------------------------------------------------------

def _snapshot_scene(scene: bpy.types.Scene) -> dict:
    r = scene.render
    return {
        "engine":               r.engine,
        "resolution_x":         r.resolution_x,
        "resolution_y":         r.resolution_y,
        "resolution_percentage":r.resolution_percentage,
        "filepath":             r.filepath,
        "file_format":          r.image_settings.file_format,
        "color_mode":           r.image_settings.color_mode,
        "use_overwrite":        r.use_overwrite,
        "use_file_extension":   r.use_file_extension,
        "frame_start":          scene.frame_start,
        "frame_end":            scene.frame_end,
        "frame_step":           scene.frame_step,
        "camera_name":          scene.camera.name if scene.camera else None,
        "use_single_layer":     r.use_single_layer,
    }


def _restore_snapshot(scene: bpy.types.Scene, snap: dict) -> None:
    r = scene.render
    r.engine                       = snap["engine"]
    r.resolution_x                 = snap["resolution_x"]
    r.resolution_y                 = snap["resolution_y"]
    r.resolution_percentage        = snap["resolution_percentage"]
    r.filepath                     = snap["filepath"]
    r.image_settings.file_format   = snap["file_format"]
    r.image_settings.color_mode    = snap["color_mode"]
    r.use_overwrite                = snap["use_overwrite"]
    r.use_file_extension           = snap["use_file_extension"]
    scene.frame_start              = snap["frame_start"]
    scene.frame_end                = snap["frame_end"]
    scene.frame_step               = snap["frame_step"]
    r.use_single_layer = snap["use_single_layer"]
    if snap["camera_name"]:
        cam = bpy.data.objects.get(snap["camera_name"])
        if cam:
            scene.camera = cam


classes = (SM_OT_RenderSelected, SM_OT_BatchRender)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    # Safety: remove handlers if add-on is disabled mid-batch.
    _remove_handler(bpy.app.handlers.render_complete, _on_render_complete)
    _remove_handler(bpy.app.handlers.render_cancel,   _on_render_cancel)
    _state.clear()
