"""Color Herdr agent counts while preserving Kitty's configured tab renderer."""

from __future__ import annotations

import re
from typing import Any

# Marker used by install.sh to distinguish this file from unrelated custom renderers.
HERDR_KITTY_STATUS_RENDERER = True

HERDR_STATUS = re.compile(
    r"^(?P<prefix>.+) W:(?P<working>\d+) B:(?P<blocked>\d+) D:(?P<done>\d+)$"
)

WORKING = "\x1b[38;2;249;226;175m"  # yellow
BLOCKED = "\x1b[38;2;250;179;135m"  # orange
DONE = "\x1b[38;2;166;227;161m"     # green


def draw_title(data: dict[str, Any]) -> str:
    """Return a title with only the Herdr count values colorized."""
    title = str(data["title"])
    match = HERDR_STATUS.match(title)
    if match is None:
        return title

    tab_foreground = str(data["fmt"].fg.tab)
    return (
        f'{match.group("prefix")} W:{WORKING}{match.group("working")}{tab_foreground}'
        f' B:{BLOCKED}{match.group("blocked")}{tab_foreground}'
        f' D:{DONE}{match.group("done")}{tab_foreground}'
    )
