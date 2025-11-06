import json
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Tuple


def count_reactions(reactions) -> int:
    """Return total reactions count on a message (handles None)."""
    if not reactions or not getattr(reactions, "results", None):
        return 0
    return sum(r.count for r in reactions.results)


def build_output_path(base_dir: str, channel_username: str) -> Tuple[str, str, str]:
    """Return (output_dir, safe_name, filepath) for a given channel/chat and today's date.

    - base_dir: root data directory (e.g. '/data')
    - channel_username: username or chat id string
    """
    safe_name = channel_username.lstrip("@")
    # heuristic: put into channels or chats folder — caller can override if needed
    if any(kw in channel_username for kw in ("chat", "beginners")):
        output_dir = os.path.join(base_dir, "chats")
    else:
        output_dir = os.path.join(base_dir, "channels")

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    dir_for_channel = os.path.join(output_dir, safe_name)
    os.makedirs(dir_for_channel, exist_ok=True)
    filepath = os.path.join(dir_for_channel, f"{today}.json")
    return output_dir, safe_name, filepath


def prepare_message(msg, channel_username: str) -> Dict[str, Any]:
    """Normalize a telethon Message into a serializable dict used by the pipeline."""
    sender_id = None
    if getattr(msg, "sender", None) and getattr(msg.sender, "id", None):
        sender_id = msg.sender.id

    text = (getattr(msg, "text", None) or "").strip()

    return {
        "id": msg.id,
        "ts": int(msg.date.timestamp()) if getattr(msg, "date", None) else None,
        "text": text,
        "reply_to": getattr(msg, "reply_to_msg_id", None),
        "reactions": count_reactions(getattr(msg, "reactions", None)),
        "sender_id": sender_id,
    }


def save_json(
    path: str, data: Any, ensure_ascii: bool = False, indent: int = 2
) -> None:
    """Save data as JSON to given path (overwrites)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
