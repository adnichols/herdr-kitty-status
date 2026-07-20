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


def title_colors(title: str) -> tuple[int | None, int | None]:
    match = HERDR_STATUS.match(title)
    if match is None:
        return None, None
    background = match.group("background")
    foreground = match.group("foreground")
    return (
        int(background, 16) if background is not None else None,
        int(foreground, 16) if foreground is not None else None,
    )


def styled_tab(tab: Any) -> Any:
    background, foreground = title_colors(str(tab.title))
    changes = {}
    if background is not None:
        changes.update(active_bg=background, inactive_bg=background)
    if foreground is not None:
        changes.update(active_fg=foreground, inactive_fg=foreground)
    return tab._replace(**changes) if changes else tab


def draw_tab(
    draw_data: Any,
    screen: Any,
    tab: Any,
    before: int,
    max_tab_length: int,
    index: int,
    is_last: bool,
    extra_data: Any,
) -> int:
    """Draw Powerline separators using each host's configured tab colors."""
    from kitty.tab_bar import as_rgb, draw_tab_with_powerline

    rendered_tab = styled_tab(tab)
    background, foreground = title_colors(str(tab.title))
    if background is not None:
        screen.cursor.bg = as_rgb(background)
    if foreground is not None:
        screen.cursor.fg = as_rgb(foreground)

    original_next_tab = extra_data.next_tab
    if original_next_tab is not None:
        extra_data.next_tab = styled_tab(original_next_tab)
    try:
        return draw_tab_with_powerline(
            draw_data,
            screen,
            rendered_tab,
            before,
            max_tab_length,
            index,
            is_last,
            extra_data,
        )
    finally:
        extra_data.next_tab = original_next_tab


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
