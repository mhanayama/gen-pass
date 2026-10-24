#!/bin/sh
# Install the standalone gen-pass release for this machine. No Python or sudo.
set -eu

fail() { printf 'gen-pass: %s\n' "$*" >&2; exit 1; }

main() {
    case "$(uname -s)" in
        Darwin) os=macos ;;
        Linux) os=linux ;;
        *) fail 'Supported systems: macOS and Linux. On Windows use install.ps1.' ;;
    esac
    case "$(uname -m)" in
        arm64|aarch64) arch=arm64 ;;
        x86_64|amd64) arch=x86_64 ;;
        *) fail 'Supported CPUs: arm64 and x86_64.' ;;
    esac
    for tool in curl tar mktemp install; do
        command -v "$tool" >/dev/null 2>&1 || fail "Required command not found: $tool"
    done
    if command -v sha256sum >/dev/null 2>&1; then
        hash_tool=sha256sum
    elif command -v shasum >/dev/null 2>&1; then
        hash_tool=shasum
    else
        fail 'SHA-256 verification requires sha256sum or shasum.'
    fi

    version=${GEN_PASS_VERSION:-latest}
    case "$version" in *[!a-zA-Z0-9._-]*|'') fail 'Invalid GEN_PASS_VERSION.' ;; esac
    base=https://github.com/mhanayama/gen-pass/releases
    if [ "$version" = latest ]; then
        base=$base/latest/download
    else
        base=$base/download/$version
    fi
    asset=gen-pass-$os-$arch.tar.gz
    existing=$(command -v gen-pass 2>/dev/null || true)
    bin_dir=${GEN_PASS_INSTALL_DIR:-}
    if [ -z "$bin_dir" ]; then
        case "$existing" in
            /*) bin_dir=$(dirname "$existing") ;;
            *) bin_dir=$HOME/.local/bin ;;
        esac
    fi
    data_dir=${GEN_PASS_DATA_DIR:-"$HOME/.local/share/gen-pass"}
    case "$bin_dir" in /*) ;; *) fail 'GEN_PASS_INSTALL_DIR must be an absolute path.' ;; esac
    case "$data_dir" in /*) ;; *) fail 'GEN_PASS_DATA_DIR must be an absolute path.' ;; esac
    if [ -d "$bin_dir" ] && [ ! -w "$bin_dir" ]; then
        fail "Installation directory is not writable: $bin_dir"
    fi
    [ ! -d "$bin_dir/gen-pass" ] || fail "Expected an executable, found a directory: $bin_dir/gen-pass"
    temporary=$(mktemp -d)
    staged=
    trap 'rm -rf "$temporary"; if [ -n "$staged" ]; then rm -f "$staged"; fi' EXIT
    trap 'exit 1' HUP INT TERM

    printf 'Downloading %s (%s)…\n' "$asset" "$version"
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        "$base/$asset" -o "$temporary/$asset"
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        "$base/$asset.sha256" -o "$temporary/checksum"
    # Never let the checksum file select arbitrary filenames for verification.
    expected=$(awk 'NR == 1 {print $1}' "$temporary/checksum")
    [ "${#expected}" -eq 64 ] || fail 'Invalid SHA-256 checksum.'
    case "$expected" in *[!0-9a-f]*) fail 'Invalid SHA-256 checksum.' ;; esac
    if [ "$hash_tool" = sha256sum ]; then
        actual=$(sha256sum "$temporary/$asset")
    else
        actual=$(shasum -a 256 "$temporary/$asset")
    fi
    actual=${actual%% *}
    [ "$actual" = "$expected" ] || fail 'SHA-256 mismatch; nothing was installed.'

    tar -xzf "$temporary/$asset" -C "$temporary"
    # Smoke-test before replacing an existing installation. Do not copy passwords.
    "$temporary/gen-pass/gen-pass" --help >/dev/null
    if [ -e "$bin_dir/gen-pass" ] || [ -L "$bin_dir/gen-pass" ]; then
        printf 'Updating existing installation: %s/gen-pass\n' "$bin_dir"
    fi
    mkdir -p "$bin_dir" "$data_dir"
    cp -R "$temporary/gen-pass/licenses" "$data_dir/"
    cp "$temporary/gen-pass/LICENSE" "$temporary/gen-pass/THIRD_PARTY_LICENSES.md" "$data_dir/"
    # Stage and rename so an unsuccessful download cannot damage an existing binary.
    staged=$(mktemp "$bin_dir/.gen-pass.XXXXXX")
    if ! install -m 755 "$temporary/gen-pass/gen-pass" "$staged"; then
        rm -f "$staged"
        fail 'Could not install executable.'
    fi
    mv -f "$staged" "$bin_dir/gen-pass"
    printf 'Installed: %s/gen-pass\nLicenses: %s\n' "$bin_dir" "$data_dir"
    case ":$PATH:" in
        *":$bin_dir:"*) printf 'Run: gen-pass\n' ;;
        *) printf 'Run now: "%s/gen-pass"\nAdd this directory to PATH in your shell settings: %s\n' "$bin_dir" "$bin_dir" ;;
    esac
}

# A partially downloaded script must not start the installation.
main
