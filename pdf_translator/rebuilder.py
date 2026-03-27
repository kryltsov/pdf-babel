"""Rebuild PDF with translated text while preserving layout."""

import os
import platform
import fitz  # PyMuPDF


def find_system_font(bold=False):
    """Find a system font that supports Latin and Cyrillic characters."""
    system = platform.system()

    if system == "Windows":
        fonts_dir = "C:/Windows/Fonts"
        font_file = "tahomabd.ttf" if bold else "tahoma.ttf"
        path = os.path.join(fonts_dir, font_file)
        if os.path.exists(path):
            return path

    elif system == "Darwin":  # macOS
        for candidate in [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Tahoma Bold.ttf" if bold
            else "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        ]:
            if os.path.exists(candidate):
                return candidate

    else:  # Linux
        for candidate in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]:
            if os.path.exists(candidate):
                return candidate

    return None


def int_to_rgb(color_int):
    """Convert PyMuPDF integer color to RGB tuple (0-1 range)."""
    r = ((color_int >> 16) & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = (color_int & 0xFF) / 255.0
    return (r, g, b)


def is_bold(flags):
    """Check if font flags indicate bold."""
    return bool(flags & (1 << 4))  # bit 4 = bold


def find_background_rect(filled_rects, bbox):
    """Find the filled rectangle behind a text span from the page's drawings.

    Args:
        filled_rects: List of (fitz.Rect, fill_color) from page.get_drawings().
        bbox: The text span's bounding box [x0, y0, x1, y1].

    Returns an RGB tuple in 0-1 range (white if no background rect found).
    """
    # Inset span rect by 1pt to tolerate coordinate rounding between
    # text extraction and drawing extraction (often differs by <0.01pt)
    span_rect = fitz.Rect(bbox)
    inset = fitz.Rect(
        span_rect.x0 + 1, span_rect.y0 + 1,
        span_rect.x1 - 1, span_rect.y1 - 1,
    )
    # Walk in reverse — later drawings are painted on top of earlier ones
    for rect, fill in reversed(filled_rects):
        if rect.contains(inset):
            return fill
    return (1.0, 1.0, 1.0)


def rebuild_pdf(original_pdf_path, translated_data, output_path):
    """Rebuild PDF by overlaying translated text on the original.

    For each span marked as translated:
    1. Find the background drawing (filled rect) behind the span
    2. Draw a cover rectangle matching that background color
    3. Insert the translated text, shrinking font if it would overflow

    Args:
        original_pdf_path: Path to the original PDF
        translated_data: Dict with same structure as extraction output,
                        but with translated text and "translated": true flags
        output_path: Path for the output PDF
    """
    doc = fitz.open(original_pdf_path)

    # Find system fonts
    font_regular = find_system_font(bold=False)
    font_bold = find_system_font(bold=True)

    if not font_regular:
        raise RuntimeError(
            "Could not find a suitable system font. "
            "Please install Tahoma, Arial, or DejaVu Sans."
        )

    # Create Font objects for text width measurement
    font_obj_regular = fitz.Font(fontfile=font_regular)
    font_obj_bold = fitz.Font(fontfile=font_bold) if font_bold else None

    for page_info in translated_data["pages"]:
        page_num = page_info["page_num"]
        page = doc[page_num]

        # Collect spans that were translated
        translated_spans = [
            s for s in page_info["spans"] if s.get("translated", False)
        ]

        if not translated_spans:
            continue

        # Extract all filled rectangles from the page's vector drawings
        filled_rects = []
        for drawing in page.get_drawings():
            fill = drawing.get("fill")
            if fill and drawing.get("rect"):
                filled_rects.append((fitz.Rect(drawing["rect"]), fill))

        # Register fonts for this page
        page.insert_font(fontfile=font_regular, fontname="tahoma-r")
        if font_bold:
            page.insert_font(fontfile=font_bold, fontname="tahoma-b")

        page_width = page.rect.width

        # Process each translated span
        for span in translated_spans:
            bbox = span["bbox"]
            origin = span["origin"]
            text = span["text"]
            size = span["size"]
            color = int_to_rgb(span["color"])
            bold = is_bold(span["flags"])

            # 1. Find background color from PDF drawing structure
            bg_color = find_background_rect(filled_rects, bbox)

            rect = fitz.Rect(
                bbox[0] - 0.5,   # small padding
                bbox[1] - 0.5,
                bbox[2] + 0.5,
                bbox[3] + 0.5,
            )
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(fill=bg_color, color=bg_color, width=0)
            shape.commit()

            # 2. Measure text width and shrink font if it would overflow
            fontname = "tahoma-b" if bold and font_bold else "tahoma-r"
            font_obj = font_obj_bold if bold and font_obj_bold else font_obj_regular

            text_width = font_obj.text_length(text, fontsize=size)
            # Available width: from origin to page right margin (with small margin)
            max_width = page_width - origin[0] - 2
            if text_width > max_width and max_width > 0:
                size = size * max_width / text_width

            # 3. Insert translated text at original position
            page.insert_text(
                fitz.Point(origin[0], origin[1]),
                text,
                fontname=fontname,
                fontsize=size,
                color=color,
            )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return output_path
