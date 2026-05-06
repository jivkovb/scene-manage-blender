"""Add-on preferences — global settings accessible via Edit ▸ Preferences ▸ Add-ons."""

import bpy


class SceneManagerPreferences(bpy.types.AddonPreferences):
    """Global add-on preferences for Scene Manager."""

    bl_idname = __package__

    default_output_template: bpy.props.StringProperty(
        name="Default Output Template",
        description="Token template applied to new setups",
        default="//{setup}/",
    )
    confirm_delete: bpy.props.BoolProperty(
        name="Confirm on Delete",
        description="Show a confirmation dialog before deleting a setup",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "default_output_template")
        layout.prop(self, "confirm_delete")


classes = (SceneManagerPreferences,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
