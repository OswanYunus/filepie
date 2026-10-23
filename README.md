# FilePie

Select a file in Windows Explorer, hit a hotkey, and a radial menu (Blender
pie-menu / Fortnite-emote-wheel style) pops up around your cursor showing
only the conversions that make sense for *that* file — a jpg never shows
you audio formats, an mp4 never shows you image formats.

## What it does out of the box

| You select...      | Menu shows...                                   |
|---------------------|--------------------------------------------------|
| .mp4/.mkv/.avi/...   | other video formats + "Extract MP3"             |
| .mp3/.wav/.flac/...  | other audio formats                             |
| .jpg/.png/.webp/...  | other image formats                             |
| .blend               | .obj / .fbx / .gltf / .stl                      |
| a folder             | "Compress to ZIP"                               |
| .zip                 | "Extract Here"                                  |

All of this is driven by `config.json` — see "Adding more file types" below.

## 1. Install Python dependencies

You need Python 3.9+ on Windows. Then:

```
pip install -r requirements.txt
```

## 2. Install ffmpeg (for video/audio conversion)

Download a Windows build from https://ffmpeg.org/download.html, unzip it
somewhere, and either:
- add the folder containing `ffmpeg.exe` to your system PATH, **or**
- open `config.json` and set `"ffmpeg_path"` to the full path of `ffmpeg.exe`.

Without this, video/audio conversions will fail gracefully (you'll get a
tray notification explaining why) — the app won't crash.

## 3. (Optional) Point it at Blender

Only needed if you want .blend exports. Open `config.json` and set
`"blender_path"` to your actual `blender.exe` location, e.g.:

```
"blender_path": "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe"
```

## 4. Run it

```
python main.py
```

It sits quietly in your system tray (bottom-right, near the clock). Right-click
the tray icon to see the current shortcut, open the config, or exit.

## 5. Use it

1. In File Explorer, click once on a file (or folder, or .zip) to select it.
2. Press **Ctrl+Alt+Space** (the default — change it in `config.json`).
3. A circle appears around your cursor. Move the mouse toward a wedge to
   highlight it, click to pick it. Click outside the circle or press Esc
   to cancel.
4. The conversion runs in the background — you'll get a tray notification
   when it's done, with the path to the new file saved alongside the original.

## Run it automatically on login

Press `Win+R`, type `shell:startup`, hit Enter. Drop a shortcut to
`main.py` (or better, a shortcut to `pythonw.exe main.py` so no console
window appears) into that folder.

## Adding more file types

Everything is config-driven — you don't need to touch the Python code to
support a new extension. Open `config.json` and either add extensions to
an existing category, or add a new category:

```json
"document": {
  "extensions": ["docx", "odt"],
  "targets": ["pdf"],
  "extra": []
}
```

Note: a target format needs an actual converter behind it. The ones wired
up today are ffmpeg (video/audio), Pillow (images), zipfile (zip/unzip),
and Blender (blend exports). Adding a converter for a brand-new tool (e.g.
pandoc for documents) means adding a small function in `conversions.py` —
the pattern for each existing converter is there to copy.

## Packaging as a standalone .exe (optional)

If you don't want to keep a Python install around:

```
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "config.json;." --add-data "blender_export.py;." main.py
```

The result lands in `dist/main.exe`. Keep `config.json` next to it (or
re-add it after building) since it's meant to be user-editable.

## Troubleshooting

- **Nothing happens when I press the hotkey** — make sure a file/folder is
  actually clicked (selected) in the Explorer window that's focused, not
  just hovered.
- **"keyboard" hotkey doesn't fire at all** — some setups need the script
  run as Administrator for global key hooks. Try right-click →
  "Run as administrator" on a shortcut to `python.exe main.py`.
- **ffmpeg / blender errors** — the tray notification shows the actual
  error message (truncated) so you can see what went wrong without digging
  through logs.
