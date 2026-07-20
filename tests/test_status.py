import importlib.util
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
            "Herdr (dever) W:2 B:1 D:3",
        )


class DummyForeground:
    tab = "<tab-fg>"


class DummyFormatter:
    fg = DummyForeground()


class RendererTests(unittest.TestCase):
    def test_colors_only_count_values(self):
        title = renderer.draw_title(
            {"title": "Herdr (dever) W:12 B:3 D:4", "fmt": DummyFormatter()}
        )
        self.assertIn(f"W:{renderer.WORKING}12<tab-fg>", title)
        self.assertIn(f"B:{renderer.BLOCKED}3<tab-fg>", title)
        self.assertIn(f"D:{renderer.DONE}4<tab-fg>", title)

    def test_preserves_unrelated_titles(self):
        title = "project shell"
        self.assertEqual(
            renderer.draw_title({"title": title, "fmt": DummyFormatter()}),
            title,
        )


if __name__ == "__main__":
    unittest.main()
