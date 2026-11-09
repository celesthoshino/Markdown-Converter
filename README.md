# Markdown Converter

Turns Markdown (`.md`) files into clean, readable web pages and PDFs. Put your files in the `input` folder, run the
script, and get the results in the `output` folder.

It follows the same Markdown rules as GitHub, so a README that looks right on GitHub looks the same here. Tables, code
with colors, task lists, footnotes and images all work.

## Folder layout

```
markdown_converter/
├── convert_markdown.py   the script
├── requirements.txt      Python packages to install
├── README.md             this file
├── input/                put your .md files (and their images) here
└── output/               results appear here
    ├── html/
    └── pdf/
```

## Setup (one time)

1. Install **Python 3.9 or newer** from https://www.python.org/downloads/
   (on Windows, tick "Add Python to PATH" during install).
2. Open a terminal in the `markdown_converter` folder and run:

   ```
   pip install -r requirements.txt
   ```

3. For PDFs you also need **Microsoft Edge** or **Google Chrome**. Edge comes with Windows, so on Windows there's
   nothing to do. The browser does the PDF printing in the background, and no window opens.

## How to use

1. Copy your `.md` files into the `input` folder. If they show images, copy those too, keeping the same folder
   structure the `.md` file expects (for example an `images` folder next to it).
2. Open a terminal in the `markdown_converter` folder and run:

   ```
   python convert_markdown.py
   ```

3. It asks whether you want web pages (`html`), PDFs (`pdf`), or both (`all`).
4. The results are saved in `output/html/` and `output/pdf/`. For example, `input/notes.md` becomes
   `output/html/notes.html` and `output/pdf/notes.pdf`.

| Command | What it does |
|---|---|
| `python convert_markdown.py` | Asks whether you want html, pdf or both |
| `python convert_markdown.py html` | Web pages only |
| `python convert_markdown.py pdf` | PDFs only |
| `python convert_markdown.py --all` | Both |
| `python convert_markdown.py pdf --toc` | PDFs with a table of contents at the top |
| `python convert_markdown.py pdf --paper letter` | PDFs on US Letter paper instead of A4 |
| `python convert_markdown.py --help` | Shows all options |

## Options

| Option | Default | Meaning |
|---|---|---|
| `formats` | asks you | `html`, `pdf`, or both |
| `--all` | off | Make both web pages and PDFs |
| `--toc` | off | Add a table of contents, with links to every heading, at the top |
| `--paper` | `a4` | PDF page size: `a4` or `letter` |
| `-i`, `--input` | `input` folder | Folder to read Markdown files from |
| `-o`, `--output` | `output` folder | Folder to save results to |

**Files it reads:** `.md .markdown .mdown .mkd`. Images in the `input` folder are left alone (they're used by the
pages). Other files are listed as "ignored".

## What's supported

Everything in standard Markdown, plus the extras GitHub has:

| You write | You get |
|---|---|
| `# Heading`, `## Smaller heading` | Headings |
| `**bold**`, `*italic*`, `~~struck~~` | **bold**, *italic*, ~~struck~~ |
| `` `code` `` and ```` ```python ```` blocks | Code, with colors for the language you name |
| Rows like `\| a \| b \|` | Tables |
| `- [ ] todo` / `- [x] done` | Checkboxes |
| `![alt text](images/photo.png)` | Images |
| `[text](other.md)` | Links. Links to other `.md` files point to their converted `.html` pages |
| `Text[^1]` and `[^1]: note` | Footnotes, listed at the end |
| `> quote` | Quotes |

## Good to know

- **Original files are never changed.** The script only reads from `input`.
- **Web pages are self-contained.** Images are stored inside the `.html` file, so you can email it or move it
  anywhere and the images still show.
- **Images from the internet** (`https://...`) stay as links, so they only show when you're online. For PDFs, the
  browser downloads them while printing.
- **Missing images** are reported as a note, and the rest of the page is still made.
- **The page title** is the first `#` heading, or the file name if there isn't one.
- **Long code blocks, tables and images aren't split** across PDF pages where possible.
- **Running it again overwrites earlier results** with the same name in `output`.
- **Subfolders inside `input` are not scanned** for `.md` files, but images in subfolders work fine.

## Troubleshooting

**`Error: the required packages are not installed`**

Run `pip install -r requirements.txt` from inside the `markdown_converter` folder.

**`making PDFs needs Microsoft Edge or Google Chrome`**

Neither browser was found. Install one of them, or make only web pages with `python convert_markdown.py html`. You
can also open a web page in any browser and use Print, then "Save as PDF".

**`image not found: ...`**

The image path in the `.md` file doesn't match a file in `input`. Check the spelling and the folder. Paths are
relative to the `.md` file.

**A nested list or code block in a list looks wrong**

Indent the inner lines to line up with the text of the list item above, as on GitHub.

**`'python' is not recognized`**

Python isn't on your PATH. On Windows, try `py convert_markdown.py` instead, or reinstall Python with "Add Python to PATH" ticked.
