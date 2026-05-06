"""Thumbnail capture operators — Phase 2 stubs."""

import bpy


class SM_OT_CaptureThumbnail(bpy.types.Operator):
    """Capture an OpenGL viewport thumbnail for the active setup (Phase 2)."""

    bl_idname = "scene_manager.capture_thumbnail"
    bl_label = "Capture Thumbnail"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "Thumbnails are a Phase 2 feature.")
        return {"FINISHED"}


classes = (SM_OT_CaptureThumbnail,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
