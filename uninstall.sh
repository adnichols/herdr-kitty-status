#!/bin/sh
set -eu

PLUGIN_ID="adnichols.kitty-status"
config_home=${XDG_CONFIG_HOME:-"$HOME/.config"}
kitty_dir=${KITTY_CONFIG_DIRECTORY:-"$config_home/kitty"}
kitty_conf="$kitty_dir/kitty.conf"
renderer="$kitty_dir/tab_bar.py"
renderer_checksum="$renderer.herdr-kitty-status.checksum"
bin_dir=${HERDR_KITTY_BIN_DIR:-"$HOME/.local/bin"}
wrapper="$bin_dir/herdr-kitty"
wrapper_checksum="$wrapper.checksum"

checksum() {
    cksum "$1" | awk '{ print $1 ":" $2 }'
}

remove_managed_file() {
    file=$1
    checksum_file=$2

    [ -f "$file" ] || { rm -f "$checksum_file"; return 0; }
    if [ -f "$checksum_file" ] && [ "$(cat "$checksum_file")" = "$(checksum "$file")" ]; then
        rm -f "$file" "$checksum_file"
    else
        echo "Preserving modified file: $file" >&2
    fi
}

if command -v herdr >/dev/null 2>&1; then
    herdr plugin uninstall "$PLUGIN_ID" >/dev/null 2>&1 || true
fi

remove_managed_file "$renderer" "$renderer_checksum"
remove_managed_file "$wrapper" "$wrapper_checksum"

if [ -f "$kitty_conf" ] && grep -qF "# BEGIN herdr-kitty-status" "$kitty_conf"; then
    expected_block=$(printf '%s\n%s\n%s' \
        '# BEGIN herdr-kitty-status' \
        'tab_title_template "{custom}"' \
        '# END herdr-kitty-status')
    actual_block=$(awk '
        $0 == "# BEGIN herdr-kitty-status" { capture = 1 }
        capture { print }
        $0 == "# END herdr-kitty-status" { exit }
    ' "$kitty_conf")
    begin_count=$(grep -cF "# BEGIN herdr-kitty-status" "$kitty_conf" || true)
    end_count=$(grep -cF "# END herdr-kitty-status" "$kitty_conf" || true)

    if [ "$begin_count" -eq 1 ] && [ "$end_count" -eq 1 ] && \
        [ "$actual_block" = "$expected_block" ]; then
        temporary=$(mktemp "${TMPDIR:-/tmp}/herdr-kitty-status.XXXXXX")
        awk '
            $0 == "# BEGIN herdr-kitty-status" { skip = 1; next }
            $0 == "# END herdr-kitty-status" { skip = 0; next }
            !skip { print }
        ' "$kitty_conf" > "$temporary"
        mv "$temporary" "$kitty_conf"
    else
        echo "Preserving modified Kitty config block in: $kitty_conf" >&2
    fi
fi

echo "Removed herdr-kitty-status. Reload or restart Kitty if it is running."
