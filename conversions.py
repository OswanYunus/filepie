"""All conversion logic lives here, driven entirely by config.json.

Converters wired up:
  ffmpeg        → video/audio conversions
  Pillow        → image conversions
  PyMuPDF       → PDF → images / text
  pdf2docx      → PDF → DOCX
  fpdf2         → anything text-like → PDF
  python-docx   → DOCX → text
  beautifulsoup → HTML → text
  markdown      → MD → HTML
  zipfile       → zip/unzip
  Blender       → blend exports
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

        # ---- folders / archives ----
        if category == "folder":
            return _zip_folder(path)
        if category == "archive" and target == "extract":
            return _unzip(path)

        # ---- video ----
        if category == "video":
            if target == "extract_audio_mp3":
                return _ffmpeg_extract_audio(path, cfg)
            if target == "gif":
                return _ffmpeg_to_gif(path, cfg)
            return _ffmpeg_convert(path, target, cfg)

        # ---- audio ----
        if category == "audio":
            return _ffmpeg_convert(path, target, cfg)

        # ---- images ----
        if category == "image":
            if target == "pdf":
                return _image_to_pdf(path)
            return _image_convert(path, target)

        # ---- PDF ----
        if category == "pdf":
            if target == "png" or target == "jpg":
                return _pdf_to_image(path, target, first_page_only=True)
            if target == "pdf_all_png":
                return _pdf_to_image(path, "png", first_page_only=False)
            if target == "txt":
                return _pdf_to_text(path)
            if target == "docx":
                return _pdf_to_docx(path)

        # ---- documents (docx, doc, odt, rtf) ----
        if category == "document":
            if target == "pdf":
                return _document_to_pdf(path)
            if target == "txt":
                return _document_to_text(path)

        # ---- plaintext / code / json_data ----
        if category in ("plaintext", "code", "json_data"):
            if target == "pdf":
                return _text_to_pdf(path)
            if target == "txt":
                return _file_copy_as(path, "txt")

        # ---- markdown ----
        if category == "markdown":
            if target == "pdf":
                return _markdown_to_pdf(path)
            if target == "html":
                return _markdown_to_html(path)
            if target == "txt":
                return _file_to_plain_text(path)

        # ---- web (html, htm) ----
        if category == "web":
            if target == "pdf":
                return _html_to_pdf(path)
            if target == "txt":
                return _html_to_text(path)

        # ---- spreadsheet ----
        if category == "spreadsheet":
            if target == "pdf":
                return _text_to_pdf(path)
            if target == "xlsx":
                return _csv_to_xlsx(path)

        # ---- blender ----
        if category == "blend":
            return _blend_export(path, target, cfg)

        return False, f"No converter registered for category '{category}' → '{target}'."
    except Exception as exc:  # belt and braces: never crash the app
        return False, f"Conversion failed: {exc}"


# ---- output path helper ------------------------------------------------

def _output_path(path, target_ext):
    base, _ = os.path.splitext(path)
    out = f"{base}.{target_ext}"
    counter = 1
    while os.path.exists(out):
        out = f"{base} ({counter}).{target_ext}"
        counter += 1
    return out


def _output_dir(path, suffix=""):
    base, _ = os.path.splitext(path)
    out = base + suffix
    counter = 1
    while os.path.exists(out):
        out = f"{base}{suffix} ({counter})"
        counter += 1
    os.makedirs(out, exist_ok=True)
    return out


# ---- ffmpeg converters --------------------------------------------------

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


def _ffmpeg_to_gif(path, cfg):
    ffmpeg = cfg.get("ffmpeg_path", "ffmpeg")
    out = _output_path(path, "gif")
    # Make a reasonable quality GIF: 480px wide, 15fps, first 10 seconds
    cmd = [
        ffmpeg, "-y", "-i", path,
        "-t", "10",
        "-vf", "fps=15,scale=480:-1:flags=lanczos",
        "-loop", "0",
        out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, **_no_window_flags())
    if result.returncode != 0 or not os.path.exists(out):
        return False, "ffmpeg failed — is ffmpeg installed and on PATH?\n" + result.stderr[-500:]
    return True, f"Saved to {out}"


# ---- image converters ---------------------------------------------------

def _image_convert(path, target_ext):
    from PIL import Image

    out = _output_path(path, target_ext)
    img = Image.open(path)
    if target_ext in ("jpg", "jpeg") and img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")  # jpg has no alpha channel
    if target_ext == "ico":
        img = img.convert("RGBA")
        img.save(out, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        return True, f"Saved to {out}"
    save_format = "JPEG" if target_ext in ("jpg", "jpeg") else target_ext.upper()
    img.save(out, format=save_format)
    return True, f"Saved to {out}"


def _image_to_pdf(path):
    from PIL import Image

    out = _output_path(path, "pdf")
    img = Image.open(path)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(out, "PDF")
    return True, f"Saved to {out}"


# ---- PDF converters -----------------------------------------------------

def _pdf_to_image(path, target_ext, first_page_only=True):
    try:
        import fitz
    except ImportError:
        return False, "PyMuPDF (fitz) is required for PDF to image rendering."

    doc = fitz.open(path)
    if first_page_only:
        out = _output_path(path, target_ext)
        page = doc[0]
        mat = fitz.Matrix(3, 3)
        pix = page.get_pixmap(matrix=mat)
        if target_ext == "jpg":
            pix.save(out, output="jpeg")
        else:
            pix.save(out)
        doc.close()
        return True, f"Saved to {out} (page 1 of {len(doc)})"
    else:
        out_dir = _output_dir(path, "_pages")
        for i, page in enumerate(doc):
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            page_file = os.path.join(out_dir, f"page_{i + 1:03d}.{target_ext}")
            if target_ext == "jpg":
                pix.save(page_file, output="jpeg")
            else:
                pix.save(page_file)
        doc.close()
        return True, f"Saved {len(doc)} pages to {out_dir}"


def _pdf_to_text(path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        out = _output_path(path, "txt")
        text_parts = [page.extract_text() or "" for page in reader.pages]
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n\n".join(text_parts))
        return True, f"Saved to {out} ({len(text_parts)} pages extracted)"
    except Exception:
        # Fallback to fitz if pypdf has an issue
        import fitz
        doc = fitz.open(path)
        out = _output_path(path, "txt")
        text_parts = [page.get_text() for page in doc]
        doc.close()
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n\n".join(text_parts))
        return True, f"Saved to {out} ({len(text_parts)} pages extracted)"


def _pdf_to_docx(path):
    try:
        from pypdf import PdfReader
        from docx import Document

        out = _output_path(path, "docx")
        reader = PdfReader(path)
        doc = Document()

        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue
                # If short line and in uppercase, treat as potential heading
                if line_str.isupper() and len(line_str) < 60:
                    doc.add_heading(line_str, level=2)
                else:
                    doc.add_paragraph(line_str)
            if page_idx < len(reader.pages) - 1:
                doc.add_page_break()

        doc.save(out)
        return True, f"Saved to {out}"
    except Exception as e:
        return False, f"PDF to DOCX conversion failed: {e}"


# ---- document converters ------------------------------------------------

# ---- PDF helper with Unicode font support -------------------------------

def _create_unicode_pdf():
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    windir = os.environ.get("WINDIR", "C:\\Windows")
    fonts_dir = os.path.join(windir, "Fonts")

    arial = os.path.join(fonts_dir, "arial.ttf")
    arial_bd = os.path.join(fonts_dir, "arialbd.ttf")
    consola = os.path.join(fonts_dir, "consola.ttf")

    has_sans = False
    has_mono = False

    if os.path.exists(arial):
        try:
            pdf.add_font("Sans", "", arial)
            if os.path.exists(arial_bd):
                pdf.add_font("Sans", "B", arial_bd)
            else:
                pdf.add_font("Sans", "B", arial)
            has_sans = True
        except Exception:
            pass

    if os.path.exists(consola):
        try:
            pdf.add_font("Mono", "", consola)
            has_mono = True
        except Exception:
            pass

    return pdf, has_sans, has_mono


def _sanitize_pdf_text(text):
    """Normalize common unicode characters like em-dashes and smart quotes
    so they render seamlessly even if a fallback font is used."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
        "\u200b": "",     # zero-width space
        "\ufeff": "",     # byte order mark
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _document_to_text(path):
    ext = os.path.splitext(path)[1].lower()
    out = _output_path(path, "txt")

    if ext == ".docx":
        from docx import Document
        doc = Document(path)
        text = "\n\n".join(p.text for p in doc.paragraphs)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        return True, f"Saved to {out}"

    # For other doc formats, try reading as text
    return _file_to_plain_text(path)


def _document_to_pdf(path):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".docx":
        return _docx_to_pdf(path)

    # For other formats, convert to text first then to PDF
    return _text_to_pdf(path)


def _docx_to_pdf(path):
    from docx import Document

    doc = Document(path)
    out = _output_path(path, "pdf")

    pdf, has_sans, _ = _create_unicode_pdf()
    pdf.add_page()
    font_name = "Sans" if has_sans else "Helvetica"
    pdf.set_font(font_name, size=11)

    for para in doc.paragraphs:
        text = _sanitize_pdf_text(para.text.strip())
        if not text:
            pdf.ln(4)
            continue
        # Detect headings
        if para.style and para.style.name and "Heading" in para.style.name:
            pdf.set_font(font_name, "B", size=14)
            pdf.multi_cell(w=pdf.epw, h=7, text=text)
            pdf.set_font(font_name, size=11)
            pdf.ln(2)
        else:
            pdf.multi_cell(w=pdf.epw, h=6, text=text)
            pdf.ln(1)

    pdf.output(out)
    return True, f"Saved to {out}"


# ---- text / code → PDF --------------------------------------------------

def _text_to_pdf(path):
    out = _output_path(path, "pdf")
    ext = os.path.splitext(path)[1].lower()

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pdf, has_sans, has_mono = _create_unicode_pdf()
    pdf.add_page()

    filename = os.path.basename(path)
    body_font = "Sans" if has_sans else "Helvetica"
    mono_font = "Mono" if has_mono else ("Courier" if not has_sans else "Sans")

    pdf.set_font(body_font, "B", size=12)
    pdf.cell(0, 10, filename, ln=True)
    pdf.ln(4)

    # Use monospace font for code files
    code_exts = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs", ".go",
                 ".rs", ".rb", ".php", ".swift", ".kt", ".sh", ".bat", ".ps1",
                 ".sql", ".r", ".lua", ".dart", ".scala", ".json", ".xml",
                 ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".csv", ".tsv"}
    if ext in code_exts:
        pdf.set_font(mono_font, size=9)
        line_height = 4.5
    else:
        pdf.set_font(body_font, size=11)
        line_height = 6

    for line in content.split("\n"):
        line = _sanitize_pdf_text(line.replace("\r", "").replace("\t", "    "))
        pdf.multi_cell(w=pdf.epw, h=line_height, text=line)

    pdf.output(out)
    return True, f"Saved to {out}"


# ---- markdown converters ------------------------------------------------

def _markdown_to_html(path):
    import markdown

    out = _output_path(path, "html")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        md_content = f.read()

    html_body = markdown.markdown(md_content, extensions=["tables", "fenced_code"])
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{os.path.basename(path)}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #333; }}
  pre {{ background: #f4f4f4; padding: 12px; border-radius: 6px; overflow-x: auto; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background: #f0f0f0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return True, f"Saved to {out}"


def _markdown_to_pdf(path):
    out = _output_path(path, "pdf")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pdf, has_sans, _ = _create_unicode_pdf()
    pdf.add_page()
    font_name = "Sans" if has_sans else "Helvetica"
    pdf.set_font(font_name, size=11)

    for line in content.split("\n"):
        line = _sanitize_pdf_text(line.replace("\r", "").replace("\t", "    "))
        # Simple markdown heading detection
        if line.startswith("# "):
            pdf.set_font(font_name, "B", size=18)
            pdf.multi_cell(w=pdf.epw, h=10, text=line[2:])
            pdf.set_font(font_name, size=11)
        elif line.startswith("## "):
            pdf.set_font(font_name, "B", size=15)
            pdf.multi_cell(w=pdf.epw, h=8, text=line[3:])
            pdf.set_font(font_name, size=11)
        elif line.startswith("### "):
            pdf.set_font(font_name, "B", size=13)
            pdf.multi_cell(w=pdf.epw, h=7, text=line[4:])
            pdf.set_font(font_name, size=11)
        elif line.strip() == "":
            pdf.ln(4)
        else:
            pdf.multi_cell(w=pdf.epw, h=6, text=line)

    pdf.output(out)
    return True, f"Saved to {out}"


# ---- HTML converters ----------------------------------------------------

def _html_to_text(path):
    from bs4 import BeautifulSoup

    out = _output_path(path, "txt")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Clean up blank lines
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    return True, f"Saved to {out}"


def _html_to_pdf(path):
    out = _output_path(path, "pdf")

    # Method 1: High-fidelity rendering via built-in Chromium (Edge/Chrome)
    # This preserves exact CSS layout, logos, grids, and typography identical to web view.
    browser_candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google\\Chrome\\Application\\chrome.exe"),
    ]

    for browser in browser_candidates:
        if os.path.exists(browser):
            try:
                cmd = [
                    browser,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={out}",
                    os.path.abspath(path),
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15, **_no_window_flags())
                if os.path.exists(out) and os.path.getsize(out) > 0:
                    return True, f"Saved to {out}"
            except Exception:
                pass

    # Method 2: Fallback text-based PDF via BeautifulSoup and FPDF
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")

    pdf, has_sans, _ = _create_unicode_pdf()
    pdf.add_page()
    font_name = "Sans" if has_sans else "Helvetica"
    pdf.set_font(font_name, size=10)

    for line in text.split("\n"):
        line = _sanitize_pdf_text(line.strip().replace("\t", "    "))
        if line:
            pdf.multi_cell(w=pdf.epw, h=6, text=line)
        else:
            pdf.ln(3)

    pdf.output(out)
    return True, f"Saved to {out}"


# ---- CSV → XLSX ---------------------------------------------------------

def _csv_to_xlsx(path):
    """Convert CSV to XLSX using openpyxl if available, otherwise fall back."""
    try:
        import openpyxl
    except ImportError:
        return False, "openpyxl is needed for CSV→XLSX. Run: pip install openpyxl"

    import csv

    out = _output_path(path, "xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            ws.append(row)

    wb.save(out)
    return True, f"Saved to {out}"


# ---- plain text helpers -------------------------------------------------

def _file_to_plain_text(path):
    out = _output_path(path, "txt")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    return True, f"Saved to {out}"


def _file_copy_as(path, target_ext):
    out = _output_path(path, target_ext)
    shutil.copy2(path, out)
    return True, f"Saved to {out}"


# ---- zip / unzip --------------------------------------------------------

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


# ---- blender export -----------------------------------------------------

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
