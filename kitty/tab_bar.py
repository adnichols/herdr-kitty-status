"""Color Herdr agent counts while preserving Kitty's configured tab renderer."""

from __future__ import annotations

import re
from typing import Any

# Marker used by install.sh to distinguish this file from unrelated custom renderers.
HERDR_KITTY_STATUS_RENDERER = True

HERDR_STATUS = re.compile(
    r"^(?P<prefix>.+) (?P<working>\d+) / (?P<blocked>\d+) / (?P<done>\d+)"
    r"(?: \[herdr-kitty(?: bg=(?P<background>[0-9a-fA-F]{6}))?"
    r"(?: fg=(?P<foreground>[0-9a-fA-F]{6}))?\])?$"
)

WORKING = "\x1b[38;2;249;226;175m"  # yellow
BLOCKED = "\x1b[38;2;250;179;135m"  # orange
DONE = "\x1b[38;2;166;227;161m"     # green


def color_escape(kind: str, color: str) -> str:
    red, green, blue = (int(color[index : index + 2], 16) for index in (0, 2, 4))
    return f"\x1b[{kind};2;{red};{green};{blue}m"


def draw_title(data: dict[str, Any]) -> str:
    """Return a title with only the Herdr count values colorized."""
    title = str(data["title"])
    match = HERDR_STATUS.match(title)
    if match is None:
        return title

    tab_foreground = str(data["fmt"].fg.tab)
    tab_background = str(data["fmt"].bg.tab)
    foreground = match.group("foreground")
    background = match.group("background")
    title_foreground = (
        color_escape("38", foreground) if foreground is not None else tab_foreground
    )
    title_background = color_escape("48", background) if background is not None else ""

    return (
        f'{title_background}{title_foreground}{match.group("prefix")} '
        f'{WORKING}{match.group("working")}{title_foreground}'
        f' / {BLOCKED}{match.group("blocked")}{title_foreground}'
        f' / {DONE}{match.group("done")}{title_foreground}'
        f'{tab_background}{tab_foreground}'
    )
