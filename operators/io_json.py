"""JSON import/export operators — Phase 2 stubs."""

import bpy


class SM_OT_ExportJSON(bpy.types.Operator):
    """Export setups to a JSON file (Phase 2 — not yet implemented)."""

    bl_idname = "scene_manager.export_json"
    bl_label = "Export Setups (JSON)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "JSON export is a Phase 2 feature.")
        return {"FINISHED"}


class SM_OT_ImportJSON(bpy.types.Operator):
    """Import setups from a JSON file (Phase 2 — not yet implemented)."""

    bl_idname = "scene_manager.import_json"
    bl_label = "Import Setups (JSON)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report({"INFO"}, "JSON import is a Phase 2 feature.")
        return {"FINISHED"}


classes = (SM_OT_ExportJSON, SM_OT_ImportJSON)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
