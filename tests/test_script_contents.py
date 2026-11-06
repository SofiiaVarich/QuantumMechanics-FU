import csv
from pathlib import Path

from quantum_tutor.infrastructure.curriculum import CurriculumRepository


def test_all_supplied_sections_are_available_in_bot_models() -> None:
    directory = Path("curriculum")
    with (directory / "script_contents.tsv").open(encoding="utf-8") as source:
        expected = list(csv.DictReader(source, delimiter="\t"))
    chapters = CurriculumRepository(directory).chapters()
    sections = {section.id: section for chapter in chapters for section in chapter.sections}
    assert len(sections) == len(expected) == 109
    for row in expected:
        section = sections[row["section"]]
        assert section.page == int(row["page"])
        assert section.title == row["title"]
        assert section.title_de == row["title_de"]
    for chapter in chapters[:10]:
        assert chapter.script_file == f"QMChapter{chapter.number}.pdf"
        assert chapter.sections
        assert all(section.id.startswith(f"{chapter.number}.") for section in chapter.sections)
    experiments = chapters[10:]
    assert len(experiments) == 10
    assert all(chapter.professor == "Franke" for chapter in experiments)
