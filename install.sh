#!/bin/sh
set -eu

REPOSITORY="adnichols/herdr-kitty-status"
PLUGIN_ID="adnichols.kitty-status"
RAW_BASE="https://raw.githubusercontent.com/$REPOSITORY/main"
INSTALL_PLUGIN=1
INSTALL_KITTY=1
LOCAL_PLUGIN_PATH=""

usage() {
    cat <<'EOF'
Usage: install.sh [options]

Options:
  --plugin-only       Install the Herdr plugin and herdr-kitty launcher.
  --kitty-only        Install only the Kitty title renderer.
  --local PATH        Link a local plugin checkout instead of GitHub installation.
  -h, --help          Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --plugin-only) INSTALL_KITTY=0 ;;
        --kitty-only) INSTALL_PLUGIN=0 ;;
        --local)
            [ "$#" -ge 2 ] || { echo "--local requires a path" >&2; exit 2; }
            LOCAL_PLUGIN_PATH=$2
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

script_root=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)

fetch_repo_file() {
    relative_path=$1
    destination=$2
    source_file="$script_root/$relative_path"

    if [ -f "$source_file" ]; then
        cp "$source_file" "$destination"
    elif command -v curl >/dev/null 2>&1; then
        curl -fsSL "$RAW_BASE/$relative_path" -o "$destination"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$destination" "$RAW_BASE/$relative_path"
    else
        echo "curl or wget is required to download $relative_path" >&2
        exit 1
    fi
}

checksum() {
    cksum "$1" | awk '{ print $1 ":" $2 }'
}

refuse_modified_managed_file() {
    file=$1
    marker=$2
    checksum_file=$3

    [ -f "$file" ] || return 0
    if ! grep -q "$marker" "$file"; then
        echo "Refusing to overwrite existing file: $file" >&2
        return 1
    fi
    if [ ! -f "$checksum_file" ] || [ "$(cat "$checksum_file")" != "$(checksum "$file")" ]; then
        echo "Refusing to overwrite modified managed file: $file" >&2
        echo "Move it aside or merge the new version manually." >&2
        return 1
    fi
}

install_wrapper() {
    bin_dir=${HERDR_KITTY_BIN_DIR:-"$HOME/.local/bin"}
    wrapper="$bin_dir/herdr-kitty"
    checksum_file="$wrapper.checksum"
    mkdir -p "$bin_dir"

    refuse_modified_managed_file \
        "$wrapper" "HERDR_KITTY_STATUS_WRAPPER" "$checksum_file"

    temporary=$(mktemp "${TMPDIR:-/tmp}/herdr-kitty-wrapper.XXXXXX")
    fetch_repo_file "herdr-kitty" "$temporary"
    chmod 0755 "$temporary"
    mv "$temporary" "$wrapper"
    checksum "$wrapper" > "$checksum_file"
    echo "Installed Herdr launcher: $wrapper"
}

install_plugin() {
    if ! command -v herdr >/dev/null 2>&1; then
        echo "herdr is required to install the plugin" >&2
        exit 1
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3.8 or newer is required on the Herdr host" >&2
        exit 1
    fi
    if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 8))'; then
        echo "Python 3.8 or newer is required on the Herdr host" >&2
        exit 1
    fi

    if [ -n "$LOCAL_PLUGIN_PATH" ]; then
        herdr plugin unlink "$PLUGIN_ID" >/dev/null 2>&1 || true
        herdr plugin link "$LOCAL_PLUGIN_PATH"
    else
        herdr plugin install "$REPOSITORY" --yes
    fi

    install_wrapper

    # Best effort: a foreground Herdr client may not exist during installation.
    herdr plugin action invoke refresh --plugin "$PLUGIN_ID" >/dev/null 2>&1 || true
    echo "Installed Herdr plugin: $PLUGIN_ID"
    echo "Launch with 'herdr-kitty' for a guaranteed initial title refresh."
}

install_kitty_renderer() {
    config_home=${XDG_CONFIG_HOME:-"$HOME/.config"}
    kitty_dir=${KITTY_CONFIG_DIRECTORY:-"$config_home/kitty"}
    kitty_conf="$kitty_dir/kitty.conf"
    renderer="$kitty_dir/tab_bar.py"
    checksum_file="$renderer.herdr-kitty-status.checksum"
    marker_begin="# BEGIN herdr-kitty-status"
    marker_end="# END herdr-kitty-status"

    mkdir -p "$kitty_dir"
    touch "$kitty_conf"

    refuse_modified_managed_file \
        "$renderer" "HERDR_KITTY_STATUS_RENDERER" "$checksum_file"

    temporary=$(mktemp "${TMPDIR:-/tmp}/herdr-kitty-renderer.XXXXXX")
    fetch_repo_file "kitty/tab_bar.py" "$temporary"
    chmod 0644 "$temporary"
    mv "$temporary" "$renderer"
    checksum "$renderer" > "$checksum_file"

    if ! grep -qF "$marker_begin" "$kitty_conf"; then
        cp "$kitty_conf" "$kitty_conf.herdr-kitty-status.bak"
        {
            printf '\n%s\n' "$marker_begin"
            printf '%s\n' 'tab_title_template "{custom}"'
            printf '%s\n' "$marker_end"
        } >> "$kitty_conf"
    fi

    kitty_pid=${KITTY_PID:-}
    if [ -n "$kitty_pid" ] && kill -0 "$kitty_pid" 2>/dev/null; then
        kill -USR1 "$kitty_pid" 2>/dev/null || true
    elif command -v pgrep >/dev/null 2>&1; then
        pgrep -x kitty 2>/dev/null | while IFS= read -r pid; do
            kill -USR1 "$pid" 2>/dev/null || true
        done
    fi

    echo "Installed Kitty renderer: $renderer"
    echo "Configured Kitty title template: $kitty_conf"
}

[ "$INSTALL_PLUGIN" -eq 0 ] || install_plugin
[ "$INSTALL_KITTY" -eq 0 ] || install_kitty_renderer
