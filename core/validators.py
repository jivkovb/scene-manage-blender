"""Pre-render sanity checks called before batch render starts."""

import bpy


def check_setup(scene: bpy.types.Scene, setup) -> list[str]:
    """Return a list of human-readable problem strings for *setup*.

    An empty list means the setup is likely renderable.
    """
    problems: list[str] = []
    prefix = f"[{setup.name}]"

    # Camera
    cam = setup.camera_module
    if cam.use and cam.override and not cam.camera:
        problems.append(f"{prefix} Camera module is active but no camera is assigned.")

    # Output — now lives on scene.scene_manager, not on the setup.
    sm = getattr(scene, "scene_manager", None)
    if sm:
        out = sm.output_module
        if out.use and out.override:
            if "//" in out.base_directory and not bpy.data.filepath:
                problems.append(
                    f"{prefix} Output directory uses '//' (relative) but the .blend file is unsaved."
                )

    return problems
