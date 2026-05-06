"""Setup and root SceneManager PropertyGroups — stored inside the .blend file."""

import bpy

from .modules import (
    CameraModule,
    ColorManagementModule,
    CompositorModule,
    EngineModule,
    FrameRangeModule,
    OutputModule,
    ResolutionModule,
    ScriptModule,
    SunModule,
    ViewLayerModule,
    WorldModule,
)


def _apply_now(self, context):
    """Update callback — immediately writes universal settings to the active scene."""
    scene = getattr(context, "scene", None)
    if scene is None:
        return
    from ..core.activation import _apply_universal
    _apply_universal(scene, self)


class SceneManagerSettings(bpy.types.PropertyGroup):
    """Universal render settings — applied automatically as the baseline on every setup
    activation, and immediately whenever any value is changed by the user.
    Per-setup modules override specific values when use=True and override=True.
    """

    # --- Universal engine ---
    engine: bpy.props.EnumProperty(
        name="Engine",
        items=[
            ("CYCLES",             "Cycles",     ""),
            ("BLENDER_EEVEE_NEXT", "EEVEE Next", ""),
        ],
        default="CYCLES",
        update=_apply_now,
    )
    samples: bpy.props.IntProperty(
        name="Samples", default=128, min=1, max=65536,
        update=_apply_now,
    )
    device: bpy.props.EnumProperty(
        name="Compute Device",
        description="Cycles compute device (GPU requires configuration in Preferences > System)",
        items=[
            ("CPU", "CPU", "Render on the Central Processing Unit"),
            ("GPU", "GPU", "Render on the Graphics Processing Unit"),
        ],
        default="CPU",
        update=_apply_now,
    )

    # --- Universal resolution ---
    resolution_x: bpy.props.IntProperty(
        name="Width", default=1920, min=4, max=65536, subtype="PIXEL",
        update=_apply_now,
    )
    resolution_y: bpy.props.IntProperty(
        name="Height", default=1080, min=4, max=65536, subtype="PIXEL",
        update=_apply_now,
    )
    resolution_percentage: bpy.props.IntProperty(
        name="Res %", default=100, min=1, max=32767, subtype="PERCENTAGE",
        update=_apply_now,
    )

    # --- Universal frame range ---
    frame_mode: bpy.props.EnumProperty(
        name="Frame Mode",
        items=[
            ("SINGLE", "Single Frame", "Render only the current frame"),
            ("RANGE",  "Frame Range",  "Render from Start to End"),
            ("LIST",   "Frame List",   'Comma-separated frames, e.g. "1, 5, 10-20"'),
        ],
        default="RANGE",
        update=_apply_now,
    )
    frame_start: bpy.props.IntProperty(name="Start", default=1,  update=_apply_now)
    frame_end:   bpy.props.IntProperty(name="End",   default=250, update=_apply_now)
    frame_step:  bpy.props.IntProperty(name="Step",  default=1, min=1, update=_apply_now)
    frame_list:  bpy.props.StringProperty(name="Frames", default="1", update=_apply_now)

    # --- Universal output ---
    base_directory: bpy.props.StringProperty(
        name="Base Directory",
        description="Default output directory used by new setups",
        default="//renders/",
        subtype="DIR_PATH",
    )
    file_format: bpy.props.EnumProperty(
        name="Format",
        items=[
            ("PNG",                 "PNG",         ""),
            ("JPEG",                "JPEG",        ""),
            ("OPEN_EXR",            "OpenEXR",     ""),
            ("OPEN_EXR_MULTILAYER", "OpenEXR Multi",""),
            ("TIFF",                "TIFF",        ""),
        ],
        default="PNG",
    )


class Setup(bpy.types.PropertyGroup):
    """A named render setup — a bundle of scene settings applied as a unit."""

    # --- Identity ---
    name: bpy.props.StringProperty(name="Name", default="Setup")
    enabled: bpy.props.BoolProperty(
        name="Enabled",
        description="Include this setup in Render All",
        default=True,
    )
    color_tag: bpy.props.EnumProperty(
        name="Color Tag",
        items=[
            ("NONE",   "None",   "", "X",              0),
            ("RED",    "Red",    "", "COLORSET_01_VEC", 1),
            ("ORANGE", "Orange", "", "COLORSET_02_VEC", 2),
            ("YELLOW", "Yellow", "", "COLORSET_03_VEC", 3),
            ("GREEN",  "Green",  "", "COLORSET_04_VEC", 4),
            ("BLUE",   "Blue",   "", "COLORSET_05_VEC", 5),
            ("PURPLE", "Purple", "", "COLORSET_06_VEC", 6),
        ],
        default="NONE",
    )
    notes: bpy.props.StringProperty(
        name="Notes", default="", options={"TEXTEDIT_UPDATE"}
    )

    # Name of the Blender View Layer that belongs to this setup.
    # Created automatically when the setup is added.
    view_layer_name: bpy.props.StringProperty(
        name="View Layer",
        description="Blender View Layer activated when this setup is selected",
        default="",
        options={"HIDDEN"},
    )

    # --- Modules (output is universal — lives on SceneManager, not here) ---
    camera_module:      bpy.props.PointerProperty(type=CameraModule)
    resolution_module:  bpy.props.PointerProperty(type=ResolutionModule)
    frame_module:       bpy.props.PointerProperty(type=FrameRangeModule)
    engine_module:      bpy.props.PointerProperty(type=EngineModule)
    sun_module:         bpy.props.PointerProperty(type=SunModule)
    world_module:       bpy.props.PointerProperty(type=WorldModule)
    view_layer_module:  bpy.props.PointerProperty(type=ViewLayerModule)
    color_module:       bpy.props.PointerProperty(type=ColorManagementModule)
    compositor_module:  bpy.props.PointerProperty(type=CompositorModule)
    script_module:      bpy.props.PointerProperty(type=ScriptModule)


def _on_active_index_update(self, context):
    """Auto-activate a setup when the user clicks a different row in the UIList.

    Suppressed by operators that change active_index programmatically (Add,
    Duplicate, Move, Remove) via the suppress_auto_activate flag, so only an
    explicit user click in the list triggers scene activation.
    """
    if self.suppress_auto_activate:
        return
    sm = self
    new_idx = sm.active_index
    old_idx = sm.prev_active_index

    scene = getattr(context, "scene", None)
    if scene is None:
        return

    sm.prev_active_index = new_idx

    if not sm.setups or not (0 <= new_idx < len(sm.setups)):
        return
    from ..core.activation import apply_setup
    warnings = apply_setup(scene, sm.setups[new_idx])
    for w in warnings:
        print(f"[Scene Manager] {w}")


class SceneManager(bpy.types.PropertyGroup):
    """Root property group attached to bpy.types.Scene as scene.scene_manager."""

    setups: bpy.props.CollectionProperty(type=Setup)

    active_index: bpy.props.IntProperty(
        name="Active Setup Index",
        default=0,
        min=0,
        update=_on_active_index_update,
    )

    # Suppresses auto-activate when operators change active_index programmatically.
    suppress_auto_activate: bpy.props.BoolProperty(
        default=False,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    # Tracks the previously active index so the update callback can snapshot it.
    prev_active_index: bpy.props.IntProperty(
        default=0,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    # Global prefix prepended to every output filename.
    prefix: bpy.props.StringProperty(
        name="Prefix",
        description=(
            "Project-wide prefix prepended to every setup's output filename "
            "(e.g. 'PROJ_2024_'). Ignored if 'Use Global Prefix' is off in a setup."
        ),
        default="",
    )

    preview_mode: bpy.props.BoolProperty(
        name="Preview Mode",
        description="Edit setup values without applying them to the scene",
        default=False,
    )
    camera_sync_mode: bpy.props.BoolProperty(
        name="Camera Sync",
        description="Switching the viewport camera activates the matching setup",
        default=False,
    )

    settings: bpy.props.PointerProperty(type=SceneManagerSettings)

    # Universal output — one shared config for the whole scene.
    # Filename parts resolve per-setup via the {setup} / {camera} tokens.
    output_module: bpy.props.PointerProperty(type=OutputModule)


classes = (SceneManagerSettings, Setup, SceneManager)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.scene_manager = bpy.props.PointerProperty(type=SceneManager)


def unregister():
    del bpy.types.Scene.scene_manager
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
