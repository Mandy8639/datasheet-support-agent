from datasheet_agent.ingest.chunker import chunk_section
from datasheet_agent.ingest.pdf import Section


def test_chunks_never_cross_a_page():
    s = Section("Features", 3, 2, 5, lines=["a", "b", "c", "d"], line_pages=[2, 2, 3, 5])
    chunks = chunk_section(s)
    assert [(c.page_no, c.page_end, c.text) for c in chunks] == [
        (2, 2, "a\nb"),
        (3, 3, "c"),
        (5, 5, "d"),
    ]


def test_size_limit_still_applies_within_a_page():
    s = Section("Long", 2, 1, 1, lines=["x" * 700, "y" * 700], line_pages=[1, 1])
    assert len(chunk_section(s, max_chars=1000)) == 2


def test_sections_without_page_info_fall_back_to_start_page():
    s = Section("Old", 2, 4, 4, lines=["a", "b"])
    assert [(c.page_no, c.page_end) for c in chunk_section(s)] == [(4, 4)]
