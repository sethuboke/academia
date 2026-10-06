# -*- coding: utf-8 -*-
"""Lightweight PDF writer with no external dependencies.

Produces raw PDF using standard Type1 base fonts (Courier and Helvetica
families). Only basic drawing primitives are implemented: filled rectangles,
lines and text (left / centre / right aligned). Input text is encoded as
latin-1 at emission time.

Usage::

    pdf = Pdf()
    pdf.table(headers, rows, col_widths=[...], align=[...])
    response = HttpResponse(pdf.render(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="x.pdf"'
"""

from __future__ import annotations

from io import BytesIO

# Courier is a fixed-width font: horizontal advance = 0.602 * font size.
_COURIER_ADVANCE = 0.602
# Fallback estimate for proportional fonts.
_PROP_ADVANCE = 0.52

PAGE_WIDTH = 595.27
PAGE_HEIGHT = 841.89
DEFAULT_MARGIN = 40


def _pdf_text(value):
    """Escape a string for a PDF content stream (base fonts, latin-1)."""
    value = (
        str(value)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    value = (
        value.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2265", ">=")
        .replace("\u2264", "<=")
        .replace("\u2026", "...")
    )
    return value.encode("latin-1", "replace").decode("latin-1")


class Pdf:
    """Minimal PDF writer used to render result tables (subject or pupil)."""

    def __init__(self, width=PAGE_WIDTH, height=PAGE_HEIGHT,
                 margin=DEFAULT_MARGIN, size=8.5):
        self.width = width
        self.height = height
        self.margin = margin
        self.size = size
        self._buffer = []
        self.pages = []
        self._current_font = "Courier"
        self._current_size = size
        self._page_index = 0
        self._start_page()

    def _start_page(self):
        self._page_index += 1
        self.pages.append(self._buffer)
        self._buffer = []
        self._y = self.height - self.margin

    def _finish_page(self):
        self.pages.append(self._buffer)
        self._buffer = []

    def _raw(self, *chunks):
        for chunk in chunks:
            self._buffer.append(str(chunk))
    # ------------------------------------------------------------------ #
    # Drawing primitives
    # ------------------------------------------------------------------ #
    def fill_color(self, r, g, b):
        self._raw(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def stroke_color(self, r, g, b):
        self._raw(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def line_width(self, w):
        self._raw(f"{w:.2f} setlinewidth")

    def rect(self, x, y_top, w, h, fill=None, stroke=None, stroke_w=0.6):
        """Rectangle defined by its top-left corner."""
        self._raw(f"{x:.2f} {y_top - h:.2f} {w:.2f} {h:.2f} re")
        if fill:
            self.fill_color(*fill)
            self._raw(" f")
        if stroke:
            self.stroke_color(*stroke)
            self.line_width(stroke_w)
            self._raw(" S")

    def text(self, x, y_top, value, font="Courier", size=8.5,
             color=None, align="left"):
        if font != self._current_font or size != self._current_size:
            self._raw(f"/{font} {size:.2f} Tf")
            self._current_font = font
            self._current_size = size
        if color:
            self.fill_color(*color)
        s = _pdf_text(value)
        if align == "center":
            w = self._text_width(s, size, font)
            x -= w / 2.0
        elif align == "right":
            w = self._text_width(s, size, font)
            x -= w
        self._raw(f"BT 0 0 Td ({s}) Tj ET")

    def _text_width(self, value, size, font):
        if "Courier" in font:
            return len(value) * size * _COURIER_ADVANCE
        return len(value) * size * _PROP_ADVANCE

    def _wrap(self, value, width, size, font):
        words = str(value).split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if candidate and self._text_width(candidate, size, font) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]
    def table(self, headers, rows, col_widths=None, align="centre",
              header_height=13, row_height=10.5, font_size=8, pad=2.5,
              header_fill=(0.91, 0.95, 0.98), zebra_fill=(0.97, 0.97, 0.97),
              header_color=(0.14, 0.16, 0.26), body_color=(0.2, 0.2, 0.2),
              value_color=None):
        import sys as _sys
        _sys.stderr.write("TB table start\n")
        n_cols = max(len(headers), max((len(r) for r in rows), default=0))
        if col_widths is None:
            col_widths = [max(30.0, (self.width - 2 * self.margin - pad * (n_cols - 1)) / n_cols)] * n_cols
        if isinstance(align, str):
            align = [align] * n_cols
        else:
            align = list(align) + ["centre"] * (n_cols - len(align))
        if len(col_widths) < n_cols:
            col_widths += [max(col_widths)] * (n_cols - len(col_widths))
        avail = self.width - 2 * self.margin
        total = sum(col_widths) + pad * (n_cols - 1)
        if total > avail:
            scale = avail / total
            col_widths = [w * scale for w in col_widths]
        starts = []
        x = self.margin
        for w in col_widths:
            x += w
            starts.append(x - w)
        ends = starts[1:] + [self.margin + sum(col_widths)]
        bottom = self.margin
        y = self._y
        # Header
        if y - header_height < bottom + 2:
            self._finish_page()
            self._start_page()
            y = self.height - self.margin
        self._y = y - header_height
        for i, h in enumerate(headers):
            self.rect(starts[i] + pad, y - header_height + pad,
                      col_widths[i] - 2 * pad, header_height - 2 * pad,
                      fill=header_fill)
            for j, line in enumerate(self._wrap(h, col_widths[i] - 2 * pad,
                                                font_size, "Courier-Bold")):
                self.text(starts[i] + (col_widths[i] - self._text_width(line, font_size, "Courier-Bold")) / 2.0,
                          y - header_height + pad - j * font_size * 1.15 - font_size * 0.95,
                          line, font="Courier-Bold", size=font_size, color=header_color, align="centre")
        y_h = y - header_height
        # Body (pagination)
        row_pos = 0
        n_rows = len(rows)
        _sys.stderr.write("TB body while len=%d\n" % n_rows)
        while row_pos < n_rows:
            take = min(max(0, int((y_h - bottom) // row_height)), n_rows - row_pos)
            if take <= 0:
                self._finish_page()
                self._start_page()
                y_h = self.height - self.margin - header_height
                continue
            for idx in range(take):
                row = rows[row_pos + idx]
                yy = y_h - idx * row_height
                self.rect(starts[0], yy - row_height + 1, ends[-1] - starts[0], row_height - 1, stroke=(0.7, 0.7, 0.7))
                for i in range(n_cols):
                    val = row[i] if i < len(row) else ""
                    self.rect(starts[i] + pad, yy - row_height + pad,
                              col_widths[i] - 2 * pad, row_height - 2 * pad,
                              fill=(zebra_fill if idx % 2 else None),
                              stroke=(0.65, 0.65, 0.65), stroke_w=0.4)
                    col = body_color
                    if value_color and val not in ("", "\u2014", None):
                        try:
                            col = value_color(val)
                        except Exception:
                            col = body_color
                    a = align[i] if i < len(align) else "centre"
                    if a == "centre":
                        tx = starts[i] + pad + (col_widths[i] - 2 * pad - self._text_width(val, font_size, "Courier")) / 2.0
                    elif a == "right":
                        tx = starts[i] + pad + col_widths[i] - 2 * pad - self._text_width(val, font_size, "Courier")
                    else:
                        tx = starts[i] + pad
                    self.text(tx, yy - row_height + pad + font_size * 0.95, val,
                              font="Courier", size=font_size, color=col, align=a)
            y_h -= take * row_height
            self._y = y_h
            row_pos += take
    def render(self):
        self._finish_page()
        return self._assemble()

    def _assemble(self):
        store = {}
        next_obj = 1

        def alloc():
            nonlocal next_obj
            n = next_obj
            next_obj += 1
            return n

        catalog = alloc()
        pages = alloc()
        store[catalog] = f"<< /Type /Catalog /Pages {pages} 0 R >>"
        kids = " ".join(f"{alloc()} 0 R" for _ in self.pages)
        store[pages] = f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>"

        font_nos = {}
        for font in ("Courier", "Courier-Bold", "Helvetica", "Helvetica-Bold"):
            font_nos[font] = alloc()

        page_obj_nos = []
        stream_nos = []
        for idx, page_content in enumerate(self.pages):
            page_obj_nos.append(alloc())
            stream_nos.append(alloc())
            store[page_obj_nos[idx]] = (
                f"<< /Type /Page /Parent {pages} 0 R "
                f"/MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Resources << /Font << /F1 {font_nos['Courier']} 0 R "
                f"/F2 {font_nos['Courier-Bold']} 0 R "
                f"/F3 {font_nos['Helvetica']} 0 R /F4 {font_nos['Helvetica-Bold']} 0 R >> >> "
                f"/Contents {stream_nos[idx]} 0 R >>"
            )
            body = "\n".join(page_content)
            store[stream_nos[idx]] = (
                f"<< /Length {len(body.encode('latin-1'))} >> stream\n{body}\nendstream"
            )

        for font, no in font_nos.items():
            store[no] = f"<< /Type /Font /Subtype /Type1 /BaseFont /{font} >>"

        out = BytesIO()
        out.write(b"%PDF-1.4\n")
        offsets = []
        for no in sorted(store):
            offsets.append(out.tell())
            out.write(f"{no} 0 obj\n".encode("latin-1"))
            out.write(store[no].encode("latin-1"))
            out.write(b"\nendobj\n")
        xref = out.tell()
        out.write(f"xref\n0 {next_obj}\n".encode("latin-1"))
        out.write(b"0000000000 65535 f \n")
        for off in offsets:
            out.write(f"{off:010d} 00000 n \n".encode("latin-1"))
        out.write(
            (f"trailer\n<< /Size {next_obj} /Root 1 0 R >>\n"
             f"startxref\n{xref}\n%%EOF\n").encode("latin-1")
        )
        return out.getvalue()
