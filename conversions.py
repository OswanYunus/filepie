"""All conversion logic lives here, driven entirely by config.json.

To support a new file type, you do NOT need to touch this file: just add a
category to config.json with its extensions and target formats. You only
need to edit this file if a new target needs a genuinely new converter
(e.g. a new tool beyond ffmpeg / Pillow / zipfile / blender).
"""
import os
import shutil
import subprocess
import zipfile
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_category(path, cfg):
    """Which config category this path belongs to, or None if unsupported."""
    if os.path.isdir(path):
        return "folder"
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    for name, rule in cfg["categories"].items():
        if ext in rule.get("extensions", []):
            return name
    return None


def get_options_for(path, cfg):
    """Return [(label, target_value), ...] for the pie menu. Empty list
    means: this file type isn't recognized, don't show a menu at all —
    this is what stops a jpg from ever offering mp3 as an option."""
    category = get_category(path, cfg)
    if category is None:
        return []
    rule = cfg["categories"][category]
    current_ext = os.path.splitext(path)[1].lower().lstrip(".")

    options = []
    for target in rule.get("targets", []):
        if target == current_ext:
            continue  # never offer to "convert" a file to its own format
        options.append((target.upper(), target))
    for label, value in rule.get("extra", []):
        options.append((label, value))
    return options


def _no_window_flags():
    # Keeps ffmpeg/blender from flashing a console window on Windows.
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def run_conversion(path, target, cfg):
    """Dispatch to the right converter. Always returns (success, message)
    instead of raising, so a bad conversion never takes the app down."""
    try:
        category = get_category(path, cfg)
        if category == "folder":
            return _zip_folder(path)
        if category == "archive" and target == "extract":
            return _unzip(path)
        if category == "video":
            if target == "extract_audio_mp3":
                return _ffmpeg_extract_audio(path, cfg)
            return _ffmpeg_convert(path, target, cfg)
        if category == "audio":
            return _ffmpeg_convert(path, target, cfg)
        if category == "image":
            return _image_convert(path, target)
        if category == "blend":
            return _blend_export(path, target, cfg)
        return False, f"No converter registered for category '{category}'."
    except Exception as exc:  # belt and braces: never crash the app
        return False, f"Conversion failed: {exc}"


def _output_path(path, target_ext):
    base, _ = os.path.splitext(path)
    out = f"{base}.{target_ext}"
    counter = 1
    while os.path.exists(out):
        out = f"{base} ({counter}).{target_ext}"
        counter += 1
    return out


def _ffmpeg_convert(path, target_ext, cfg):
    ffmpeg = cfg.get("ffmpeg_path", "ffmpeg")
    out = _output_path(path, target_ext)
    cmd = [ffmpeg, "-y", "-i", path, out]
    result = subprocess.run(cmd, capture_output=True, text=True, **_no_window_flags())
    if result.returncode != 0 or not os.path.exists(out):
        return False, "ffmpeg failed — is ffmpeg installed and on PATH?\n" + result.stderr[-500:]
    return True, f"Saved to {out}"


def _ffmpeg_extract_audio(path, cfg):
    ffmpeg = cfg.get("ffmpeg_path", "ffmpeg")
    out = _output_path(path, "mp3")
    cmd = [ffmpeg, "-y", "-i", path, "-vn", "-acodec", "libmp3lame", out]
    result = subprocess.run(cmd, capture_output=True, text=True, **_no_window_flags())
    if result.returncode != 0 or not os.path.exists(out):
        return False, "ffmpeg failed — is ffmpeg installed and on PATH?\n" + result.stderr[-500:]
    return True, f"Saved to {out}"


def _image_convert(path, target_ext):
    from PIL import Image

    out = _output_path(path, target_ext)
    img = Image.open(path)
    if target_ext in ("jpg", "jpeg") and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")  # jpg has no alpha channel
    save_format = "JPEG" if target_ext in ("jpg", "jpeg") else target_ext.upper()
    img.save(out, format=save_format)
    return True, f"Saved to {out}"


def _zip_folder(folder_path):
    base = folder_path.rstrip("\\/")
    out = base + ".zip"
    counter = 1
    while os.path.exists(out):
        out = f"{base} ({counter}).zip"
        counter += 1
    shutil.make_archive(out[:-4], "zip", base)
    return True, f"Zipped to {out}"


def _unzip(zip_path):
    base, _ = os.path.splitext(zip_path)
    out_dir = base
    counter = 1
    while os.path.exists(out_dir):
        out_dir = f"{base} ({counter})"
        counter += 1
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    return True, f"Extracted to {out_dir}"


def _blend_export(path, target_ext, cfg):
    blender = cfg.get("blender_path")
    if not blender or not os.path.exists(blender):
        return False, (
            "Blender path not set or wrong. Edit config.json and set "
            "'blender_path' to your blender.exe location."
        )
    out = _output_path(path, target_ext)
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_export.py")
    cmd = [blender, "--background", path, "--python", script, "--", out, target_ext]
    result = subprocess.run(cmd, capture_output=True, text=True, **_no_window_flags())
    if result.returncode != 0 or not os.path.exists(out):
        return False, "Blender export failed:\n" + result.stdout[-400:] + "\n" + result.stderr[-300:]
    return True, f"Saved to {out}"
