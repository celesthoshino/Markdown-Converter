"""
Markdown Converter
------------------
Put Markdown (.md) files in the "input" folder, run this script, and web pages
(HTML) and/or PDFs show up in the "output" folder.

    python convert_markdown.py                 # asks: html, pdf or both
    python convert_markdown.py html            # web pages only
    python convert_markdown.py pdf             # PDFs only (uses Edge or Chrome)
    python convert_markdown.py pdf --toc       # PDFs with a table of contents

See README.md for all the details.
"""

import argparse
import base64
import html
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

try:
    from markdown_it import MarkdownIt
    from mdit_py_plugins.anchors import anchors_plugin
    from mdit_py_plugins.footnote import footnote_plugin
    from mdit_py_plugins.tasklists import tasklists_plugin
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound
except ImportError:
    sys.exit("Error: the required packages are not installed.\n"
             "Fix it by running:  pip install -r requirements.txt")

# The input/output folders live next to this script, so it works no matter
# which folder you run it from.
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

FORMATS = {"html": ".html", "pdf": ".pdf"}
INPUT_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
PAPER_SIZES = {"a4": "A4", "letter": "letter"}

BROWSER_NAMES = ["msedge", "chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge"]
BROWSER_LOCATIONS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

STYLE = """
body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.6;
       color: #1f2328; max-width: 860px; margin: 2em auto; padding: 0 1.5em; }
h1, h2 { border-bottom: 1px solid #d8dee4; padding-bottom: .3em; }
h1, h2, h3, h4 { margin-top: 1.5em; line-height: 1.25; }
a { color: #0969da; }
code { font-family: Consolas, "Courier New", monospace; font-size: 85%; background: #eff1f3;
       padding: .2em .4em; border-radius: 6px; }
pre { background: #f6f8fa; padding: 1em; border-radius: 6px; overflow-x: auto; line-height: 1.45; }
pre code { background: none; padding: 0; font-size: 85%; }
blockquote { margin: 0; padding: 0 1em; color: #59636e; border-left: .25em solid #d1d9e0; }
table { border-collapse: collapse; margin: 1em 0; display: block; overflow-x: auto; }
th, td { border: 1px solid #d1d9e0; padding: 6px 13px; }
th { background: #f6f8fa; }
tr:nth-child(even) td { background: #f9fafb; }
img { max-width: 100%; }
hr { border: 0; border-top: 1px solid #d1d9e0; margin: 2em 0; }
li.task-list-item { list-style: none; margin-left: -1.3em; }
.toc { background: #f6f8fa; border-radius: 6px; padding: .8em 1.5em; margin-bottom: 2em; }
.toc ul { margin: .2em 0; }
.footnotes { font-size: 90%; color: #59636e; }

@page { size: PAPER; margin: 18mm 16mm; }
@media print {
  body { max-width: none; margin: 0; padding: 0; font-size: 11pt; }
  pre, blockquote, tr, img, table { break-inside: avoid; }
  h1, h2, h3, h4 { break-after: avoid; }
  a { color: inherit; }
}
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}
{code_style}</style>
</head>
<body>
{toc}{body}
</body>
</html>
"""


def find_browser():
    """Microsoft Edge or Google Chrome, which can print web pages to PDF without opening a window."""
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    for location in BROWSER_LOCATIONS:
        if Path(location).exists():
            return location
    return None


def embed_images(page: str, folder: Path, warnings: list) -> str:
    """Put local images inside the page, so the HTML file works on its own and the PDF shows them."""
    def replace(match):
        src = match[2]
        if re.match(r"^(https?:|data:|//)", src):
            return match[0]  # images from the internet stay as links
        path = (folder / unquote(src)).resolve()
        mime = mimetypes.guess_type(path.name)[0]
        if not path.is_file() or not mime or not mime.startswith("image/"):
            warnings.append(f"image not found: {src}")
            return match[0]
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'{match[1]}data:{mime};base64,{data}"'
    return re.sub(r'(<img\b[^>]*?\bsrc=")([^"]+)"', replace, page)


def color_code(code: str, language: str, _attrs) -> str:
    """Color the code in ```python blocks. Unknown languages are shown plain."""
    try:
        lexer = get_lexer_by_name(language.strip())
    except ClassNotFound:
        return ""  # empty means "no coloring"
    return highlight(code, lexer, HtmlFormatter(nowrap=True))


def make_converter() -> MarkdownIt:
    # "commonmark" is the same Markdown standard GitHub uses, plus GitHub's extras:
    # tables, ~~strikethrough~~, footnotes, task lists and links to headings.
    return (MarkdownIt("commonmark", {"html": True, "highlight": color_code})
            .enable(["table", "strikethrough"])
            .use(footnote_plugin)
            .use(tasklists_plugin)
            .use(anchors_plugin, min_level=1, max_level=3))


def table_of_contents(body: str) -> str:
    """A nested list of links to the headings (levels 1-3) in the page."""
    headings = re.findall(r'<h([1-3]) id="([^"]+)">(.*?)</h\1>', body, re.S)
    if len(headings) < 2:
        return ""
    lowest = min(int(level) for level, _, _ in headings)
    parts, depth = [], 0
    for level, anchor, text in headings:
        level = int(level) - lowest + 1
        while depth < level:
            parts.append("<ul>")
            depth += 1
        while depth > level:
            parts.append("</ul>")
            depth -= 1
        parts.append(f'<li><a href="#{anchor}">{re.sub(r"<[^>]+>", "", text)}</a></li>')
    parts.append("</ul>" * depth)
    return f'<nav class="toc">{"".join(parts)}</nav>\n'


def to_html(src: Path, paper: str, with_toc: bool, warnings: list) -> str:
    """Turn one Markdown file into a complete web page."""
    text = src.read_text(encoding="utf-8-sig", errors="replace")
    body = make_converter().render(text)

    # Links to other Markdown files point to their converted web pages instead.
    body = re.sub(r'href="(?![a-z]+:)([^"#]+)\.(?:md|markdown)(#[^"]*)?"',
                  lambda m: f'href="{m[1]}.html{m[2] or ""}"', body)

    heading = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", heading[1])).strip() if heading else src.stem

    page = PAGE.format(
        title=html.escape(title),
        style=STYLE.replace("PAPER", PAPER_SIZES[paper]),
        code_style=HtmlFormatter(style="default").get_style_defs("pre"),
        toc=table_of_contents(body) if with_toc else "",
        body=body,
    )
    return embed_images(page, src.parent, warnings)


def print_to_pdf(browser: str, page_html: str, out_path: Path):
    """Have Edge/Chrome open the page without showing a window and save it as a PDF."""
    with tempfile.TemporaryDirectory() as temp:
        page_file = Path(temp, "page.html")
        page_file.write_text(page_html, encoding="utf-8")
        command = [
            browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions",
            f"--user-data-dir={Path(temp, 'profile')}",  # separate from your normal browser
            "--no-pdf-header-footer", "--print-to-pdf-no-header",  # no date/URL printed on each page
            f"--print-to-pdf={out_path}", page_file.as_uri(),
        ]
        out_path.unlink(missing_ok=True)
        try:
            subprocess.run(command, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            raise RuntimeError("the browser took longer than 2 minutes and was stopped") from None
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("the browser couldn't make the PDF")


def kb(size: int) -> str:
    return f"{size / 1024:,.0f} KB"


def clean_formats(words: list[str]) -> list[str]:
    formats = []
    for word in words:
        for part in word.replace(",", " ").split():
            fmt = part.lower().lstrip(".")
            fmt = {"htm": "html", "web": "html"}.get(fmt, fmt)
            if fmt not in formats:
                formats.append(fmt)
    return formats


def ask_formats() -> list[str]:
    print()
    while True:
        answer = input("Make web pages (html), PDFs (pdf), or both (all)? ").strip().lower()
        if answer in ("all", "both"):
            return list(FORMATS)
        formats = clean_formats([answer])
        if formats and all(f in FORMATS for f in formats):
            return formats
        print("  Please type html, pdf or all.")


def find_input_files(input_dir: Path) -> list[Path]:
    """Return the Markdown files in input_dir. Other files are listed as ignored."""
    files = []
    for path in sorted(input_dir.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in INPUT_EXTENSIONS:
            files.append(path)
        elif not mimetypes.guess_type(path.name)[0] or not mimetypes.guess_type(path.name)[0].startswith("image/"):
            print(f"  [ignored] {path.name} (not a Markdown file)")  # images are used by the pages, so not listed
    return files


def main():
    parser = argparse.ArgumentParser(description="Turn every Markdown file in the input folder into a web page and/or PDF.")
    parser.add_argument("formats", nargs="*", help="html, pdf, or both")
    parser.add_argument("--all", action="store_true", help="make both web pages and PDFs")
    parser.add_argument("--paper", choices=PAPER_SIZES, default="a4", help="PDF page size (default: a4)")
    parser.add_argument("--toc", action="store_true", help="add a table of contents at the top")
    parser.add_argument("-i", "--input", type=Path, default=INPUT_DIR,
                        help="folder to read Markdown files from (default: the input folder)")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT_DIR,
                        help="folder to save results to (default: the output folder)")
    args = parser.parse_args()

    formats = list(FORMATS) if args.all else clean_formats(args.formats)
    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        sys.exit(f"Error: unknown format(s): {', '.join(unknown)}\nSupported: html, pdf")

    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    print(f"Looking in: {args.input}")
    files = find_input_files(args.input)
    if not files:
        print("No Markdown files found. Put the .md files you want converted in that folder, then run this again.")
        return
    print(f"Found {len(files)} Markdown file(s).")
    if not formats:
        formats = ask_formats()

    browser = None
    if "pdf" in formats:
        browser = find_browser()
        if not browser:
            sys.exit("Error: making PDFs needs Microsoft Edge or Google Chrome, and neither was found.\n"
                     "Install one of them, or make web pages only:  python convert_markdown.py html")

    print()
    made = failed = 0
    for src in files:
        warnings = []
        try:
            page = to_html(src, args.paper, args.toc, warnings)
        except Exception as error:
            print(f"  [fail] {src.name}: {error}")
            failed += len(formats)
            continue
        for warning in dict.fromkeys(warnings):
            print(f"  note: {src.name}: {warning}")

        for fmt in formats:
            fmt_dir = args.output / fmt
            fmt_dir.mkdir(exist_ok=True)
            out_path = fmt_dir / (src.stem + FORMATS[fmt])
            try:
                if fmt == "html":
                    out_path.write_text(page, encoding="utf-8")
                else:
                    print_to_pdf(browser, page, out_path.resolve())
            except Exception as error:
                print(f"  [fail] {src.name} -> {fmt}: {error}")
                failed += 1
                continue
            print(f"  [ok]   {src.name} -> {fmt}/{out_path.name}  ({kb(out_path.stat().st_size)})")
            made += 1

    print(f"\nDone: {made} made, {failed} failed.")
    print(f"Results are in: {args.output}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(1)
