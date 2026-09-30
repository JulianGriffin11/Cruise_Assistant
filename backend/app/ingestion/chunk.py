MAX_PAGE_CHARS = 800 * 4
TARGET_CHARS = 650 * 4
OVERLAP_CHARS = 200 * 4


def chunk_pages(pages: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    chunk_index = 0
    for page_number, text in pages:
        for segment in _chunk_page_text(text):
            chunks.append((page_number, chunk_index, segment))
            chunk_index += 1
    return chunks


def _chunk_page_text(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    if len(stripped) <= MAX_PAGE_CHARS:
        return [stripped]

    words = stripped.split()
    segments: list[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words):
            word = words[end]
            add = len(word) + (1 if end > start else 0)
            if end > start and length + add > MAX_PAGE_CHARS:
                break
            length += add
            end += 1
            if length >= TARGET_CHARS:
                break
        if end == start:
            end = start + 1
        segments.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        overlap = 0
        overlap_start = end
        while overlap_start > start and overlap < OVERLAP_CHARS:
            overlap_start -= 1
            overlap += len(words[overlap_start]) + 1
        start = overlap_start if overlap_start < end else end
    return segments
