# herdr-kitty-status

Show live [Herdr](https://herdr.dev/) agent counts in a [Kitty](https://sw.kovidgoyal.net/kitty/) tab without wrapping or scraping individual agents.

```text
Herdr W:2 B:1 D:3
        ^   ^   ^
      yellow orange green
```

- **W** — agents currently working
- **B** — agents blocked and waiting for attention
- **D** — agents that finished while unseen

The count values are colored while Kitty's configured tab style, including Powerline, remains intact.

## How it works

The repository contains two small integrations:

1. A Herdr plugin reads semantic agent state from `session.snapshot` and sets the foreground client's outer terminal title.
2. A Kitty `draw_title` hook recognizes that title and colors the three count values.

The plugin is event-driven. It refreshes on agent-state changes, pane lifecycle events, and focus changes. The included `herdr-kitty` launcher schedules one initial refresh while the Herdr client attaches, so every launcher invocation starts with a current title. It does not run a polling daemon and does not inspect agent output.

## Requirements

- Herdr 0.7.4 or newer
- Kitty with Python title-renderer support
- Python 3.8 or newer on the Herdr host
- macOS or Linux

## Install

### Herdr and Kitty on the same machine

```sh
curl -fsSL https://raw.githubusercontent.com/adnichols/herdr-kitty-status/main/install.sh | sh
```

This installs the Herdr plugin, the `~/.local/bin/herdr-kitty` launcher, and the Kitty renderer. Restart Kitty if the automatic config reload is not visible immediately.

Launch Herdr with:

```sh
herdr-kitty
```

The launcher keeps Herdr in the foreground and performs a short, best-effort initial status refresh while the client attaches. All later updates come from plugin events.

### Remote Herdr over SSH

Install the Kitty renderer on the machine running Kitty:

```sh
curl -fsSL https://raw.githubusercontent.com/adnichols/herdr-kitty-status/main/install.sh \
  | sh -s -- --kitty-only
```

Install the plugin and launcher on every host that runs Herdr:

```sh
curl -fsSL https://raw.githubusercontent.com/adnichols/herdr-kitty-status/main/install.sh \
  | sh -s -- --plugin-only
```

Start remote sessions with `~/.local/bin/herdr-kitty`. The remote plugin updates Herdr's foreground client title. That title travels through the attached terminal session, and the local Kitty renderer colors it.

### Install directly with Herdr

If the Kitty renderer and launcher are already installed:

```sh
herdr plugin install adnichols/herdr-kitty-status --yes
herdr plugin action invoke refresh --plugin adnichols.kitty-status
```

Direct Herdr installation installs only the plugin. Use `install.sh --plugin-only` when you also want the `herdr-kitty` launcher that guarantees an initial refresh on attach.

### Local development

```sh
git clone https://github.com/adnichols/herdr-kitty-status.git
cd herdr-kitty-status
./install.sh --local "$PWD"
```

## Existing Kitty customization

The installer adds this managed block to `kitty.conf`:

```conf
# BEGIN herdr-kitty-status
tab_title_template "{custom}"
# END herdr-kitty-status
```

It installs the renderer at:

```text
~/.config/kitty/tab_bar.py
```

If an unrelated or locally modified `tab_bar.py` already exists, the installer refuses to overwrite it. Merge the repository's `draw_title()` function into the existing renderer manually. Uninstall also preserves managed files whose content changed after installation.

The renderer returns unrelated titles unchanged. It does not replace Kitty's `tab_bar_style`, so existing styles such as `powerline` continue to work.

## Configuration

Set a different title prefix in the environment inherited by the Herdr server:

```sh
export HERDR_KITTY_STATUS_PREFIX="Agents"
```

Colors are defined near the top of `kitty/tab_bar.py` as 24-bit SGR foreground colors:

```python
WORKING = "\x1b[38;2;249;226;175m"
BLOCKED = "\x1b[38;2;250;179;135m"
DONE = "\x1b[38;2;166;227;161m"
```

## Uninstall

From a checkout:

```sh
./uninstall.sh
```

Or remove only the plugin:

```sh
herdr plugin uninstall adnichols.kitty-status
```

## Privacy and security

- Uses Herdr's local Unix socket only.
- Does not read terminal scrollback, prompts, source code, or agent output.
- Does not send telemetry or make network requests at runtime.
- Publishes only three aggregate integer counts in the terminal title.
- Plugin commands run with normal user permissions, as documented by Herdr.

## Limitations

- Herdr updates its foreground attached client. With multiple simultaneous clients, the title follows whichever client Herdr considers foreground.
- Running plain `herdr` still receives event-driven updates, but the initial title refresh is guaranteed only when launching through `herdr-kitty` or manually invoking the refresh action.
- `done` follows Herdr semantics: completed and not yet seen. Focusing the relevant tab or pane can transition it to `idle`, reducing the done count.
- Kitty tab titles are plain text. Per-count colors come from the local `tab_bar.py` renderer, not from ANSI sequences embedded by the remote process.

## Development

Run the dependency-free test suite:

```sh
python3 -m unittest discover -s tests -v
```

Validate shell scripts:

```sh
sh -n install.sh uninstall.sh
```

## License

MIT
