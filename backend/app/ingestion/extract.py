import pymupdf


def extract_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [(page_index + 1, doc[page_index].get_text()) for page_index in range(len(doc))]
    finally:
        doc.close()
