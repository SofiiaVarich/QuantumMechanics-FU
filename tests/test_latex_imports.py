import json
from pathlib import Path

from quantum_tutor.infrastructure.curriculum import CurriculumRepository


def test_latex_is_retained_separately_from_telegram_text() -> None:
    repository = CurriculumRepository(Path("curriculum"))
    for chapter_number, expected_cards, expected_latex in ((2, 34, 31), (4, 50, 46), (5, 83, 83), (6, 85, 64)):
        data = json.loads(Path(f"curriculum/topic_{chapter_number}.json").read_text())
        chapter = repository.chapter(chapter_number)
        assert chapter is not None
        assert len(chapter.concepts) == expected_cards
        metadata = data["concept_metadata"]
        assert sum(bool(metadata[card.id]["formula_latex"]) for card in chapter.concepts) == expected_latex
        assert len({card.id for card in chapter.concepts}) == expected_cards
        for card in chapter.concepts:
            assert "LaTeX.xlsx" in card.source_file
            assert "\\(" not in card.key_rule
            assert "\\)" not in card.key_rule
            assert "Render LaTeX" not in card.definition
    c2 = json.loads(Path("curriculum/topic_2.json").read_text())
    assert len(c2["workbook_sources"]) == 2
    assert len({entry["sha256"] for entry in c2["workbook_sources"]}) == 1
    assert c2["workbook_sources"][1]["filename"].endswith(" copy.xlsx")
    assert len(c2["box_script_rules"]) == 20
    assert len(c2["named_concepts_reference"]) == 19
    renamed = next(card for card in c2["concepts"] if card["front"] == "Heisenberg uncertainty relation (first reading)")
    assert renamed["id"] == "concept-6a256a8567d518a7"
    assert len([card for card in c2["concepts"] if card["section_id"] == "2.3.4"]) == 8
    c4 = json.loads(Path("curriculum/topic_4.json").read_text())
    assert {card["id"] for card in c4["concepts"]} == {f"C4-{i:03}" for i in range(1, 51)}
    assert len(c4["box_script_rules"]) == 24
    assert len(c4["named_concepts_reference"]) == 19
    assert c4["concept_metadata"]["C4-002"]["formula_latex"] == r"p_j\ge 0,\quad \sum_{j=1}^{n}p_j=1"
    assert c4["concept_metadata"]["C4-002"]["telegram_rendering_input"].startswith("<code>")
    assert c4["concept_metadata"]["C4-001"]["formula_latex"] == ""
    c5 = json.loads(Path("curriculum/topic_5.json").read_text())
    assert c5["concept_metadata"]["C5-001"]["formula_latex"] == r"\mathbf L=\mathbf X\times\mathbf P"
    assert sum(item.get("priority") == "BOX" for item in c5["concept_metadata"].values()) == 29
    c6 = json.loads(Path("curriculum/topic_6.json").read_text())
    assert len(c6["box_script_rules"]) == 15
    assert len(c6["script_terminology_reference"]) == 18
    assert "C6-023" in c6["content_review_required"]
    assert c6["concept_metadata"]["C6-001"]["telegram_rendering_input"].startswith(r"\(")
    assert any("does not natively render" in row["note"] for row in c6["workbook_source_caveats"])
