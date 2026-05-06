"""UI sub-package — panels, lists, and menus."""

from . import lists, panels, menus


def register():
    lists.register()
    panels.register()
    menus.register()


def unregister():
    menus.unregister()
    panels.unregister()
    lists.unregister()
