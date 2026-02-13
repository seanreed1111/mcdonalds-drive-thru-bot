"""Convert a markdown blog post to Substack-friendly format.

Transforms tables and code blocks into images, strips bold formatting.
Output: <original>-substack.md with images in ./images/ relative to the file.

Usage:
    uv run python scripts/convert_to_substack.py <path-to-markdown-file>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from PIL import ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

_MONO_FONT_NAMES = [
    "Consolas",
    "Courier New",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "monospace",
]


def _find_mono_font(size: int = 16) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return the first available monospace font, falling back to default."""
    for name in _MONO_FONT_NAMES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------------------
# Code block → image  (Pygments + Pillow, light theme)
# ---------------------------------------------------------------------------


def render_code_image(
    code: str,
    language: str | None,
    dest: Path,
    *,
    font_size: int = 16,
    line_pad: int = 4,
    pad: int = 24,
) -> None:
    """Render *code* as a syntax-highlighted PNG (light background)."""
    try:
        lexer = get_lexer_by_name(language) if language else guess_lexer(code)
    except Exception:
        lexer = get_lexer_by_name("text")

    formatter = ImageFormatter(
        style="friendly",  # light Pygments style
        font_size=font_size,
        font_name="Consolas",
        line_numbers=False,
        line_pad=line_pad,
        image_pad=pad,
    )
    raw_png = highlight(code, lexer, formatter)
    dest.write_bytes(raw_png)


# ---------------------------------------------------------------------------
# Table → image  (matplotlib)
# ---------------------------------------------------------------------------


def _parse_md_table(table_text: str) -> tuple[list[str], list[list[str]]]:
    """Return (headers, rows) from a markdown table string."""
    lines = [ln.strip() for ln in table_text.strip().splitlines() if ln.strip()]
    # First line = headers, second = separator, rest = data
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return headers, rows


def render_table_image(table_text: str, dest: Path) -> None:
    """Render a markdown table as a clean PNG using matplotlib."""
    headers, rows = _parse_md_table(table_text)

    n_cols = len(headers)
    n_rows = len(rows)

    # --- Compute proportional column widths based on content ---------------
    all_rows = [headers] + rows
    max_lens = []
    for col_idx in range(n_cols):
        col_max = max(len(row[col_idx]) for row in all_rows)
        max_lens.append(max(col_max, 3))  # minimum width
    total = sum(max_lens)
    col_widths = [w / total for w in max_lens]

    # --- Figure sizing proportional to content ----------------------------
    fig_width = max(8, total * 0.12)
    row_height = 0.4
    fig_height = max(2, (n_rows + 1) * row_height + 0.5)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    tbl = ax.table(
        cellText=rows,
        colLabels=headers,
        colWidths=col_widths,
        cellLoc="left",
        loc="center",
    )

    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.0, 2.8)

    # Style header row
    for col_idx in range(n_cols):
        cell = tbl[0, col_idx]
        cell.set_facecolor("#e8e8e8")
        cell.set_text_props(weight="bold")

    # Light alternating rows
    for row_idx in range(1, n_rows + 1):
        for col_idx in range(n_cols):
            cell = tbl[row_idx, col_idx]
            if row_idx % 2 == 0:
                cell.set_facecolor("#f9f9f9")
            else:
                cell.set_facecolor("#ffffff")

    fig.tight_layout(pad=0.5)
    fig.savefig(str(dest), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Markdown conversion
# ---------------------------------------------------------------------------

# Regex patterns
_FENCED_CODE = re.compile(r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL)

# Markdown table: header row, separator row (with |---), and 1+ data rows.
_TABLE = re.compile(
    r"(^\|.+\|[ \t]*\n^\|[\s\-:|]+\|[ \t]*\n(?:^\|.+\|[ \t]*\n?)+)",
    re.MULTILINE,
)

_BOLD_ASTERISK = re.compile(r"\*\*(.+?)\*\*")
_BOLD_UNDERSCORE = re.compile(r"__(.+?)__")


def convert(src: Path) -> Path:
    """Convert *src* markdown file to Substack format. Returns output path."""
    text = src.read_text(encoding="utf-8")
    images_dir = src.parent / "images"
    images_dir.mkdir(exist_ok=True)

    code_counter = 0
    table_counter = 0

    # --- Replace code blocks first (they might contain pipe chars) ----------
    def _replace_code(m: re.Match) -> str:
        nonlocal code_counter
        code_counter += 1
        lang = m.group(1) or None
        code = m.group(2)
        fname = f"code-{code_counter}.png"
        render_code_image(code, lang, images_dir / fname)
        alt = f"Code snippet{f' ({lang})' if lang else ''}"
        return f"![{alt}](./images/{fname})"

    text = _FENCED_CODE.sub(_replace_code, text)

    # --- Replace tables -------------------------------------------------------
    def _replace_table(m: re.Match) -> str:
        nonlocal table_counter
        table_counter += 1
        fname = f"table-{table_counter}.png"
        render_table_image(m.group(0), images_dir / fname)
        return f"![Table {table_counter}](./images/{fname})"

    text = _TABLE.sub(_replace_table, text)

    # --- Strip bold -----------------------------------------------------------
    text = _BOLD_ASTERISK.sub(r"\1", text)
    text = _BOLD_UNDERSCORE.sub(r"\1", text)

    # --- Write output ---------------------------------------------------------
    out_path = src.with_stem(f"{src.stem}-substack")
    out_path.write_text(text, encoding="utf-8")

    print(f"Converted: {src}")
    print(f"  Output:  {out_path}")
    print(f"  Images:  {images_dir}/ ({code_counter} code, {table_counter} table)")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <markdown-file>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    convert(src)
