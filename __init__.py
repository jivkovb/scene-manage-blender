"""Scene Manager — Blender add-on entry point.

Provides a multi-setup render variant manager analogous to Pulze Scene Manager
in 3ds Max. Each Setup stores a bundle of camera, resolution, output, engine,
lighting, visibility, and color management settings that can be applied in one
click or iterated over in a non-blocking batch render.
"""

# Legacy bl_info kept for Blender < 4.2 compatibility.
bl_info = {
    "name": "Scene Manager",
    "author": "Scene Manager Developer",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "N-Panel ▸ Scene Manager | Properties ▸ Render ▸ Scene Manager",
    "description": "Multi-setup shot/variant manager for Blender",
    "doc_url": "",
    "category": "Render",
}

from . import preferences, props, operators, ui


def register():
    preferences.register()
    props.register()
    operators.register()
    ui.register()


def unregister():
    ui.unregister()
    operators.unregister()
    props.unregister()
    preferences.unregister()
