# sortimg — Sort photos from your terminal

`sortimg` shows the photos in a folder one at a time, right inside your terminal, and lets you file each one into a category (or delete it) with a single short command.

- Categories are just folders named `NN_name` (e.g. `01_screenshots`, `02_memories`)
- Deleted photos go to your system Trash (Recycle Bin on Windows), so nothing is lost for good
- Every action can be undone
- Works on **Windows (Git Bash)**, **macOS**, **Linux**, and **WSL**

---

## Recommended setup: Windows Terminal + Git Bash

For the best experience on Windows, run `sortimg` in **Windows Terminal** with **Git Bash** as the default profile. Windows Terminal 1.22 or newer supports Sixel graphics, which gives you full-color image previews.

### 1. Install the prerequisites

Open PowerShell and run:

```powershell
winget install --id Microsoft.WindowsTerminal --exact
winget install --id Git.Git --exact
winget install --id Python.Python.3.12 --exact
winget install --id hpjansson.Chafa --exact
```

(Skip any you already have. Chafa is optional but strongly recommended; see [Image previews](#image-previews).)

Then close and reopen your terminal so the new programs are on your PATH.

### 2. Set Git Bash as the default profile

1. Open **Windows Terminal**
2. Press `Ctrl` + `,` to open Settings
3. Under **Startup → Default profile**, choose **Git Bash**
4. Click **Save**

From now on, every new Windows Terminal tab opens Git Bash.

> If Git Bash is not in the list, open Settings → **Add a new profile** → **New empty profile**, set the command line to `C:\Program Files\Git\bin\bash.exe --login -i`, then choose it as the default.

---

## Install sortimg (one time)

1. Put these four files in the same folder, e.g. `~/Downloads/sortimg/`:
   - `sortimg.py`
   - `install.sh`
   - `requirements.txt`
   - `README.md`

2. Open a terminal (Git Bash on Windows) and go to that folder:

   ```bash
   cd ~/Downloads/sortimg
   ```

3. Install the Python dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

   (On macOS/Linux, use `pip3 install -r requirements.txt` or `python3 -m pip install -r requirements.txt`.)

4. Run the installer:

   ```bash
   chmod +x install.sh
   ./install.sh
   ```

   The installer will:
   - Copy `sortimg.py` to `~/.sortimg/sortimg.py`
   - Create a `sortimg` command at `~/.local/bin/sortimg`
   - Find a working Python (it skips the fake Microsoft Store `python3` stub on Windows)
   - Check that your dependencies are in place and tell you what's missing

5. If the installer says `~/.local/bin` is not in your PATH, add this line to the end of `~/.bashrc` (or `~/.zshrc` on macOS/zsh):

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

   Then reload it:

   ```bash
   source ~/.bashrc
   ```

   or just open a new terminal tab.

To update later, replace `sortimg.py` in the folder and run `./install.sh` again.

---

## Usage

Go to the folder that contains the photos you want to sort and run:

```bash
cd /path/to/your/photos
sortimg
```

`sortimg` scans the **current folder only** (not subfolders) for `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` and `.bmp` files. Press Enter to start, then for each photo type a command and press Enter.

### Commands

| Command | What it does |
|---|---|
| `01`, `02`, … | Move this photo into the category with that number |
| `n` | Create a new category (you'll be asked for its name) and move this photo into it |
| `f` | **Find** a category by part of its name, then move the photo there |
| `o` | Move to the `99_other` category (created automatically) |
| `d` | Delete this photo (goes to Trash when you exit) |
| `u` | **Undo** the last action. Repeat to keep stepping back |
| `v` | View this photo full-size in your default image viewer |
| `s` | Switch preview mode between **sixels** and **symbols** |
| `c` | Toggle showing the top-5 most-used categories / all categories |
| `h` | Show or hide the command help |
| `q` | Quit |

**Tip:** Pressing **Enter on an empty line repeats your last successful command** (`d`, `o`, `n`, a category number, or `u`). The prompt shows what will happen, e.g. `(Enter = repeat: move to 01 - screenshots)`. This makes sorting long runs of similar photos very fast.

### Typical session

```text
>> n
New category name (Enter to cancel): screenshots     # creates 01_screenshots, moves the photo
>> n
New category name (Enter to cancel): memories        # creates 02_memories
>> 01                                                # next photo → 01_screenshots
>> (just press Enter)                                # repeats: move to 01 - screenshots
>> d                                                 # delete a blurry one
>> u                                                 # oops, undo that
>> q
```

---

## How it works

- **Categories are real folders.** They are named `NN_name` with a number from `01` to `98`, e.g. `01_screenshots`. `sortimg` re-scans the folder names every time it starts, so there is no config file. You can rename, add, or remove category folders yourself between sessions.
- **Category numbers fill gaps first.** If `01` and `03` exist, the next new category becomes `02`.
- **Category names must be unique** (case-insensitive, and `other` is reserved). If you pick a name that's taken, you'll get a warning and can type another command.
- **`99_other` is the catch-all** for anything that doesn't fit. It is created the first time you use `o`.
- **Duplicate filenames are handled.** If a file with the same name already exists in the target category, you're asked whether to delete this one or move it to `99_other` instead.
- **Deleting is safe.** `d` first moves the photo into a hidden `.sortimg_trash` folder, so `u` can bring it back instantly. When you quit (`q`) or finish the last photo, everything in that folder is sent to the real system Trash. You can still restore it from the Trash / Recycle Bin.
- **Quitting with Ctrl+C** also exits cleanly and flushes pending deletes to Trash.

---

## Image previews

`sortimg` picks the best available previewer automatically:

1. **chafa** (best: sharp, full color, supports sixels)
2. **viu**
3. **Pillow** (built-in fallback: coarse color blocks, still usable)

Install chafa for the nicest result:

```bash
# Windows
winget install --id hpjansson.Chafa --exact

# macOS
brew install chafa

# Ubuntu / Debian
sudo apt install chafa
```

If previews look garbled or blank, press `s` to switch to **symbols** mode, which works in any terminal. Sixel mode needs a terminal that supports it (Windows Terminal 1.22+, iTerm2, WezTerm, foot, etc.).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `sortimg: command not found` | `~/.local/bin` isn't in your PATH. See step 5 of the install, then open a new terminal |
| Installer says "No working Python found" | Install Python from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH**, then reopen the terminal and rerun `./install.sh` |
| `send2trash not found` warning | Run `python -m pip install send2trash`. Until then, deleted files stay in `.sortimg_trash` inside your photo folder |
| Preview is blocky or low quality | Install `chafa` (see above) |
| Preview shows strange characters | Press `s` to switch to symbols mode, or upgrade Windows Terminal |
| "No image files found in this directory" | You're in the wrong folder, or the photos are in a subfolder. `cd` into the folder that directly contains them |
| `v` doesn't open a viewer (Linux) | Install `xdg-utils`, or make sure a default image viewer is set |

---

## Requirements

- Python 3
- `send2trash` and `pillow` (installed via `requirements.txt`)
- `bash` (Git Bash on Windows, or the default shell on macOS/Linux/WSL)
- Optional: `chafa` or `viu` for high-quality previews
