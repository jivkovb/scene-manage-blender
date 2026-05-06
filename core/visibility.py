"""Visibility helpers — shared logic for applying VisibilityEntry lists."""


def apply_visibility_entries(entries, warnings: list[str]) -> None:
    """Apply render/viewport hide flags from a CollectionProperty of VisibilityEntry."""
    for entry in entries:
        if entry.collection:
            entry.collection.hide_render = entry.hide_render
            entry.collection.hide_viewport = entry.hide_viewport
        else:
            warnings.append("Visibility: an entry has no collection assigned — skipped.")
