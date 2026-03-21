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


def rebuild_pdf(original_pdf_path, translated_data, output_path):
    """Rebuild PDF by overlaying translated text on the original.

    For each span marked as translated:
    1. Draw a white rectangle over the original text area
    2. Insert the translated text at the same position

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

    # Pre-register fonts on each page as needed
    font_names = {}  # page_num -> {bold: fontname, regular: fontname}

    for page_info in translated_data["pages"]:
        page_num = page_info["page_num"]
        page = doc[page_num]

        # Collect spans that were translated
        translated_spans = [
            s for s in page_info["spans"] if s.get("translated", False)
        ]

        if not translated_spans:
            continue

        # Register fonts for this page
        page.insert_font(fontfile=font_regular, fontname="tahoma-r")
        if font_bold:
            page.insert_font(fontfile=font_bold, fontname="tahoma-b")

        # Process each translated span
        for span in translated_spans:
            bbox = span["bbox"]
            origin = span["origin"]
            text = span["text"]
            size = span["size"]
            color = int_to_rgb(span["color"])
            bold = is_bold(span["flags"])

            # 1. Draw white rectangle to cover original text
            rect = fitz.Rect(
                bbox[0] - 0.5,   # small padding
                bbox[1] - 0.5,
                bbox[2] + 0.5,
                bbox[3] + 0.5,
            )
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(fill=(1, 1, 1), color=(1, 1, 1), width=0)
            shape.commit()

            # 2. Insert translated text at original position
            fontname = "tahoma-b" if bold and font_bold else "tahoma-r"
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
