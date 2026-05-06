"""Utility operators — copy/paste module values, select-similar (Phase 2 stubs)."""

import bpy


class SM_OT_CopyModule(bpy.types.Operator):
    """Copy a module's values to the WindowManager clipboard (Phase 2)."""

    bl_idname = "scene_manager.copy_module"
    bl_label = "Copy Module Values"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "Copy/paste is a Phase 2 feature.")
        return {"FINISHED"}


classes = (SM_OT_CopyModule,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
