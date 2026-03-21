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


def classify_zone(span_bbox, header_bottom_y):
    """Classify a span's zone based on its vertical position."""
    y_top = span_bbox[1]
    if y_top < header_bottom_y:
        return "header"
    return "body"


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

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        header_bottom_y = (
            config.header_fixed_y if use_fixed_header
            else find_header_bottom(blocks)
        )

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
                    zone = classify_zone(bbox, header_bottom_y)

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
                        "translate": zone != "header",
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
