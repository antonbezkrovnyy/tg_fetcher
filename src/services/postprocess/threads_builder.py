"""Thread structure builder for a day's collection."""

from __future__ import annotations

from typing import Any

from src.models.schemas import MessageCollection


def build_threads(collection: MessageCollection) -> dict[str, Any]:
    """Build thread mapping (roots, parent_to_children, depth) from messages."""
    parent_to_children: dict[str, list[int]] = {}
    roots: list[int] = []
    depth: dict[str, int] = {}

    id_to_parent: dict[int, int | None] = {}
    for m in collection.messages:
        if m.reply_to_msg_id:
            id_to_parent[m.id] = m.reply_to_msg_id
            parent_to_children.setdefault(str(m.reply_to_msg_id), []).append(m.id)
        else:
            id_to_parent[m.id] = None
            roots.append(m.id)

    def calc_depth(mid: int) -> int:
        d = 0
        cur = id_to_parent.get(mid)
        while cur:
            d += 1
            cur = id_to_parent.get(cur)
        return d

    for m in collection.messages:
        depth[str(m.id)] = calc_depth(m.id)

    return {
        "roots": roots,
        "parent_to_children": parent_to_children,
        "depth": depth,
    }
