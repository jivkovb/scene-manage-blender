"""Module PropertyGroups — each represents one saveable aspect of a render setup.

Every module has two control booleans:
  use      — the module is part of this setup (data preserved when False)
  override — apply on activate (lets you temporarily disable without losing values)
"""

import bpy


# ---------------------------------------------------------------------------
# Output filename construction
# ---------------------------------------------------------------------------

class FilenamePart(bpy.types.PropertyGroup):
    """One building-block of the output filename construction rule.

    Parts are evaluated left-to-right and concatenated to form the filename.
    Separator parts (slash, underscore, dash, dot) insert literal characters.
    Token parts are expanded from scene/setup data at render time.
    Custom parts insert a user-typed literal string.
    """

    part_type: bpy.props.EnumProperty(
        name="Part Type",
        items=[
            # --- Tokens ---
            ("SETUP",       "Setup Name",   "Name of this render setup"),
            ("CAMERA",      "Camera",       "Active camera object name"),
            ("SCENE",       "Scene Name",   "Blender scene name"),
            ("DATE",        "Date",         "Render date — YYYYMMDD"),
            ("TIME",        "Time",         "Render time — HHMMSS"),
            ("BLEND",       "Blend File",   ".blend filename stem"),
            ("FRAME",       "Frame #",      "Current frame, zero-padded (0001)"),
            ("VIEW_LAYER",  "View Layer",   "Active view layer name"),
            ("CUSTOM",      "Custom Text",  "A fixed user-typed string"),
            # --- Separators ---
            ("SEP_SLASH",   "/",            "Path separator (sub-folder)"),
            ("SEP_UNDER",   "_",            "Underscore separator"),
            ("SEP_DASH",    "-",            "Dash separator"),
            ("SEP_DOT",     ".",            "Dot separator"),
        ],
        default="SETUP",
    )
    custom_text: bpy.props.StringProperty(
        name="Text",
        description="Literal text to insert (only used when Part Type = Custom Text)",
        default="",
    )


# ---------------------------------------------------------------------------
# Render modules
# ---------------------------------------------------------------------------

class CameraModule(bpy.types.PropertyGroup):
    """Camera assignment and optional lens/DOF overrides."""

    use: bpy.props.BoolProperty(name="Use Camera Module", default=True)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    camera: bpy.props.PointerProperty(
        name="Camera",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == "CAMERA",
    )
    lens_override: bpy.props.BoolProperty(name="Override Focal Length", default=False)
    lens: bpy.props.FloatProperty(
        name="Focal Length", default=50.0, min=1.0, max=5000.0, unit="CAMERA",
    )
    dof_override: bpy.props.BoolProperty(name="Override DOF", default=False)


class ResolutionModule(bpy.types.PropertyGroup):
    """Render resolution and pixel aspect ratio."""

    use: bpy.props.BoolProperty(name="Use Resolution Module", default=True)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    resolution_x: bpy.props.IntProperty(
        name="Width", default=1920, min=4, max=65536, subtype="PIXEL"
    )
    resolution_y: bpy.props.IntProperty(
        name="Height", default=1080, min=4, max=65536, subtype="PIXEL"
    )
    resolution_percentage: bpy.props.IntProperty(
        name="Resolution %", default=100, min=1, max=32767, subtype="PERCENTAGE"
    )
    pixel_aspect_x: bpy.props.FloatProperty(
        name="Pixel Aspect X", default=1.0, min=0.001, max=200.0
    )
    pixel_aspect_y: bpy.props.FloatProperty(
        name="Pixel Aspect Y", default=1.0, min=0.001, max=200.0
    )


class OutputModule(bpy.types.PropertyGroup):
    """Render output — directory, filename construction rule, and format.

    The full output path is:
        base_directory + [global_prefix] + resolved(filename_parts) + [.ext]

    filename_parts is an ordered list of FilenamePart items evaluated
    left-to-right, matching the Pulze Scene Manager filename construction rule.
    """

    use: bpy.props.BoolProperty(name="Use Output Module", default=True)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)

    # --- Directory ---
    base_directory: bpy.props.StringProperty(
        name="Base Directory",
        description="Root folder for render output. Filename parts are appended.",
        default="//renders/",
        subtype="DIR_PATH",
    )
    use_global_prefix: bpy.props.BoolProperty(
        name="Use Global Prefix",
        description="Prepend the Scene Manager prefix (shown at panel top) to the filename",
        default=True,
    )

    # --- Filename construction ---
    filename_parts: bpy.props.CollectionProperty(
        type=FilenamePart,
        description="Ordered list of tokens/separators that form the output filename",
    )
    active_part_index: bpy.props.IntProperty(name="Active Part", default=0, min=0)

    # --- Format ---
    file_format: bpy.props.EnumProperty(
        name="Format",
        items=[
            ("PNG",                  "PNG",              ""),
            ("JPEG",                 "JPEG",             ""),
            ("OPEN_EXR",             "OpenEXR",          ""),
            ("OPEN_EXR_MULTILAYER",  "OpenEXR Multi",    ""),
            ("TIFF",                 "TIFF",             ""),
            ("BMP",                  "BMP",              ""),
        ],
        default="PNG",
    )
    color_mode: bpy.props.EnumProperty(
        name="Color Mode",
        items=[("BW", "BW", ""), ("RGB", "RGB", ""), ("RGBA", "RGBA", "")],
        default="RGB",
    )
    color_depth: bpy.props.EnumProperty(
        name="Color Depth",
        items=[("8", "8-bit", ""), ("16", "16-bit", "")],
        default="8",
    )
    compression: bpy.props.IntProperty(
        name="PNG Compression", default=15, min=0, max=100, subtype="PERCENTAGE"
    )
    create_dirs: bpy.props.BoolProperty(name="Create Missing Directories", default=True)
    use_overwrite: bpy.props.BoolProperty(name="Overwrite Existing", default=True)
    use_file_extension: bpy.props.BoolProperty(name="Auto File Extension", default=True)


class FrameRangeModule(bpy.types.PropertyGroup):
    """Frame range / animation timing."""

    use: bpy.props.BoolProperty(name="Use Frame Range Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ("SINGLE", "Single Frame", "Render only the current frame"),
            ("RANGE",  "Frame Range",  "Render start to end with step"),
            ("LIST",   "Frame List",   'Comma list e.g. "1, 5, 10-20"'),
        ],
        default="RANGE",
    )
    frame_start: bpy.props.IntProperty(name="Start", default=1)
    frame_end: bpy.props.IntProperty(name="End", default=250)
    frame_step: bpy.props.IntProperty(name="Step", default=1, min=1)
    frame_list: bpy.props.StringProperty(name="Frame List", default="1")


class EngineModule(bpy.types.PropertyGroup):
    """Render engine, sampling, and compute device settings."""

    use: bpy.props.BoolProperty(name="Use Engine Module", default=True)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    engine: bpy.props.EnumProperty(
        name="Engine",
        items=[
            ("CYCLES",             "Cycles",     ""),
            ("BLENDER_EEVEE_NEXT", "EEVEE Next", ""),
        ],
        default="CYCLES",
    )
    samples: bpy.props.IntProperty(name="Samples", default=128, min=1, max=65536)
    denoise: bpy.props.BoolProperty(name="Denoise", default=True)
    max_bounces: bpy.props.IntProperty(name="Max Bounces", default=12, min=0, max=1024)
    device: bpy.props.EnumProperty(
        name="Compute Device",
        description=(
            "Cycles compute device for this setup. "
            "GPU requires a device configured in Preferences ▸ System ▸ Cycles Render Devices."
        ),
        items=[
            ("CPU", "CPU", "Render on the Central Processing Unit"),
            ("GPU", "GPU", "Render on the Graphics Processing Unit"),
        ],
        default="CPU",
    )


class SunModule(bpy.types.PropertyGroup):
    """Sun light override."""

    use: bpy.props.BoolProperty(name="Use Sun Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    sun_light: bpy.props.PointerProperty(
        name="Sun Light",
        type=bpy.types.Object,
        poll=lambda self, obj: (
            obj.type == "LIGHT" and obj.data is not None and obj.data.type == "SUN"
        ),
    )
    turn_off_others: bpy.props.BoolProperty(name="Hide All Other Lights", default=False)
    strength_override: bpy.props.BoolProperty(name="Override Strength", default=False)
    strength: bpy.props.FloatProperty(name="Strength", default=1.0, min=0.0)
    rotation_override: bpy.props.BoolProperty(name="Override Rotation Z", default=False)
    rotation_z: bpy.props.FloatProperty(name="Rotation Z", default=0.0, subtype="ANGLE")


class WorldModule(bpy.types.PropertyGroup):
    """World / HDRI environment settings."""

    use: bpy.props.BoolProperty(name="Use World Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    world: bpy.props.PointerProperty(name="World", type=bpy.types.World)
    hdri_path: bpy.props.StringProperty(
        name="HDRI File", default="", subtype="FILE_PATH"
    )
    rotation_z: bpy.props.FloatProperty(
        name="HDRI Rotation Z", default=0.0, subtype="ANGLE"
    )
    strength: bpy.props.FloatProperty(name="HDRI Strength", default=1.0, min=0.0)
    use_as_background: bpy.props.BoolProperty(name="Visible as Background", default=True)



class ViewLayerModule(bpy.types.PropertyGroup):
    """View layer selection — Phase 2 stub."""

    use: bpy.props.BoolProperty(name="Use View Layer Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)


class ColorManagementModule(bpy.types.PropertyGroup):
    """Color management overrides."""

    use: bpy.props.BoolProperty(name="Use Color Management Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)
    show_expanded: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    view_transform: bpy.props.StringProperty(name="View Transform", default="Filmic")
    look: bpy.props.StringProperty(name="Look", default="None")
    exposure: bpy.props.FloatProperty(name="Exposure", default=0.0)
    gamma: bpy.props.FloatProperty(name="Gamma", default=1.0, min=0.0)


class CompositorModule(bpy.types.PropertyGroup):
    """Compositor toggle — Phase 2 stub."""

    use: bpy.props.BoolProperty(name="Use Compositor Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)

    use_compositor: bpy.props.BoolProperty(name="Use Compositor", default=True)
    use_nodes: bpy.props.BoolProperty(name="Use Nodes", default=True)


class ScriptModule(bpy.types.PropertyGroup):
    """Python Text datablock run after activation — Phase 2 stub."""

    use: bpy.props.BoolProperty(name="Use Script Module", default=False)
    override: bpy.props.BoolProperty(name="Apply on Activate", default=True)

    text: bpy.props.PointerProperty(name="Script", type=bpy.types.Text)


# Registration order: leaf types before types that reference them.
classes = (
    FilenamePart,       # must precede OutputModule
    CameraModule,
    ResolutionModule,
    OutputModule,
    FrameRangeModule,
    EngineModule,
    SunModule,
    WorldModule,
    ViewLayerModule,
    ColorManagementModule,
    CompositorModule,
    ScriptModule,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
