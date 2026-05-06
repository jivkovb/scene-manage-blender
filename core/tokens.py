"""Output path token resolver.

All public functions are pure (no side effects, no bpy.ops) and accept
explicit arguments so they can be unit-tested outside Blender.

Two resolution strategies:
  resolve()       — legacy {token} template string (kept for back-compat).
  resolve_parts() — evaluates an ordered list of FilenamePart items, matching
                    the Pulze Scene Manager filename construction rule UI.
"""

import datetime
import os
import re

# Conservative cross-platform forbidden filesystem characters.
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_name(name: str) -> str:
    """Replace characters that are illegal in file/directory names with underscores."""
    return _FORBIDDEN.sub("_", name)


# ---------------------------------------------------------------------------
# Parts-based resolver (primary path for the Output module)
# ---------------------------------------------------------------------------

#: Maps FilenamePart.part_type separator values to their literal characters.
_SEP_CHARS: dict[str, str] = {
    "SEP_SLASH": "/",
    "SEP_UNDER": "_",
    "SEP_DASH":  "-",
    "SEP_DOT":   ".",
}


def resolve_parts(
    parts,
    scene,
    setup,
    render_time: datetime.datetime | None = None,
    blend_path: str | None = None,
) -> str:
    """Evaluate an ordered collection of FilenamePart items into a filename string.

    Args:
        parts:       Iterable of FilenamePart PropertyGroup items (or dicts for tests).
        scene:       bpy.types.Scene or duck-typed mock.
        setup:       Setup PropertyGroup or mock with .name attribute.
        render_time: Datetime for {date}/{time} tokens; defaults to now.
        blend_path:  Override for bpy.data.filepath; useful in tests.

    Returns:
        Concatenated filename string (no directory, no extension).
        Returns the sanitized setup name as fallback when parts is empty.
    """
    if render_time is None:
        render_time = datetime.datetime.now()

    if blend_path is None:
        import bpy
        blend_path = bpy.data.filepath

    # Build lazy token lookup so we only compute what's needed.
    def _blend_stem():
        return sanitize_name(
            os.path.splitext(os.path.basename(blend_path))[0]
        ) if blend_path else "unsaved"

    def _camera_name():
        cam = getattr(scene, "camera", None)
        return sanitize_name(cam.name) if cam else "no_camera"

    def _scene_name():
        return sanitize_name(getattr(scene, "name", "scene"))

    def _view_layer():
        vls = getattr(scene, "view_layers", None)
        if vls:
            try:
                return sanitize_name(vls[0].name)
            except (IndexError, TypeError):
                pass
        return "ViewLayer"

    _TOKEN_FN = {
        "SETUP":      lambda: sanitize_name(setup.name),
        "CAMERA":     _camera_name,
        "SCENE":      _scene_name,
        "DATE":       lambda: render_time.strftime("%Y%m%d"),
        "TIME":       lambda: render_time.strftime("%H%M%S"),
        "BLEND":      _blend_stem,
        "FRAME":      lambda: f"{scene.frame_current:04d}",
        "VIEW_LAYER": _view_layer,
    }

    result: list[str] = []
    for part in parts:
        pt = part.part_type if hasattr(part, "part_type") else part.get("part_type", "")
        if pt in _SEP_CHARS:
            result.append(_SEP_CHARS[pt])
        elif pt == "CUSTOM":
            text = part.custom_text if hasattr(part, "custom_text") else part.get("custom_text", "")
            result.append(sanitize_name(text) if text else "")
        elif pt in _TOKEN_FN:
            result.append(_TOKEN_FN[pt]())

    return "".join(result) if result else sanitize_name(setup.name)


def build_full_path(
    base_directory: str,
    prefix: str,
    filename: str,
) -> str:
    """Combine directory + prefix + filename into a single render filepath.

    The prefix is inserted between the base directory and the filename so that:
        base_directory = '//renders/'
        prefix         = 'PROJECT_'
        filename       = 'Shot_01_Hero_0001'
        result         = '//renders/PROJECT_Shot_01_Hero_0001'
    """
    # Normalise the directory separator so we don't double-up slashes.
    sep = "/" if base_directory.endswith("/") or base_directory.endswith("\\") else "/"
    if base_directory and not (base_directory.endswith("/") or base_directory.endswith("\\")):
        base_directory += sep
    return base_directory + prefix + filename


# ---------------------------------------------------------------------------
# Legacy template resolver (kept for unit tests and potential fallback)
# ---------------------------------------------------------------------------

def resolve(
    template: str,
    scene,
    setup,
    render_time: datetime.datetime | None = None,
    blend_path: str | None = None,
) -> str:
    """Expand {token} placeholders in *template* and return the resolved string.

    Supported tokens:
      {setup} {camera} {date} {time} {blend} {frame} {ext} {view_layer}
    """
    if render_time is None:
        render_time = datetime.datetime.now()

    if blend_path is None:
        import bpy
        blend_path = bpy.data.filepath

    blend_stem = (
        os.path.splitext(os.path.basename(blend_path))[0] if blend_path else "unsaved"
    )

    camera = getattr(scene, "camera", None)
    camera_name = sanitize_name(camera.name) if camera else "no_camera"

    fmt = scene.render.image_settings.file_format
    ext = _FORMAT_EXT.get(fmt, fmt.lower())

    view_layers = getattr(scene, "view_layers", None)
    vl_name = "ViewLayer"
    if view_layers:
        try:
            vl_name = sanitize_name(view_layers[0].name)
        except (IndexError, TypeError):
            pass

    replacements = {
        "{setup}":      sanitize_name(setup.name),
        "{camera}":     camera_name,
        "{date}":       render_time.strftime("%Y%m%d"),
        "{time}":       render_time.strftime("%H%M%S"),
        "{blend}":      sanitize_name(blend_stem),
        "{frame}":      f"{scene.frame_current:04d}",
        "{ext}":        ext,
        "{view_layer}": vl_name,
    }

    result = template
    for token, value in replacements.items():
        result = result.replace(token, value)
    return result


_FORMAT_EXT: dict[str, str] = {
    "PNG":                 "png",
    "JPEG":                "jpg",
    "OPEN_EXR":            "exr",
    "OPEN_EXR_MULTILAYER": "exr",
    "TIFF":                "tif",
    "BMP":                 "bmp",
    "WEBP":                "webp",
}
