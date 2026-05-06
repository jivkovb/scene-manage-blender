"""Top-header quick-access menu for Scene Manager."""

import bpy


class SM_MT_HeaderMenu(bpy.types.Menu):
    """Scene Manager quick-access dropdown in the top header."""

    bl_idname = "SM_MT_HeaderMenu"
    bl_label = "Scene Manager"

    def draw(self, context):
        layout = self.layout
        sm = context.scene.scene_manager
        layout.operator("scene_manager.setup_add", icon="ADD", text="New Setup")
        layout.separator()
        if sm.setups:
            for i, setup in enumerate(sm.setups):
                op = layout.operator(
                    "scene_manager.setup_activate",
                    text=setup.name,
                    icon="SCENE_DATA",
                )
                op.index = i
        else:
            layout.label(text="No setups defined", icon="INFO")


def _draw_header_menu(self, context):
    self.layout.menu("SM_MT_HeaderMenu", text="", icon="SCENE_DATA")


classes = (SM_MT_HeaderMenu,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_editor_menus.append(_draw_header_menu)


def unregister():
    bpy.types.TOPBAR_MT_editor_menus.remove(_draw_header_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
