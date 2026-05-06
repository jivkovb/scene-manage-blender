"""N-Panel and Render Properties panels for Scene Manager."""

import bpy

from ..core.tokens import resolve_parts, build_full_path, _FORMAT_EXT


# ---------------------------------------------------------------------------
# Shared mixin
# ---------------------------------------------------------------------------

class _SM_PanelBase:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scene Manager"


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class SM_PT_Main(_SM_PanelBase, bpy.types.Panel):
    """Scene Manager main panel — prefix, setup list, render buttons."""

    bl_idname = "SM_PT_Main"
    bl_label = "Scene Manager"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        sm = context.scene.scene_manager

        # --- Global Prefix ---
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Prefix:", icon="FONT_DATA")
        row.prop(sm, "prefix", text="")

        layout.separator(factor=0.5)

        # --- Setup list ---
        row = layout.row()
        row.template_list(
            "SM_UL_SetupList", "",
            sm, "setups",
            sm, "active_index",
            rows=5,
        )
        col = row.column(align=True)
        col.operator("scene_manager.setups_from_cameras", icon="CAMERA_DATA", text="")
        col.separator()
        col.operator("scene_manager.setup_add",       icon="ADD",       text="")
        col.operator("scene_manager.setup_duplicate", icon="DUPLICATE", text="")
        col.operator("scene_manager.setup_remove",    icon="REMOVE",    text="")
        col.separator()
        col.operator("scene_manager.setup_move", icon="TRIA_UP",   text="").direction = "UP"
        col.operator("scene_manager.setup_move", icon="TRIA_DOWN", text="").direction = "DOWN"

        # --- Render buttons ---
        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("scene_manager.render_selected", icon="RENDER_STILL",     text="Render Selected")
        row.operator("scene_manager.batch_render",    icon="RENDER_ANIMATION", text="Render All")

        # --- Active setup identity ---
        if sm.setups and 0 <= sm.active_index < len(sm.setups):
            setup = sm.setups[sm.active_index]
            layout.separator()
            col = layout.column(align=True)
            col.prop(setup, "name")
            col.prop(setup, "color_tag")
            col.prop(setup, "enabled")
            if setup.notes:
                layout.prop(setup, "notes")


# ---------------------------------------------------------------------------
# Universal Render Settings panel
# ---------------------------------------------------------------------------

class SM_PT_UniversalSettings(_SM_PanelBase, bpy.types.Panel):
    """Project-wide render defaults — new setups inherit these values."""

    bl_idname = "SM_PT_UniversalSettings"
    bl_label = "Universal Render Settings"
    bl_parent_id = "SM_PT_Main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        uni = context.scene.scene_manager.settings

        # --- Engine & Samples ---
        col = layout.column(align=True)
        col.label(text="Engine & Samples:", icon="SHADING_RENDERED")
        row = col.row(align=True)
        row.prop(uni, "engine",  text="")
        row.prop(uni, "samples", text="Samples")
        if uni.engine == "CYCLES":
            row = col.row(align=True)
            row.prop(uni, "device", expand=True)

        layout.separator(factor=0.5)

        # --- Resolution ---
        col = layout.column(align=True)
        col.label(text="Resolution:", icon="RENDER_RESULT")
        row = col.row(align=True)
        row.prop(uni, "resolution_x", text="W")
        row.prop(uni, "resolution_y", text="H")
        col.prop(uni, "resolution_percentage", text="Scale %")

        layout.separator(factor=0.5)

        # --- Frame Range ---
        col = layout.column(align=True)
        col.label(text="Frame Range:", icon="TIME")
        col.prop(uni, "frame_mode", expand=True)
        if uni.frame_mode == "RANGE":
            row = col.row(align=True)
            row.prop(uni, "frame_start", text="Start")
            row.prop(uni, "frame_end",   text="End")
            col.prop(uni, "frame_step",  text="Step")
        elif uni.frame_mode == "LIST":
            col.prop(uni, "frame_list", text="Frames")
        col.separator(factor=0.3)
        col.operator("scene_manager.match_timeline", icon="NLA_PUSHDOWN", text="Match Current Timeline")



# ---------------------------------------------------------------------------
# Universal Output Setup panel
# ---------------------------------------------------------------------------

class SM_PT_OutputSetup(_SM_PanelBase, bpy.types.Panel):
    """Scene-wide output configuration — one rule shared by every setup.

    Filename parts containing the {setup} or {camera} tokens are resolved
    differently for each setup, giving each render a unique path.
    """

    bl_idname = "SM_PT_OutputSetup"
    bl_label = "Output Setup"
    bl_parent_id = "SM_PT_Main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        mod = context.scene.scene_manager.output_module
        self.layout.prop(mod, "use", text="")

    def draw(self, context):
        sm = context.scene.scene_manager
        mod = sm.output_module
        layout = self.layout
        layout.active = mod.use

        layout.prop(mod, "override", text="Apply on Activate")
        layout.separator()

        # --- Directory ---
        col = layout.column(align=True)
        col.label(text="Base Directory:", icon="FILE_FOLDER")
        col.prop(mod, "base_directory", text="")
        col.prop(
            mod, "use_global_prefix",
            text=f"Prepend Prefix  (\"{sm.prefix}\")" if sm.prefix else "Prepend Global Prefix",
        )

        layout.separator()

        # --- Filename construction rule ---
        layout.label(text="Filename Construction Rule:", icon="SORTALPHA")

        box = layout.box()
        if mod.filename_parts:
            for i, part in enumerate(mod.filename_parts):
                row = box.row(align=True)
                row.prop(part, "part_type", text="")
                if part.part_type == "CUSTOM":
                    row.prop(part, "custom_text", text="")
                sub = row.row(align=True)
                sub.scale_x = 0.6
                sub.operator("scene_manager.filename_part_move", text="", icon="TRIA_UP").direction   = "UP"
                sub.operator("scene_manager.filename_part_move", text="", icon="TRIA_DOWN").direction = "DOWN"
                sub.operator("scene_manager.filename_part_remove", text="", icon="X")
        else:
            col = box.column(align=True)
            col.label(text="No parts defined.", icon="INFO")
            col.operator("scene_manager.init_output_parts", icon="FILE_REFRESH",
                         text="Initialize with Defaults")

        # Quick-add row
        row = layout.row(align=True)
        row.label(text="Add:")
        for type_key, label in (
            ("SETUP",     "Setup"),
            ("CAMERA",    "Cam"),
            ("SCENE",     "Scene"),
            ("DATE",      "Date"),
            ("FRAME",     "Frame"),
            ("SEP_UNDER", "_"),
            ("SEP_SLASH", "/"),
            ("CUSTOM",    "Custom"),
        ):
            row.operator("scene_manager.filename_part_add", text=label).part_type = type_key

        layout.separator()

        # --- Live preview ---
        box = layout.box()
        box.label(text="Preview:", icon="VIEWZOOM")
        try:
            if sm.setups and 0 <= sm.active_index < len(sm.setups):
                active_setup = sm.setups[sm.active_index]
            else:
                class _Stub:
                    name = "Setup_Name"
                active_setup = _Stub()

            filename = resolve_parts(mod.filename_parts, context.scene, active_setup)
            prefix   = sm.prefix if mod.use_global_prefix else ""
            full     = build_full_path(mod.base_directory, prefix, filename)
            if mod.use_file_extension:
                ext = _FORMAT_EXT.get(mod.file_format, mod.file_format.lower())
                full += "." + ext
            display = full if len(full) <= 64 else "..." + full[-61:]
            box.label(text=display)
        except Exception as exc:
            box.label(text=f"(preview error: {exc})", icon="ERROR")

        layout.separator()

        # --- Format settings ---
        layout.label(text="Format:", icon="IMAGE_DATA")
        col = layout.column(align=True)
        col.prop(mod, "file_format")
        col.prop(mod, "color_mode")
        if mod.file_format == "PNG":
            col.prop(mod, "compression")
        row = layout.row(align=True)
        row.prop(mod, "use_file_extension")
        row.prop(mod, "use_overwrite")
        layout.prop(mod, "create_dirs")


# ---------------------------------------------------------------------------
# Per-setup module panel — single expandable list replaces 6 sub-panels
# ---------------------------------------------------------------------------

class SM_PT_Modules(_SM_PanelBase, bpy.types.Panel):
    """Per-setup modules — click the arrow to expand settings inline."""

    bl_idname = "SM_PT_Modules"
    bl_label = "Modules"
    bl_parent_id = "SM_PT_Main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        sm = context.scene.scene_manager
        return bool(sm.setups) and 0 <= sm.active_index < len(sm.setups)

    def draw(self, context):
        sm = context.scene.scene_manager
        setup = sm.setups[sm.active_index]
        layout = self.layout

        _draw_expandable_module(
            layout, setup.camera_module, "Camera", "CAMERA_DATA",
            _draw_camera_settings)
        _draw_expandable_module(
            layout, setup.resolution_module, "Resolution", "RENDER_RESULT",
            _draw_resolution_settings)
        _draw_expandable_module(
            layout, setup.frame_module, "Frame Range", "TIME",
            _draw_frame_settings)
        _draw_expandable_module(
            layout, setup.sun_module, "Sun", "LIGHT_SUN",
            _draw_sun_settings)
        _draw_expandable_module(
            layout, setup.world_module, "World / HDRI", "WORLD",
            _draw_world_settings)
        _draw_expandable_module(
            layout, setup.color_module, "Color Management", "COLOR",
            _draw_color_settings)


# ---------------------------------------------------------------------------
# Render Properties panel (secondary location)
# ---------------------------------------------------------------------------

class SM_PT_RenderProps(bpy.types.Panel):
    bl_idname = "SM_PT_RenderProps"
    bl_label = "Scene Manager"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sm = context.scene.scene_manager
        row = layout.row()
        row.template_list(
            "SM_UL_SetupList", "render_props",
            sm, "setups",
            sm, "active_index",
            rows=4,
        )
        row = layout.row(align=True)
        row.operator("scene_manager.render_selected", icon="RENDER_STILL",     text="Render Selected")
        row.operator("scene_manager.batch_render",    icon="RENDER_ANIMATION", text="Render All")


# ---------------------------------------------------------------------------
# Module row helpers
# ---------------------------------------------------------------------------

def _draw_expandable_module(layout, mod, label, icon, draw_settings_fn):
    """Draw a header row with expand/collapse, use-dot, label, override-check.

    When expanded, calls *draw_settings_fn(box, mod)* inside a box below.
    """
    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(
        mod, "show_expanded",
        icon="DISCLOSURE_TRI_DOWN" if mod.show_expanded else "DISCLOSURE_TRI_RIGHT",
        emboss=False, text="",
    )
    row.prop(mod, "use", text="", emboss=False,
             icon="RADIOBUT_ON" if mod.use else "RADIOBUT_OFF")
    row.label(text=label, icon=icon)
    if mod.use:
        row.prop(mod, "override", text="", emboss=False,
                 icon="CHECKBOX_HLT" if mod.override else "CHECKBOX_DEHLT")

    if mod.show_expanded:
        box = col.box()
        box.active = mod.use and mod.override
        draw_settings_fn(box, mod)

    col.separator(factor=0.2)


def _draw_camera_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    layout.prop(mod, "camera")
    row = layout.row(align=True)
    row.prop(mod, "lens_override", text="")
    sub = row.row()
    sub.active = mod.lens_override
    sub.prop(mod, "lens")
    layout.prop(mod, "dof_override")


def _draw_resolution_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    col = layout.column(align=True)
    col.prop(mod, "resolution_x", text="Width")
    col.prop(mod, "resolution_y", text="Height")
    col.prop(mod, "resolution_percentage", text="%")
    layout.separator()
    row = layout.row(align=True)
    row.prop(mod, "pixel_aspect_x", text="Aspect X")
    row.prop(mod, "pixel_aspect_y", text="Aspect Y")


def _draw_frame_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    layout.prop(mod, "mode")
    if mod.mode == "RANGE":
        row = layout.row(align=True)
        row.prop(mod, "frame_start", text="Start")
        row.prop(mod, "frame_end",   text="End")
        layout.prop(mod, "frame_step", text="Step")
    elif mod.mode == "LIST":
        layout.prop(mod, "frame_list")


def _draw_engine_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    layout.prop(mod, "engine")
    layout.prop(mod, "samples")
    if mod.engine == "CYCLES":
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Compute Device:", icon="DESKTOP")
        row = col.row(align=True)
        row.prop(mod, "device", expand=True)
        if mod.device == "GPU":
            col.label(
                text="GPU backend set in Preferences > System > Cycles Render Devices",
                icon="INFO",
            )
        layout.separator()
        layout.prop(mod, "denoise")
        layout.prop(mod, "max_bounces")


def _draw_sun_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    layout.prop(mod, "sun_light")
    layout.prop(mod, "turn_off_others")
    row = layout.row(align=True)
    row.prop(mod, "strength_override", text="")
    sub = row.row()
    sub.active = mod.strength_override
    sub.prop(mod, "strength")
    row = layout.row(align=True)
    row.prop(mod, "rotation_override", text="")
    sub = row.row()
    sub.active = mod.rotation_override
    sub.prop(mod, "rotation_z")


def _draw_world_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    layout.prop(mod, "world")
    layout.separator()
    layout.label(text="HDRI Override (when no World is set):")
    layout.prop(mod, "hdri_path", text="File")
    layout.prop(mod, "strength")
    layout.prop(mod, "rotation_z")



def _draw_color_settings(layout, mod):
    layout.prop(mod, "override", text="Apply on Activate")
    layout.separator()
    layout.prop(mod, "view_transform")
    layout.prop(mod, "look")
    layout.prop(mod, "exposure")
    layout.prop(mod, "gamma")


classes = (
    SM_PT_Main,
    SM_PT_UniversalSettings,
    SM_PT_OutputSetup,
    SM_PT_Modules,
    SM_PT_RenderProps,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
