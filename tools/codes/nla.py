"""Reading-order text from Editora Peru "Normas Legales Actualizadas" PDFs.

The NLA editions are set in two columns with a running header and footer. We take
PyMuPDF text blocks, drop the header/footer bands, and read the left column
top to bottom, then the right column. Each block becomes one string with its
internal line breaks kept (paragraph = block in these editions).
"""
from __future__ import annotations

import fitz

fitz.TOOLS.mupdf_display_errors(False)

HEADER_Y = 72      # blocks starting above this are running headers (page no., title)
FOOTER_Y = 762     # blocks starting below this are running footers ("Inicio", title)


def blocks(path, first_page=0, last_page=None):
    """Yield (page, column, y0, x0, text) in reading order."""
    d = fitz.open(path)
    last = d.page_count if last_page is None else last_page
    for pno in range(first_page, last):
        p = d[pno]
        mid = p.rect.width / 2
        top, bottom = HEADER_Y * p.rect.height / 779.5, FOOTER_Y * p.rect.height / 779.5
        out = []
        for b in p.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if b[6] != 0:  # image block
                continue
            if y0 < top or y0 > bottom:
                continue
            col = 0 if x0 < mid - 5 else 1
            out.append((pno, col, round(y0, 1), round(x0, 1), text))
        out.sort(key=lambda r: (r[1], r[2], r[3]))
        yield from out
