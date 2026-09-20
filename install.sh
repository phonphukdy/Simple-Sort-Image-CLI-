#!/usr/bin/env bash
set -e

CMD_NAME="sortimg"
INSTALL_DIR="$HOME/.local/bin"
SCRIPT_DEST_DIR="$HOME/.sortimg"
SCRIPT_DEST="$SCRIPT_DEST_DIR/sortimg.py"
WRAPPER_PATH="$INSTALL_DIR/$CMD_NAME"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$SCRIPT_DEST_DIR"
mkdir -p "$INSTALL_DIR"

cp "$SOURCE_DIR/sortimg.py" "$SCRIPT_DEST"

# Detect a WORKING python command. On Windows, `python3` (and sometimes
# `python`) may exist in PATH only as a fake "Microsoft Store alias" stub
# that does nothing useful - so we don't just check existence, we check that
# running it actually reports a real Python version.
find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            local ver
            ver="$("$candidate" --version 2>&1)"
            if [[ "$ver" == Python\ [0-9]* ]]; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python)" || {
    echo "✘ No working Python found in PATH"
    echo "   Install it from https://www.python.org/downloads/ (check 'Add python.exe to PATH' during setup)"
    echo "   Then run install.sh again"
    exit 1
}

# Write a small wrapper script instead of a symlink. Symlinks need admin
# rights / Developer Mode on Windows, so a wrapper works everywhere
# (macOS, Linux, and Git Bash on Windows) with no special permissions.
cat > "$WRAPPER_PATH" << EOF
#!/usr/bin/env bash
exec "$PYTHON_BIN" "$SCRIPT_DEST" "\$@"
EOF
chmod +x "$WRAPPER_PATH" 2>/dev/null || true
chmod +x "$SCRIPT_DEST" 2>/dev/null || true

echo "✅ Installed successfully!"
echo "   Script location : $SCRIPT_DEST"
echo "   Command wrapper : $WRAPPER_PATH"
echo "   Command to use  : $CMD_NAME  (runs via: $PYTHON_BIN)"
echo

if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    SHELL_RC="$HOME/.bashrc"
    [[ "$SHELL" == *zsh* ]] && SHELL_RC="$HOME/.zshrc"
    echo "⚠️  $INSTALL_DIR is not yet in your PATH"
    echo "   Add this line to the end of $SHELL_RC :"
    echo
    echo '     export PATH="$HOME/.local/bin:$PATH"'
    echo
    echo "   Then run:  source $SHELL_RC"
else
    echo "🎉 Ready to go! cd into a folder with photos and type: $CMD_NAME"
fi

echo
echo "Checking dependencies..."
echo "  ✔ using $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

if "$PYTHON_BIN" -c "import send2trash" >/dev/null 2>&1; then
    echo "  ✔ send2trash found (deleted photos go to system Trash)"
else
    echo "  ✘ send2trash not found -> run: $PYTHON_BIN -m pip install send2trash"
fi

if command -v chafa >/dev/null 2>&1; then
    echo "  ✔ chafa found (nice color previews)"
elif command -v viu >/dev/null 2>&1; then
    echo "  ✔ viu found (nice color previews)"
elif "$PYTHON_BIN" -c "import PIL" >/dev/null 2>&1; then
    echo "  ⚠ chafa/viu not found, but Pillow is -> using the lower-quality fallback preview"
else
    echo "  ✘ None of chafa, viu, or Pillow found -> no image previews will be shown"
    echo "    Install one of these:"
    echo "      macOS         : brew install chafa"
    echo "      Debian/Ubuntu : sudo apt install chafa"
    echo "      Windows       : winget install --id hpjansson.Chafa --exact"
    echo "      or: $PYTHON_BIN -m pip install pillow"
fi

echo
echo "Setup complete 🎉"
