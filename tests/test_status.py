import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


status = load_module("herdr_kitty_status", ROOT / "status.py")
renderer = load_module("herdr_kitty_tab_bar", ROOT / "kitty" / "tab_bar.py")


class StatusTests(unittest.TestCase):
    def test_counts_semantic_agent_states(self):
        snapshot = {
            "snapshot": {
                "agents": [
                    {"agent_status": "working"},
                    {"agent_status": "working"},
                    {"agent_status": "blocked"},
                    {"agent_status": "done"},
                    {"agent_status": "idle"},
                ]
            }
        }
        self.assertEqual(status.status_counts(snapshot), (2, 1, 1))

    def test_formats_machine_readable_title_with_hostname(self):
        self.assertEqual(
            status.format_title("Herdr", "dever", (2, 1, 3)),
            "Herdr (dever) 2 / 1 / 3",
        )

    def test_formats_validated_style_metadata(self):
        self.assertEqual(
            status.format_title(
                "Herdr", "dever", (2, 1, 3), "#123456", "#abcdef"
            ),
            "Herdr (dever) 2 / 1 / 3 [herdr-kitty bg=123456 fg=abcdef]",
        )

    def test_loads_host_local_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "label": "build",
                        "tab_background": "#123456",
                        "tab_foreground": "#ABCDEF",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                status.load_config(path),
                {
                    "label": "build",
                    "tab_background": "#123456",
                    "tab_foreground": "#abcdef",
                },
            )

    def test_rejects_invalid_config_color(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"tab_background": "blue"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "#RRGGBB"):
                status.load_config(path)


class DummyForeground:
    tab = "<tab-fg>"


class DummyBackground:
    tab = "<tab-bg>"


class DummyFormatter:
    fg = DummyForeground()
    bg = DummyBackground()


class RendererTests(unittest.TestCase):
    def test_colors_only_count_values(self):
        title = renderer.draw_title(
            {"title": "Herdr (dever) 12 / 3 / 4", "fmt": DummyFormatter()}
        )
        self.assertIn(f"{renderer.WORKING}12<tab-fg>", title)
        self.assertIn(f"{renderer.BLOCKED}3<tab-fg>", title)
        self.assertIn(f"{renderer.DONE}4<tab-fg>", title)

    def test_applies_host_style_and_hides_metadata(self):
        title = renderer.draw_title(
            {
                "title": (
                    "Herdr (dever) 12 / 3 / 4 "
                    "[herdr-kitty bg=123456 fg=abcdef]"
                ),
                "fmt": DummyFormatter(),
            }
        )
        self.assertTrue(title.startswith("\x1b[48;2;18;52;86m\x1b[38;2;171;205;239m"))
        self.assertNotIn("herdr-kitty bg", title)
        self.assertTrue(title.endswith("<tab-bg><tab-fg>"))

    def test_preserves_unrelated_titles(self):
        title = "project shell"
        self.assertEqual(
            renderer.draw_title({"title": title, "fmt": DummyFormatter()}),
            title,
        )


if __name__ == "__main__":
    unittest.main()
