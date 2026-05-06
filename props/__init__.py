"""Props sub-package — registers all PropertyGroups in dependency order."""

from . import modules, setup


def register():
    modules.register()  # Module PGs must precede Setup which references them.
    setup.register()


def unregister():
    setup.unregister()
    modules.unregister()
