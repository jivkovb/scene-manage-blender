"""Setup list operators — add, duplicate, remove, reorder, activate.
Also contains filename-part operators for the universal Output Setup.
"""

import bpy

from ..core.activation import apply_setup


# ---------------------------------------------------------------------------
# Index helper
# ---------------------------------------------------------------------------

def _set_active_index(sm, idx: int) -> None:
    """Set active_index without triggering the UIList auto-activate callback."""
    sm.suppress_auto_activate = True
    sm.active_index = idx
    sm.suppress_auto_activate = False


# ---------------------------------------------------------------------------
# View Layer helpers
# ---------------------------------------------------------------------------

def _create_view_layer(scene, name: str) -> str:
    """Create a View Layer named *name* (or a suffixed variant if taken).
    Returns the actual name used.
    """
    if name not in scene.view_layers:
        scene.view_layers.new(name=name)
    return name


def _remove_view_layer(scene, name: str) -> None:
    """Remove the View Layer named *name*, but only if at least 2 layers exist."""
    vl = scene.view_layers.get(name)
    if vl and len(scene.view_layers) > 1:
        scene.view_layers.remove(vl)


# ---------------------------------------------------------------------------
# Default filename parts
# ---------------------------------------------------------------------------

_DEFAULT_PARTS = ("SETUP", "SEP_UNDER", "CAMERA", "SEP_UNDER", "FRAME")


def _init_default_filename_parts(output_mod) -> None:
    output_mod.filename_parts.clear()
    for type_key in _DEFAULT_PARTS:
        p = output_mod.filename_parts.add()
        p.part_type = type_key


# ---------------------------------------------------------------------------
# Setup CRUD
# ---------------------------------------------------------------------------

class SM_OT_SetupAdd(bpy.types.Operator):
    """Add a new setup and create a dedicated View Layer for it."""

    bl_idname = "scene_manager.setup_add"
    bl_label = "Add Setup"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sm = context.scene.scene_manager
        setup = sm.setups.add()
        n = len(sm.setups)
        setup.name = f"Setup {n:02d}"

        # Inherit universal engine/resolution into the new setup.
        uni = sm.settings
        setup.engine_module.engine = uni.engine
        setup.engine_module.samples = uni.samples
        setup.resolution_module.resolution_x = uni.resolution_x
        setup.resolution_module.resolution_y = uni.resolution_y
        setup.resolution_module.resolution_percentage = uni.resolution_percentage

        # Create a dedicated View Layer.
        vl_name = _create_view_layer(context.scene, setup.name)
        setup.view_layer_name = vl_name

        _set_active_index(sm, n - 1)
        return {"FINISHED"}


class SM_OT_SetupDuplicate(bpy.types.Operator):
    """Duplicate the active setup and create a new View Layer for the copy."""

    bl_idname = "scene_manager.setup_duplicate"
    bl_label = "Duplicate Setup"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.scene_manager.setups)

    def execute(self, context):
        sm = context.scene.scene_manager
        src = sm.setups[sm.active_index]
        dst = sm.setups.add()
        _copy_setup(src, dst)
        dst.name = src.name + " (Copy)"

        # Each copy gets its own View Layer.
        vl_name = _create_view_layer(context.scene, dst.name)
        dst.view_layer_name = vl_name

        _set_active_index(sm, len(sm.setups) - 1)
        return {"FINISHED"}


class SM_OT_SetupRemove(bpy.types.Operator):
    """Delete the active setup and its View Layer."""

    bl_idname = "scene_manager.setup_remove"
    bl_label = "Remove Setup"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.scene_manager.setups)

    def invoke(self, context, event):
        prefs = context.preferences.addons.get(__package__.split(".")[0])
        confirm = prefs.preferences.confirm_delete if prefs else True
        if confirm:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        sm = context.scene.scene_manager
        setup = sm.setups[sm.active_index]
        # Remove the associated View Layer before deleting the setup.
        if setup.view_layer_name:
            _remove_view_layer(context.scene, setup.view_layer_name)
        sm.setups.remove(sm.active_index)
        _set_active_index(sm, max(0, min(sm.active_index, len(sm.setups) - 1)))
        return {"FINISHED"}


class SM_OT_SetupMove(bpy.types.Operator):
    """Move the active setup up or down in the list."""

    bl_idname = "scene_manager.setup_move"
    bl_label = "Move Setup"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(
        items=[("UP", "Up", ""), ("DOWN", "Down", "")], default="UP"
    )

    @classmethod
    def poll(cls, context):
        return len(context.scene.scene_manager.setups) > 1

    def execute(self, context):
        sm = context.scene.scene_manager
        idx = sm.active_index
        new_idx = idx - 1 if self.direction == "UP" else idx + 1
        if 0 <= new_idx < len(sm.setups):
            sm.setups.move(idx, new_idx)
            _set_active_index(sm, new_idx)
        return {"FINISHED"}


class SM_OT_SetupActivate(bpy.types.Operator):
    """Apply the selected setup's settings to the current scene."""

    bl_idname = "scene_manager.setup_activate"
    bl_label = "Activate Setup"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(name="Setup Index", default=-1)

    @classmethod
    def poll(cls, context):
        return bool(context.scene.scene_manager.setups)

    def execute(self, context):
        sm = context.scene.scene_manager
        idx = self.index if self.index >= 0 else sm.active_index
        if not (0 <= idx < len(sm.setups)):
            self.report({"WARNING"}, "No valid setup selected.")
            return {"CANCELLED"}

        setup = sm.setups[idx]
        warnings = apply_setup(context.scene, setup)
        for w in warnings:
            self.report({"WARNING"}, w)
        _set_active_index(sm, idx)
        sm.prev_active_index = idx
        self.report({"INFO"}, f"Activated: {setup.name}")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Create setups from all scene cameras
# ---------------------------------------------------------------------------

class SM_OT_SetupsFromCameras(bpy.types.Operator):
    """Create one setup per camera in the scene (skips cameras that already have a setup)."""

    bl_idname = "scene_manager.setups_from_cameras"
    bl_label = "Create Setups from Cameras"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type == "CAMERA" for o in context.scene.objects)

    def execute(self, context):
        scene = context.scene
        sm = scene.scene_manager

        # Collect cameras already assigned to a setup so we skip duplicates.
        used = {
            s.camera_module.camera.name
            for s in sm.setups
            if s.camera_module.camera
        }

        cameras = [o for o in scene.objects if o.type == "CAMERA" and o.name not in used]
        if not cameras:
            self.report({"INFO"}, "All cameras already have a setup.")
            return {"CANCELLED"}

        for cam_obj in cameras:
            setup = sm.setups.add()
            setup.name = cam_obj.name

            # Assign camera module.
            setup.camera_module.use = True
            setup.camera_module.override = True
            setup.camera_module.camera = cam_obj

            # Create a dedicated View Layer.
            vl_name = _create_view_layer(scene, setup.name)
            setup.view_layer_name = vl_name

        _set_active_index(sm, len(sm.setups) - 1)
        self.report({"INFO"}, f"Created {len(cameras)} setup(s) from cameras.")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Universal settings operators
# ---------------------------------------------------------------------------

class SM_OT_MatchTimeline(bpy.types.Operator):
    """Set the universal frame range to match the scene's current timeline."""

    bl_idname = "scene_manager.match_timeline"
    bl_label = "Match Current Timeline"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        uni = context.scene.scene_manager.settings
        uni.frame_mode  = "RANGE"
        uni.frame_start = context.scene.frame_start
        uni.frame_end   = context.scene.frame_end
        uni.frame_step  = context.scene.frame_step
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Universal Output filename-part operators
# ---------------------------------------------------------------------------

class SM_OT_InitOutputParts(bpy.types.Operator):
    """Populate the universal output filename with the default part sequence."""

    bl_idname = "scene_manager.init_output_parts"
    bl_label = "Initialize Output Filename Parts"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sm = context.scene.scene_manager
        _init_default_filename_parts(sm.output_module)
        self.report({"INFO"}, "Output filename parts initialised with defaults.")
        return {"FINISHED"}


class SM_OT_FilenamePartAdd(bpy.types.Operator):
    """Append a filename part to the universal output construction rule."""

    bl_idname = "scene_manager.filename_part_add"
    bl_label = "Add Filename Part"
    bl_options = {"REGISTER", "UNDO"}

    part_type: bpy.props.EnumProperty(
        name="Part Type",
        items=[
            ("SETUP",      "Setup Name",  ""),
            ("CAMERA",     "Camera",      ""),
            ("SCENE",      "Scene Name",  ""),
            ("DATE",       "Date",        ""),
            ("TIME",       "Time",        ""),
            ("BLEND",      "Blend File",  ""),
            ("FRAME",      "Frame #",     ""),
            ("VIEW_LAYER", "View Layer",  ""),
            ("CUSTOM",     "Custom Text", ""),
            ("SEP_SLASH",  "/",           ""),
            ("SEP_UNDER",  "_",           ""),
            ("SEP_DASH",   "-",           ""),
            ("SEP_DOT",    ".",           ""),
        ],
        default="SEP_UNDER",
    )

    def execute(self, context):
        mod = context.scene.scene_manager.output_module
        p = mod.filename_parts.add()
        p.part_type = self.part_type
        mod.active_part_index = len(mod.filename_parts) - 1
        return {"FINISHED"}


class SM_OT_FilenamePartRemove(bpy.types.Operator):
    """Remove the selected filename part from the universal output rule."""

    bl_idname = "scene_manager.filename_part_remove"
    bl_label = "Remove Filename Part"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.scene_manager.output_module.filename_parts)

    def execute(self, context):
        mod = context.scene.scene_manager.output_module
        mod.filename_parts.remove(mod.active_part_index)
        mod.active_part_index = max(0, min(mod.active_part_index, len(mod.filename_parts) - 1))
        return {"FINISHED"}


class SM_OT_FilenamePartMove(bpy.types.Operator):
    """Move the selected filename part up or down."""

    bl_idname = "scene_manager.filename_part_move"
    bl_label = "Move Filename Part"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(
        items=[("UP", "Up", ""), ("DOWN", "Down", "")], default="UP"
    )

    @classmethod
    def poll(cls, context):
        return len(context.scene.scene_manager.output_module.filename_parts) > 1

    def execute(self, context):
        mod = context.scene.scene_manager.output_module
        idx = mod.active_part_index
        new_idx = idx - 1 if self.direction == "UP" else idx + 1
        if 0 <= new_idx < len(mod.filename_parts):
            mod.filename_parts.move(idx, new_idx)
            mod.active_part_index = new_idx
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Internal copy helpers
# ---------------------------------------------------------------------------

def _copy_setup(src, dst) -> None:
    """Deep-copy all per-setup module values from src to dst."""
    for attr in ("enabled", "color_tag", "notes"):
        setattr(dst, attr, getattr(src, attr))
    for attr in (
        "camera_module", "resolution_module", "frame_module", "engine_module",
        "sun_module", "world_module", "view_layer_module", "color_module",
        "compositor_module", "script_module",
    ):
        _copy_pg(getattr(src, attr), getattr(dst, attr))


def _copy_pg(src_pg, dst_pg) -> None:
    for prop in src_pg.bl_rna.properties:
        if prop.identifier in {"rna_type", "name"}:
            continue
        if prop.is_readonly:
            continue
        try:
            setattr(dst_pg, prop.identifier, getattr(src_pg, prop.identifier))
        except (AttributeError, TypeError):
            pass


classes = (
    SM_OT_SetupAdd,
    SM_OT_SetupDuplicate,
    SM_OT_SetupRemove,
    SM_OT_SetupMove,
    SM_OT_SetupActivate,
    SM_OT_SetupsFromCameras,
    SM_OT_MatchTimeline,
    SM_OT_InitOutputParts,
    SM_OT_FilenamePartAdd,
    SM_OT_FilenamePartRemove,
    SM_OT_FilenamePartMove,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
