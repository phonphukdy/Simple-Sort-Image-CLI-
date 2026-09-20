#!/usr/bin/env python3
"""
sortimg - Interactive terminal-based photo sorter.

Usage: cd into the folder with your photos, then run `sortimg`
(after installing via install.sh), or run directly with: python3 sortimg.py

Commands while running (type and press Enter):
  d              delete this photo (moved to system Trash on exit)
  o              move to the "other" category (99_other)
  n              create a new category and move this photo into it
  <number>       move this photo into that category, e.g. 01
  u              undo the last action (repeatable)
  s              toggle preview mode (sixels / symbols)
  v              view this photo full-size in your default image viewer
  c              toggle showing top-5 / all categories
  h              toggle showing help commands
  q              quit

Pressing Enter with no input repeats the last successful d / o / n / <number> / u command.
"""

import os
import re
import sys
import shlex
import shutil
import platform
import subprocess
from pathlib import Path
from collections import Counter

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

try:
    from PIL import Image
except ImportError:
    Image = None


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
CATEGORY_PATTERN = re.compile(r"^(\d{2})_(.+)$")
OTHER_NUMBER = 99
OTHER_NAME = "other"
MIN_CATEGORY_NUMBER = 1
TRASH_STAGING_DIRNAME = ".sortimg_trash"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
MAX_PREVIEW_HEIGHT = 22  # จำกัดความสูงรูปไม่ให้ใหญ่เกินไป


# --------------------------------------------------------------------------
# Category helpers
# --------------------------------------------------------------------------

def scan_categories(base: Path):
    cats = {}
    for entry in base.iterdir():
        if entry.is_dir():
            m = CATEGORY_PATTERN.match(entry.name)
            if m:
                num = int(m.group(1))
                name = m.group(2)
                if MIN_CATEGORY_NUMBER <= num < OTHER_NUMBER:
                    cats[num] = name
    return cats


def next_free_number(cats: dict):
    for i in range(MIN_CATEGORY_NUMBER, OTHER_NUMBER):
        if i not in cats:
            return i
    return None


# --------------------------------------------------------------------------
# Trash helpers
# --------------------------------------------------------------------------

def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    i = 1
    while True:
        candidate = path.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def soft_delete(path: Path, base: Path) -> Path:
    trash_dir = base / TRASH_STAGING_DIRNAME
    trash_dir.mkdir(exist_ok=True)
    dest = unique_path(trash_dir / path.name)
    shutil.move(str(path), str(dest))
    return dest


def flush_trash_to_system(base: Path):
    trash_dir = base / TRASH_STAGING_DIRNAME
    if not trash_dir.exists():
        return
    files = list(trash_dir.iterdir())
    if not files:
        try:
            trash_dir.rmdir()
        except OSError:
            pass
        return
    if send2trash is None:
        print(
            f"[warning] send2trash is not installed - deleted files are still in "
            f"{trash_dir}"
        )
        return
    for f in files:
        try:
            send2trash(str(f))
        except Exception as e:
            print(f"[warning] failed to move {f.name} to system Trash: {e}")
    try:
        trash_dir.rmdir()
    except OSError:
        pass


# --------------------------------------------------------------------------
# Image preview
# --------------------------------------------------------------------------

def preview_tool():
    for tool in ("chafa", "viu"):
        if shutil.which(tool):
            return tool
    return None


def get_terminal_width():
    return shutil.get_terminal_size((80, 24)).columns


def visible_len(s: str) -> int:
    return len(ANSI_ESCAPE.sub("", s))


def _run_preview_tool(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return None
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout
    return None


def render_ascii_fallback_lines(path: Path, width: int):
    if Image is None:
        return [f"[no chafa/viu/Pillow available - cannot preview] ({path.name})"]
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        return [f"[could not open image: {e}]"]
    target_w = max(10, min(width, 50))
    aspect = img.height / img.width if img.width else 1
    target_h = max(1, min(int(target_w * aspect * 0.5), MAX_PREVIEW_HEIGHT))
    img = img.resize((target_w, target_h))
    lines = []
    for y in range(target_h):
        row = []
        for x in range(target_w):
            r, g, b = img.getpixel((x, y))
            row.append(f"\x1b[48;2;{r};{g};{b}m ")
        row.append("\x1b[0m")
        lines.append("".join(row))
    return lines


def get_image_lines(path: Path, width: int, mode: str = "sixels"):
    tool = preview_tool()
    # จำกัดขนาดทั้งความกว้างและความสูงไม่ให้เกินขอบเขต
    max_w = min(width, 55)
    max_h = MAX_PREVIEW_HEIGHT

    if tool == "chafa":
        fmt = "sixels" if mode == "sixels" else "symbols"
        output = _run_preview_tool(
            ["chafa", "-f", fmt, "--size", f"{max_w}x{max_h}", str(path)]
        )
        if output:
            return output.rstrip("\n").split("\n")
    elif tool == "viu":
        output = _run_preview_tool(["viu", "-w", str(max_w), "-h", str(max_h), str(path)])
        if output:
            return output.rstrip("\n").split("\n")
    return render_ascii_fallback_lines(path, max_w)


def view_full_image(path: Path):
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["cmd", "/c", "start", "/wait", "", str(path)])
        elif system == "Darwin":
            subprocess.run(["open", "-W", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])
            input("Viewer opened - press Enter here when you're done...")
    except Exception as e:
        print(f"[!] Could not open external viewer: {e}")
        input("Press Enter to continue...")


# --------------------------------------------------------------------------
# Move / delete with duplicate-name handling
# --------------------------------------------------------------------------

def move_with_dup_check(src: Path, dest_dir: Path, base: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src.name
    if dest_path.exists():
        print(f"\n[!] Filename '{src.name}' already exists in category '{dest_dir.name}'")
        while True:
            choice = input(
                "Choose: [1] delete this file (Trash)   [2] move to other (99_other) instead\n>> "
            ).strip()
            if choice == "1":
                trashed = soft_delete(src, base)
                return ("deleted", trashed)
            elif choice == "2":
                other_dir = base / f"{OTHER_NUMBER:02d}_{OTHER_NAME}"
                other_dir.mkdir(exist_ok=True)
                other_dest = unique_path(other_dir / src.name)
                shutil.move(str(src), str(other_dest))
                return ("moved", other_dest)
            else:
                print("Please type 1 or 2")
    else:
        shutil.move(str(src), str(dest_path))
        return ("moved", dest_path)


# --------------------------------------------------------------------------
# Undo
# --------------------------------------------------------------------------

def do_undo(history):
    if not history:
        print("[i] Nothing left to undo")
        return None
    entry = history.pop()
    dest = entry["dest_path"]
    original = entry["original_path"]
    try:
        shutil.move(str(dest), str(original))
    except Exception as e:
        print(f"[!] undo failed: {e}")
        history.append(entry)
        return None
    if entry.get("created_category"):
        parent = dest.parent
        try:
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass
    return entry["image_index"]


# --------------------------------------------------------------------------
# Command handling
# --------------------------------------------------------------------------

def handle_command(cmd_line, path, idx, history, base, state):
    cats = scan_categories(base)
    try:
        tokens = shlex.split(cmd_line)
    except ValueError:
        print("[!] Invalid command (unmatched quotes)")
        return "stay"
    if not tokens:
        return "stay"
    cmd = tokens[0]

    if cmd == "q":
        return "quit"

    if cmd == "v":
        view_full_image(path)
        return "redraw"

    if cmd == "h":
        state["show_help"] = not state["show_help"]
        return "redraw"

    if cmd == "c":
        state["show_all_cats"] = not state["show_all_cats"]
        return "redraw"

    if cmd == "s":
        state["preview_mode"] = "symbols" if state["preview_mode"] == "sixels" else "sixels"
        return "redraw"

    if cmd == "u":
        prev_idx = do_undo(history)
        if prev_idx is None:
            return "stay"
        return f"goto:{prev_idx}"

    if cmd == "d":
        dest = soft_delete(path, base)
        history.append(
            {
                "action": "deleted",
                "image_index": idx,
                "original_path": path,
                "dest_path": dest,
                "created_category": False,
            }
        )
        state["category_usage"]["d"] += 1
        return "advance"

    if cmd == "o":
        other_dir = base / f"{OTHER_NUMBER:02d}_{OTHER_NAME}"
        other_dir.mkdir(exist_ok=True)
        kind, dest = move_with_dup_check(path, other_dir, base)
        history.append(
            {
                "action": kind,
                "image_index": idx,
                "original_path": path,
                "dest_path": dest,
                "created_category": False,
            }
        )
        state["category_usage"][OTHER_NUMBER] += 1
        return "advance"

    if cmd == "n":
        try:
            name = input("New category name (Enter to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[!] Cancelled")
            return "stay"
            
        if not name:
            print("[!] Cancelled - no category created")
            return "stay"
            
        existing_lower = {n.lower() for n in cats.values()} | {OTHER_NAME.lower()}
        if name.lower() in existing_lower:
            print(f"[!] The name '{name}' is already in use - please pick another one")
            return "stay"
            
        num = next_free_number(cats)
        if num is None:
            print("[!] All categories (01-98) are used - cannot create a new one")
            return "stay"
            
        new_dir = base / f"{num:02d}_{name}"
        created_new = not new_dir.exists()
        new_dir.mkdir(exist_ok=True)
        kind, dest = move_with_dup_check(path, new_dir, base)
        history.append(
            {
                "action": kind,
                "image_index": idx,
                "original_path": path,
                "dest_path": dest,
                "created_category": created_new,
            }
        )
        state["category_usage"][num] += 1
        state["last_created_cat"] = num
        return "advance"

    if cmd.isdigit():
        num = int(cmd)
        if num == OTHER_NUMBER:
            return handle_command("o", path, idx, history, base, state)
        if num in cats:
            dest_dir = base / f"{num:02d}_{cats[num]}"
            kind, dest = move_with_dup_check(path, dest_dir, base)
            history.append(
                {
                    "action": kind,
                    "image_index": idx,
                    "original_path": path,
                    "dest_path": dest,
                    "created_category": False,
                }
            )
            state["category_usage"][num] += 1
            return "advance"
        else:
            print(f"[!] Category {num:02d} does not exist")
            return "stay"

    print(f"[!] Unknown command '{cmd}'")
    return "stay"


# --------------------------------------------------------------------------
# Repeat-last-command helpers
# --------------------------------------------------------------------------

def describe_command(cmd_line, base, state):
    if not cmd_line:
        return None
    tokens = cmd_line.split()
    if not tokens:
        return None
    first = tokens[0]
    if first == "d":
        return "delete"
    if first == "u":
        return "undo"
    if first == "o":
        return f"move to other ({OTHER_NUMBER:02d})"
    if first == "n" and state.get("last_created_cat"):
        num = state["last_created_cat"]
        cats = scan_categories(base)
        name = cats.get(num, "")
        return f"move to {num:02d} - {name}"
    if first.isdigit():
        num = int(first)
        if num == OTHER_NUMBER:
            return f"move to other ({OTHER_NUMBER:02d})"
        cats = scan_categories(base)
        name = cats.get(num)
        if name:
            return f"move to {num:02d} - {name}"
        return f"move to {num:02d}"
    return None


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

def clear_screen():
    sys.stdout.write("\x1b[2J\x1b[3J\x1b[H")
    sys.stdout.flush()


def build_category_grid(cats: dict, state: dict, total_width: int):
    if not cats:
        return ["Categories: (none yet)"]
    
    if not state["show_all_cats"] and state["category_usage"]:
        top_nums = [num for num, _ in state["category_usage"].most_common() if isinstance(num, int) and num in cats][:5]
        display_cats = {num: cats[num] for num in top_nums}
        title = f"Categories (Top-5 used, press 'c' to show all {len(cats)}):"
    else:
        display_cats = cats
        title = f"Categories (All {len(cats)}, press 'c' to filter Top-5):" if len(cats) > 5 else "Categories:"

    if not display_cats:
        display_cats = cats
        title = "Categories:"

    items = [f"{num:02d}-{display_cats[num]}" for num in sorted(display_cats)]
    lines = [title]
    current_line = "  "
    
    for item in items:
        if len(current_line) + len(item) + 3 > total_width:
            lines.append(current_line)
            current_line = f"  {item}"
        else:
            current_line += (", " if current_line.strip() else "") + item
    if current_line.strip():
        lines.append(current_line)
        
    return lines


def compose_columns(left_lines, right_lines, left_width, gutter=2):
    max_lines = max(len(left_lines), len(right_lines))
    output = []
    for i in range(max_lines):
        left = left_lines[i] if i < len(left_lines) else ""
        right = right_lines[i] if i < len(right_lines) else ""
        pad = left_width - visible_len(left)
        if pad > 0:
            left = left + " " * pad
        output.append(left + (" " * gutter) + right)
    return output


def get_command_lines(show_help: bool):
    if not show_help:
        return ["[Press 'h' to show commands]"]
    return [
        "Commands:",
        "  d       delete (Trash)",
        "  o       move to 99_other",
        "  n       create new category",
        "  <num>   move to category",
        "  u       undo last action",
        "  s       toggle sixel/symbols",
        "  v       view full-size",
        "  c       toggle categories",
        "  h       toggle help info",
        "  q       quit",
    ]


def draw_screen(path: Path, idx: int, total: int, base: Path, state: dict):
    cats = scan_categories(base)
    total_width = min(get_terminal_width(), 100)
    mode_str = state["preview_mode"].upper()

    print("=" * total_width)
    print(f" File: {path.name}   ({idx + 1}/{total})   [Mode: {mode_str}]")
    print("=" * total_width)
    print()

    cmd_lines = get_command_lines(state["show_help"])
    image_lines = get_image_lines(path, 50, state["preview_mode"])

    # โหมด Sixels: พิมพ์รูป แล้วพิมพ์ Commands บรรทัดถัดไปแบบแนวนอน/ระเบียบเรียบร้อยป้องกันการเบี้ยว
    if state["preview_mode"] == "sixels":
        for line in image_lines:
            print(line)
        print()
        if state["show_help"]:
            print("Commands:  d:delete  o:other  n:new  u:undo  s:mode  v:view  c:cats  h:hide  q:quit")
        else:
            print("[Press 'h' to show commands]")
    else:
        # โหมด Symbols: รวมคอลัมน์ Side-by-Side
        left_width = 50
        for line in compose_columns(image_lines, cmd_lines, left_width):
            print(line)

    print()
    print("-" * total_width)
    for line in build_category_grid(cats, state, total_width):
        print(line)
    print("-" * total_width)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    base = Path.cwd()
    images = sorted(
        p for p in base.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        print("No image files found in this directory")
        return

    print(f"Found {len(images)} image file(s) in {base}")
    if preview_tool() is None and Image is None:
        print(
            "[warning] Neither chafa/viu nor Pillow is installed "
            "- image previews will not be available"
        )
    try:
        input("Press Enter to start... ")
    except (EOFError, KeyboardInterrupt):
        return

    history = []
    current_index = 0
    last_shown = -1
    last_command = None

    state = {
        "show_help": True,
        "show_all_cats": False,
        "category_usage": Counter(),
        "last_created_cat": None,
        "preview_mode": "sixels",
    }

    while current_index < len(images):
        path = images[current_index]
        if not path.exists():
            current_index += 1
            continue

        if current_index != last_shown:
            clear_screen()
            draw_screen(path, current_index, len(images), base, state)
            last_shown = current_index

        hint = describe_command(last_command, base, state)
        prompt = f"(Enter = repeat: {hint})\n>> " if hint else ">> "

        try:
            cmd_line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting")
            break

        if not cmd_line:
            if last_command is None:
                print("[i] No previous command to repeat")
                continue
            if last_command == "n" and state["last_created_cat"]:
                cmd_line = str(state["last_created_cat"])
            else:
                cmd_line = last_command

        result = handle_command(cmd_line, path, current_index, history, base, state)
        first_token = cmd_line.split()[0] if cmd_line.split() else ""

        if result == "advance":
            current_index += 1
            if first_token in ("d", "o", "n") or first_token.isdigit():
                last_command = cmd_line
        elif result and result.startswith("goto:"):
            current_index = int(result.split(":")[1])
            last_shown = -1
            if first_token == "u":
                last_command = cmd_line
        elif result == "redraw":
            last_shown = -1
        elif result == "quit":
            break

    flush_trash_to_system(base)
    print("\nDone. Thanks for using sortimg!")


if __name__ == "__main__":
    main()