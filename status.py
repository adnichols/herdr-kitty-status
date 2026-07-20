#!/usr/bin/env python3
"""Publish aggregate Herdr agent counts to the foreground terminal title."""

from __future__ import annotations

import fcntl
import json
import os
import re
import socket
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

DEFAULT_SOCKET = Path.home() / ".config" / "herdr" / "herdr.sock"
DEFAULT_PREFIX = "Herdr"
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def request(
    socket_path: str, method: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    payload = {
        "id": f"kitty-status:{os.getpid()}:{method}",
        "method": method,
        "params": params or {},
    }

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(socket_path)
        connection.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        with connection.makefile("r", encoding="utf-8") as reader:
            line = reader.readline()

    if not line:
        raise ConnectionError("Herdr closed the socket without responding")

    response = json.loads(line)
    if "error" in response:
        error = response["error"]
        raise RuntimeError(error.get("message", str(error)))
    return response["result"]


def status_counts(snapshot_result: Dict[str, Any]) -> Tuple[int, int, int]:
    agents = snapshot_result["snapshot"].get("agents", [])
    working = sum(agent.get("agent_status") == "working" for agent in agents)
    blocked = sum(agent.get("agent_status") == "blocked" for agent in agents)
    done = sum(agent.get("agent_status") == "done" for agent in agents)
    return working, blocked, done


def load_config(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    if not isinstance(raw_config, dict):
        raise ValueError(f"config must contain a JSON object: {path}")

    config: Dict[str, str] = {}
    label = raw_config.get("label")
    if label is not None:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("config 'label' must be a non-empty string")
        label = label.strip()
        if len(label) > 64 or not all(character.isprintable() for character in label):
            raise ValueError("config 'label' must be at most 64 printable characters")
        config["label"] = label

    for key in ("tab_background", "tab_foreground"):
        color = raw_config.get(key)
        if color is None:
            continue
        if not isinstance(color, str) or HEX_COLOR.fullmatch(color) is None:
            raise ValueError(f"config '{key}' must be a color in #RRGGBB format")
        config[key] = color.lower()

    return config


def format_title(
    prefix: str,
    hostname: str,
    counts: Tuple[int, int, int],
    tab_background: Optional[str] = None,
    tab_foreground: Optional[str] = None,
) -> str:
    working, blocked, done = counts
    title = f"{prefix} ({hostname}) {working} / {blocked} / {done}"
    style = []
    if tab_background:
        style.append(f"bg={tab_background.lstrip('#')}")
    if tab_foreground:
        style.append(f"fg={tab_foreground.lstrip('#')}")
    if style:
        title += " [herdr-kitty " + " ".join(style) + "]"
    return title


@contextmanager
def update_lock() -> Iterator[None]:
    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if state_dir:
        lock_dir = Path(state_dir)
    else:
        lock_dir = Path(tempfile.gettempdir()) / "herdr-kitty-status-{}".format(os.getuid())
    lock_dir.mkdir(parents=True, exist_ok=True)

    with (lock_dir / "update.lock").open("w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield


def main() -> int:
    socket_path = os.environ.get("HERDR_SOCKET_PATH", str(DEFAULT_SOCKET))
    prefix = os.environ.get("HERDR_KITTY_STATUS_PREFIX", DEFAULT_PREFIX).strip() or DEFAULT_PREFIX
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    config_path = Path(
        os.environ.get(
            "HERDR_KITTY_STATUS_CONFIG",
            str(config_home / "herdr-kitty-status" / "config.json"),
        )
    )

    try:
        config = load_config(config_path)
        default_hostname = socket.gethostname().split(".", 1)[0]
        hostname = (
            os.environ.get(
                "HERDR_KITTY_STATUS_HOSTNAME",
                config.get("label", default_hostname),
            ).strip()
            or default_hostname
        )
        # Herdr can launch several event hooks together. Serialize the complete
        # snapshot-and-title operation so an older process cannot overwrite a
        # newer count after a burst of events.
        with update_lock():
            snapshot = request(socket_path, "session.snapshot")
            title = format_title(
                prefix,
                hostname,
                status_counts(snapshot),
                config.get("tab_background"),
                config.get("tab_foreground"),
            )
            request(socket_path, "client.window_title.set", {"title": title})
    except (
        ConnectionError,
        FileNotFoundError,
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"herdr-kitty-status: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
