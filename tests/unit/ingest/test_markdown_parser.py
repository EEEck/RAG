import uuid

from ingest.markdown_parser import parse_markdown_sections, build_markdown_nodes_and_atoms


def test_parse_markdown_sections_extracts_headings_and_units():
    text = "\n".join(
        [
            "# Unit 1 Greetings",
            "Hello from the intro.",
            "<!-- image -->",
            "## Lesson 1 Hello",
            "Say hello and introduce yourself.",
        ]
    )

    sections = parse_markdown_sections(text)

    assert len(sections) == 2
    assert sections[0].title == "Unit 1 Greetings"
    assert sections[0].unit_number == 1
    assert sections[0].heading_level == 1
    assert "Hello from the intro." in sections[0].body
    assert sections[1].title == "Lesson 1 Hello"
    assert sections[1].heading_level == 2


def test_build_markdown_nodes_and_atoms_creates_structure():
    text = "\n".join(
        [
            "# Unit 2 Travel",
            "Talk about places and directions.",
            "## Lesson 1 Tickets",
            "Practice buying tickets.",
        ]
    )
    sections = parse_markdown_sections(text)

    book_id = uuid.uuid4()
    nodes, atoms = build_markdown_nodes_and_atoms(
        sections=sections,
        book_id=book_id,
        category="language",
        book_metadata={"subject": "language", "grade_level": 5},
    )

    assert len(nodes) == 3  # root + 2 sections
    assert nodes[0].node_level == 0
    assert nodes[1].meta_data.get("unit") == 2
    assert len(atoms) == 2
    assert atoms[0].meta_data.unit_number == 2
