"""UIList subclass for the setup list panel."""

import bpy

_COLOR_ICONS = {
    "NONE": "BLANK1",
    "RED": "COLORSET_01_VEC",
    "ORANGE": "COLORSET_02_VEC",
    "YELLOW": "COLORSET_03_VEC",
    "GREEN": "COLORSET_04_VEC",
    "BLUE": "COLORSET_05_VEC",
    "PURPLE": "COLORSET_06_VEC",
}


class SM_UL_SetupList(bpy.types.UIList):
    """Renders a single row for each Setup in the list."""

    bl_idname = "SM_UL_SetupList"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        setup = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            # Color dot
            color_icon = _COLOR_ICONS.get(setup.color_tag, "BLANK1")
            row.label(text="", icon=color_icon)
            # Enabled checkbox (greyed text when off)
            row.prop(
                setup, "enabled", text="", emboss=False,
                icon="CHECKBOX_HLT" if setup.enabled else "CHECKBOX_DEHLT",
            )
            # Name — disabled/greyed when not enabled
            sub = row.row(align=True)
            sub.active = setup.enabled
            sub.prop(setup, "name", text="", emboss=False, icon="SCENE_DATA")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="SCENE_DATA")


classes = (SM_UL_SetupList,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
