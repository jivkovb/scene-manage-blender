"""apply_setup() — the single authoritative function that writes a Setup's state to a Scene.

Rules:
  • Uses only the data API (scene.render.xxx = ...). No bpy.ops calls.
  • Universal settings (engine, resolution) are applied first as a baseline.
  • Per-setup modules override the baseline when use=True AND override=True.
  • View Layer: each setup has a dedicated Blender View Layer; activating a setup
    switches the window to that layer — giving per-pass collection visibility for free.
  • Logs warnings for broken pointers rather than raising exceptions.
  • Application order:
      universal baseline → view layer → camera → resolution →
      world → sun → engine → color → frame_range → output
"""

import logging
import os

import bpy

from . import tokens as tok

log = logging.getLogger(__name__)


def apply_setup(scene: bpy.types.Scene, setup) -> list[str]:
    """Apply all active+override modules of *setup* to *scene*.

    Universal settings are applied first; per-setup modules override selectively.
    Returns a (possibly empty) list of non-fatal warning strings.
    """
    warnings: list[str] = []

    sm = getattr(scene, "scene_manager", None)

    # 1. Universal baseline — always applied so the scene is never left in an
    #    unknown state regardless of which per-setup modules are active.
    if sm:
        _apply_universal(scene, sm.settings)

    # 2. Switch to this setup's dedicated View Layer (handles per-pass visibility).
    _apply_view_layer(scene, setup, warnings)

    # 3. Per-setup module overrides (skip if use=False or override=False).
    _apply_camera(scene, setup.camera_module, warnings)
    _apply_resolution(scene, setup.resolution_module, warnings)
    _apply_world(scene, setup.world_module, warnings)
    _apply_sun(scene, setup.sun_module, warnings)
    _apply_color(scene, setup.color_module, warnings)
    _apply_frame_range(scene, setup.frame_module, warnings)

    # 4. Output — universal module, resolved per-setup via tokens.
    if sm:
        _apply_output(scene, sm.output_module, setup, warnings)

    return warnings


# ---------------------------------------------------------------------------
# Universal baseline
# ---------------------------------------------------------------------------

def _apply_universal(scene: bpy.types.Scene, settings) -> None:
    """Apply SceneManagerSettings as the render baseline before per-setup overrides."""
    r = scene.render
    r.engine = settings.engine
    r.resolution_x = settings.resolution_x
    r.resolution_y = settings.resolution_y
    r.resolution_percentage = settings.resolution_percentage
    if settings.engine == "CYCLES":
        try:
            scene.cycles.samples = settings.samples
            scene.cycles.device  = settings.device
        except AttributeError:
            pass
    elif settings.engine == "BLENDER_EEVEE_NEXT":
        try:
            scene.eevee.taa_render_samples = settings.samples
        except AttributeError:
            pass

    # Frame range baseline.
    if settings.frame_mode == "SINGLE":
        scene.frame_start = scene.frame_current
        scene.frame_end   = scene.frame_current
        scene.frame_step  = 1
    elif settings.frame_mode == "RANGE":
        scene.frame_start = settings.frame_start
        scene.frame_end   = settings.frame_end
        scene.frame_step  = settings.frame_step
    elif settings.frame_mode == "LIST":
        frames = _parse_frame_list(settings.frame_list)
        if frames:
            scene.frame_start = frames[0]
            scene.frame_end   = frames[-1]
            scene.frame_step  = 1


# ---------------------------------------------------------------------------
# View Layer — per-pass visibility via Blender's native system
# ---------------------------------------------------------------------------

def _apply_view_layer(scene: bpy.types.Scene, setup, warnings: list[str]) -> None:
    """Switch the active window's View Layer to the one belonging to this setup.

    Each setup has a dedicated view layer (created automatically when the setup
    was added). The user controls collection visibility per layer through the
    standard Blender outliner — no custom tracking needed.
    """
    vl_name = getattr(setup, "view_layer_name", "") or setup.name
    vl = scene.view_layers.get(vl_name)
    if vl is None:
        # Layer may have been manually deleted or this is a legacy setup.
        return
    ctx = bpy.context
    if ctx is None or not hasattr(ctx, "window") or ctx.window is None:
        return
    ctx.window.view_layer = vl


# ---------------------------------------------------------------------------
# Per-setup module helpers
# ---------------------------------------------------------------------------

def _skip(module) -> bool:
    return not (module.use and module.override)


def _switch_to_camera_view() -> None:
    """Switch every 3D viewport to camera perspective."""
    ctx = bpy.context
    if ctx is None or not hasattr(ctx, "window") or ctx.window is None:
        return
    for area in ctx.window.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.region_3d.view_perspective = "CAMERA"


def _apply_camera(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    if not mod.camera:
        warnings.append("Camera module: no camera assigned — skipping.")
        return
    scene.camera = mod.camera
    if mod.lens_override and mod.camera.data:
        mod.camera.data.lens = mod.lens
    _switch_to_camera_view()


def _apply_resolution(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    r = scene.render
    r.resolution_x = mod.resolution_x
    r.resolution_y = mod.resolution_y
    r.resolution_percentage = mod.resolution_percentage
    r.pixel_aspect_x = mod.pixel_aspect_x
    r.pixel_aspect_y = mod.pixel_aspect_y


def _apply_output(scene: bpy.types.Scene, mod, setup, warnings: list[str]) -> None:
    if _skip(mod):
        return
    r = scene.render

    filename = tok.resolve_parts(mod.filename_parts, scene, setup)

    prefix = ""
    if mod.use_global_prefix:
        sm = getattr(scene, "scene_manager", None)
        if sm:
            prefix = sm.prefix or ""

    full_path = tok.build_full_path(mod.base_directory, prefix, filename)
    r.filepath = full_path

    r.image_settings.file_format = mod.file_format
    r.image_settings.color_mode = mod.color_mode
    r.use_overwrite = mod.use_overwrite
    r.use_file_extension = mod.use_file_extension
    if mod.file_format == "PNG":
        r.image_settings.compression = mod.compression

    if mod.create_dirs:
        abs_path = bpy.path.abspath(full_path)
        dir_path = os.path.dirname(abs_path)
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except OSError as exc:
                warnings.append(f"Output: could not create '{dir_path}': {exc}")


def _apply_frame_range(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    if mod.mode == "SINGLE":
        scene.frame_start = scene.frame_current
        scene.frame_end = scene.frame_current
        scene.frame_step = 1
    elif mod.mode == "RANGE":
        scene.frame_start = mod.frame_start
        scene.frame_end = mod.frame_end
        scene.frame_step = mod.frame_step
    elif mod.mode == "LIST":
        frames = _parse_frame_list(mod.frame_list)
        if frames:
            scene.frame_start = frames[0]
            scene.frame_end = frames[-1]
            scene.frame_step = 1
        else:
            warnings.append(f"Frame Range: could not parse '{mod.frame_list}'.")


def _parse_frame_list(raw: str) -> list[int]:
    frames: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                frames.extend(range(int(a.strip()), int(b.strip()) + 1))
            except ValueError:
                pass
        else:
            try:
                frames.append(int(part))
            except ValueError:
                pass
    return sorted(set(frames))


def _apply_engine(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    scene.render.engine = mod.engine
    if mod.engine == "CYCLES":
        try:
            scene.cycles.samples = mod.samples
            scene.cycles.use_denoising = mod.denoise
            scene.cycles.max_bounces = mod.max_bounces
            scene.cycles.device = mod.device
        except AttributeError:
            warnings.append("Engine: Cycles settings unavailable — is Cycles enabled?")
    elif mod.engine == "BLENDER_EEVEE_NEXT":
        try:
            scene.eevee.taa_render_samples = mod.samples
        except AttributeError:
            warnings.append("Engine: EEVEE Next settings unavailable.")


def _apply_sun(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    if not mod.sun_light:
        warnings.append("Sun module: no sun light assigned — skipping.")
        return
    light_obj = mod.sun_light
    if mod.turn_off_others:
        for obj in scene.objects:
            if obj.type == "LIGHT" and obj != light_obj:
                obj.hide_render = True
    if mod.strength_override and light_obj.data:
        light_obj.data.energy = mod.strength
    if mod.rotation_override:
        light_obj.rotation_euler[2] = mod.rotation_z


def _apply_world(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    if mod.world:
        scene.world = mod.world
    elif mod.hdri_path:
        _load_hdri(scene, mod.hdri_path, mod.rotation_z, mod.strength, warnings)


def _load_hdri(scene, hdri_path, rotation_z, strength, warnings):
    world = scene.world
    if not world:
        warnings.append("World module: scene has no world — skipping HDRI load.")
        return
    world.use_nodes = True
    nt = world.node_tree
    env_node = next((n for n in nt.nodes if n.type == "TEX_ENVIRONMENT"), None)
    if not env_node:
        env_node = nt.nodes.new("ShaderNodeTexEnvironment")
    abs_path = bpy.path.abspath(hdri_path)
    if not os.path.exists(abs_path):
        warnings.append(f"World module: HDRI not found at '{abs_path}'.")
        return
    img = bpy.data.images.load(abs_path, check_existing=True)
    env_node.image = img
    bg_node = next((n for n in nt.nodes if n.type == "BACKGROUND"), None)
    if bg_node:
        bg_node.inputs["Strength"].default_value = strength


def _apply_color(scene: bpy.types.Scene, mod, warnings: list[str]) -> None:
    if _skip(mod):
        return
    vs = scene.view_settings
    try:
        vs.view_transform = mod.view_transform
    except TypeError:
        warnings.append(f"Color: unknown view transform '{mod.view_transform}'.")
    try:
        vs.look = mod.look
    except TypeError:
        warnings.append(f"Color: unknown look '{mod.look}'.")
    vs.exposure = mod.exposure
    vs.gamma = mod.gamma
