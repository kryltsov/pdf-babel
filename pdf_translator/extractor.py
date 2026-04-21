"""Extract text spans with layout information from PDF files."""

import json
import fitz  # PyMuPDF


def find_header_bottom(blocks):
    """Find the bottom edge of the header zone by locating the logo image.

    The logo image (typically the second image block) marks the header area.
    Everything above its bottom edge + small margin is header.
    """
    images = [b for b in blocks if b.get("type") == 1]
    if len(images) >= 2:
        # Second image is typically the logo
        logo = images[1]
        return logo["bbox"][3] + 5  # bottom of logo + margin
    # Fallback: use a reasonable default
    return 110.0


def classify_zone(span_bbox, header_bottom_y, footer_top_y=None):
    """Classify a span's zone based on its vertical position."""
    y_top = span_bbox[1]
    if y_top < header_bottom_y:
        return "header"
    if footer_top_y is not None and y_top >= footer_top_y:
        return "footer"
    return "body"


def is_rotated_span(span_bbox):
    """Detect rotated (90-degree) text spans rendered on the page margin.

    Rotated spans appear with a narrow bounding box and large vertical extent
    because PyMuPDF reports the unrotated typesetting bbox. A normal line of
    horizontal text has w >> h; rotated marginalia have h >> w.
    """
    width = span_bbox[2] - span_bbox[0]
    height = span_bbox[3] - span_bbox[1]
    return width < 20 and height > 50


def extract_pdf(pdf_path, config=None):
    """Extract all text spans with layout metadata from a PDF.

    Args:
        pdf_path: Path to the PDF file.
        config: Optional TranslateConfig. If provided and header_fixed_y is set,
                uses that instead of auto-detection.

    Returns a dict with pages, each containing spans with:
    - text, bbox, origin, font, size, color, flags
    - zone classification (header/body)
    - translate flag (False for header, True for body)
    """
    doc = fitz.open(pdf_path)
    result = {
        "source_file": str(pdf_path),
        "pages": [],
    }

    use_fixed_header = (
        config is not None
        and config.header_detection != "auto"
        and config.header_fixed_y is not None
    )
    footer_top_y = config.footer_fixed_y if config is not None else None

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        # If header_first_page_only, skip header detection on pages after the first
        if (config is not None and config.header_first_page_only
                and page_num > 0):
            header_bottom_y = 0
        elif use_fixed_header:
            header_bottom_y = config.header_fixed_y
        else:
            header_bottom_y = find_header_bottom(blocks)

        page_data = {
            "page_num": page_num,
            "width": round(page.rect.width, 2),
            "height": round(page.rect.height, 2),
            "header_bottom_y": round(header_bottom_y, 2),
            "spans": [],
        }

        span_index = 0
        for block in blocks:
            if block.get("type") == 1:  # image block
                continue

            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"]
                    if not text.strip():
                        continue

                    bbox = [round(x, 2) for x in span["bbox"]]
                    origin = [round(x, 2) for x in span["origin"]]
                    if is_rotated_span(bbox):
                        zone = "rotated"
                    else:
                        zone = classify_zone(bbox, header_bottom_y, footer_top_y)

                    span_data = {
                        "id": f"p{page_num}_s{span_index}",
                        "text": text,
                        "bbox": bbox,
                        "origin": origin,
                        "font": span["font"],
                        "size": span["size"],
                        "color": span["color"],
                        "flags": span["flags"],
                        "zone": zone,
                        "translate": zone == "body",
                    }
                    page_data["spans"].append(span_data)
                    span_index += 1

        result["pages"].append(page_data)

    doc.close()
    return result


def save_extraction(data, output_path):
    """Save extracted data to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_extraction(json_path):
    """Load extracted/translated data from a JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
