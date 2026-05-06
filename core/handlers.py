"""Persistent Blender app-handlers for Scene Manager.

depsgraph_update_post watches for visibility changes (hide_render /
hide_viewport on objects and collections) and auto-snapshots them into the
currently active setup — with zero buttons or manual steps required.
"""

from bpy.app.handlers import persistent
import bpy

# Set to True inside apply_setup() so the handler ignores the transient
# visibility changes that happen while a setup is being applied.
applying_setup: bool = False

# Per-scene cache of the last known visibility hash, used to avoid
# redundant snapshots when nothing actually changed.
_last_hashes: dict[str, int] = {}


def _vis_hash(scene) -> int:
    """O(n) hash over every object/collection's hide_render + hide_viewport."""
    from .activation import _iter_all_collections
    parts: list = []
    for obj in scene.objects:
        parts.append((obj.name, obj.hide_render, obj.hide_viewport))
    root = getattr(scene, "collection", None)
    if root:
        for col in _iter_all_collections(root):
            parts.append((col.name, col.hide_render, col.hide_viewport))
    return hash(tuple(parts))


@persistent
def on_depsgraph_update(scene, depsgraph) -> None:
    """Called by Blender after every depsgraph evaluation.

    Filters to only act when:
      1. We are NOT mid-apply_setup() (applying_setup guard).
      2. An Object or Collection ID is among the updated datablocks.
      3. The computed visibility hash actually differs from last time.
    """
    if applying_setup:
        return

    sm = getattr(scene, "scene_manager", None)
    if sm is None or not sm.setups:
        return
    if not (0 <= sm.active_index < len(sm.setups)):
        return

    # Quick early-out: only care about Object / Collection updates.
    if not any(
        isinstance(upd.id, (bpy.types.Object, bpy.types.Collection))
        for upd in depsgraph.updates
    ):
        return

    key = scene.name
    h = _vis_hash(scene)
    if _last_hashes.get(key) == h:
        return  # nothing visibility-related changed

    _last_hashes[key] = h
    from .activation import snapshot_visibility
    snapshot_visibility(scene, sm.setups[sm.active_index])


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)


def unregister() -> None:
    handlers = bpy.app.handlers.depsgraph_update_post
    if on_depsgraph_update in handlers:
        handlers.remove(on_depsgraph_update)
