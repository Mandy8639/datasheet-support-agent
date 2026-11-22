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
    """Pack whole lines into chunks of at most max_chars (a single longer line stands alone)."""
    chunks, buf = [], []
    size = 0
    for line in section.lines:
        line = line.strip()
        if not line:
            continue
        if buf and size + len(line) + 1 > max_chars:
            chunks.append("\n".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        chunks.append("\n".join(buf))
    return [Chunk(section.page_start, section.page_end, section.heading, "text", c) for c in chunks]


def render_table(table: Table) -> str:
    lines = [" | ".join(table.header)]
    lines += [" | ".join(r) for r in table.rows]
    return "\n".join(lines)


def table_chunk(table: Table) -> Chunk:
    return Chunk(table.page_no, table.page_no, table.section, "table", render_table(table))
