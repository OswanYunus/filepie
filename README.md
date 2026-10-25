# FilePie

**The radial pie-menu file converter for Windows.**

Right-click any file or folder in Windows Explorer, and an intuitive radial wheel (Blender pie-menu / Fortnite emote wheel style) pops up centered right on your cursor with only the conversions relevant to that file.

---

## Download & Install (Zero Setup)

1. Go to **[Releases](https://github.com/OswanYunus/filepie/releases)**.
2. Download **`FilePie_Setup_v1.0.3.exe`**.
3. Run the installer and finish the setup wizard.
4. **Done!** No Python, no terminal, no `pip install` required.

---

## How to Use

1. In Windows Explorer, **right-click** any file or folder.
   *(On Windows 11, click "Show more options" or press `Shift + F10`)*.
2. Click **Convert with FilePie**.
3. Move your mouse toward any wedge on the circular wheel and **click to convert**.
4. A notification appears when the converted file is ready right next to the original!

---

## Supported Conversions Out of the Box

| File Type | Available Conversions |
|-----------|------------------------|
| **PDF** (`.pdf`) | First page to PNG / JPG, Extract full text (`.txt`), All pages to PNGs |
| **Documents** (`.docx`, `.odt`, `.rtf`) | Formatted PDF, Plain text (`.txt`) |
| **Web** (`.html`, `.htm`) | Render to PDF, Clean plain text (`.txt`) |
| **Markdown** (`.md`, `.markdown`) | Formatted PDF, Styled HTML page, Plain text |
| **Code** (`.py`, `.js`, `.ts`, `.cpp`, `.cs`, `.sql`, etc.) | Monospace formatted PDF with pagination |
| **Images** (`.jpg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.ico`, etc.) | PNG, JPG, WebP, BMP, GIF, TIFF, PDF, ICO |
| **Video** (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, etc.) | MP4, MKV, AVI, MOV, WebM, GIF, Extract MP3 Audio |
| **Audio** (`.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a`, etc.) | MP3, WAV, FLAC, AAC, OGG, M4A |
| **Archives** (`.zip`) | Extract Here |
| **Folders** | Compress to ZIP |
| **3D Models** (`.blend`) | OBJ, FBX, GLTF, STL (requires Blender path) |

---

## Customizing Formats & Targets

All file formats and conversions are driven by a simple `config.json` installed alongside the app. You can add new extensions, target formats, or custom command triggers at any time without recompiling.

---

## Building from Source (Developers Only)

If you wish to run or modify the Python source directly:

```powershell
git clone https://github.com/OswanYunus/filepie.git
cd filepie
pip install -r requirements.txt
python main.py
```

To compile the standalone installer yourself:
```powershell
pyinstaller FilePie.spec
ISCC installer.iss
```
