from pathlib import Path

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


def test_every_card_has_unique_valid_choices_and_correct_answer(tmp_path: Path) -> None:
    service = StudyService(CurriculumRepository(Path("curriculum")), ProgressRepository(tmp_path / "db"))
    for card in service.cards():
        assert card.front.strip() and card.definition.strip(), card.id
        assert "�" not in card.key_rule, card.id
        for mode in ("learn", "law", "formula"):
            if mode == "formula" and not service.has_formula(card):
                continue
            exercise = service.set_exercise(card, mode)
            assert 2 <= len(exercise.choices) <= 4, card.id
            assert len(exercise.choices) == len(set(exercise.choices)), card.id
            expected = service.formula_text(card) if service.has_formula(card) else card.definition
            assert exercise.choices.count(expected) == 1, card.id
            assert exercise.choices[exercise.correct_index] == expected, card.id
            assert expected in exercise.question.answer, card.id


def test_formula_mode_supports_definition_only_imports(tmp_path: Path) -> None:
    service = StudyService(CurriculumRepository(Path("curriculum")), ProgressRepository(tmp_path / "db"))
    cards = {card.id: card for card in service.cards()}
    for card_id in ("C3-001", "C4-004"):
        card = cards[card_id]
        assert not card.key_rule
        assert service.has_formula(card)
        exercise = service.set_exercise(card, "formula")
        assert exercise.choices[exercise.correct_index] == card.definition
    assert len(service.mode_cards(3, "formula")) > 1
    assert len(service.mode_cards(4, "formula")) > 3


def test_definite_physics_corrections_and_visible_source_flags(tmp_path: Path) -> None:
    service = StudyService(CurriculumRepository(Path("curriculum")), ProgressRepository(tmp_path / "db"))
    cards = {card.id: card for card in service.cards()}
    assert "− (eB/2mc)" in cards["C8-012"].key_rule
    assert "|e|B/(mc)" in cards["C8-029"].key_rule
    assert "Ze₀²" in cards["C10-036"].key_rule
    assert "trace preserving" in cards["C10-022"].key_rule
    assert "Σⱼ Aⱼ†Aⱼ = I" in cards["C10-023"].key_rule
    assert "i/ℏ" in cards["C10-030"].key_rule
    assert "single-photon" in cards["EXP-041"].definition
    assert "ultraviolet" in cards["EXP-029"].definition
    assert "Source check needed" in service.set_exercise(cards["C6-023"]).question.answer


def test_known_equivalent_definitions_never_appear_as_wrong_choices(tmp_path: Path) -> None:
    service = StudyService(CurriculumRepository(Path("curriculum")), ProgressRepository(tmp_path / "db"))
    cards = {card.id: card for card in service.cards()}
    groups = (("EXP-023", "EXP-044"), ("EXP-029", "EXP-046"), ("C7-008", "C7-015"))
    for first, second in groups:
        for _ in range(10):
            exercise = service.set_exercise(cards[first])
            wrong = [choice for i, choice in enumerate(exercise.choices) if i != exercise.correct_index]
            assert cards[second].definition not in wrong
