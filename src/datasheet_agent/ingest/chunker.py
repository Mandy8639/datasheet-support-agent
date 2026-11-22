"""Split section text into retrieval chunks and render tables as text chunks."""

from dataclasses import dataclass

from datasheet_agent.ingest.pdf import Section, Table

MAX_CHARS = 1200


@dataclass
class Chunk:
    page_no: int
    page_end: int
    section: str
    kind: str  # text | table
    text: str


def chunk_section(section: Section, max_chars: int = MAX_CHARS) -> list[Chunk]:
    """Pack whole lines into chunks of at most max_chars, never crossing a page boundary.

    v2 (2026-11-21): a chunk that spanned pages 2-5 let the model cite page 2 for a fact on
    page 5, and the guardrail then (correctly) blocked the answer. One page per chunk makes
    every citation exact.
    """
    pages = section.line_pages or [section.page_start] * len(section.lines)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_page, size = None, 0

    def flush():
        if buf:
            chunks.append(Chunk(buf_page, buf_page, section.heading, "text", "\n".join(buf)))

    for line, page in zip(section.lines, pages, strict=True):
        line = line.strip()
        if not line:
            continue
        if buf and (page != buf_page or size + len(line) + 1 > max_chars):
            flush()
            buf, size = [], 0
        buf_page = page
        buf.append(line)
        size += len(line) + 1
    flush()
    return chunks


def render_table(table: Table) -> str:
    lines = [" | ".join(table.header)]
    lines += [" | ".join(r) for r in table.rows]
    return "\n".join(lines)


def table_chunk(table: Table) -> Chunk:
    return Chunk(table.page_no, table.page_no, table.section, "table", render_table(table))
