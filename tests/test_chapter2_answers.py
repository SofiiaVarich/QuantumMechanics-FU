import random
from pathlib import Path

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository


def test_chapter2_equivalent_answers_never_compete():
    service = StudyService(CurriculumRepository(Path("curriculum")), None)
    cards = {card.id: card for card in service.cards(2)}
    pairs = (
        ("concept-bbf3c48cc71c54f5", "concept-09a186cab399efc8"),
        ("concept-36e0507fcc738744", "concept-7bcd3378b1235038"),
    )
    state = random.getstate()
    try:
        for left, right in pairs:
            for source, excluded in ((left, right), (right, left)):
                other = cards[excluded]
                excluded_answer = service.formula_text(other) or other.definition
                for seed in range(30):
                    random.seed(seed)
                    exercise = service.set_exercise(cards[source])
                    assert excluded_answer not in exercise.choices
                    expected = service.formula_text(cards[source]) or cards[source].definition
                    assert exercise.choices[exercise.correct_index] == expected
    finally:
        random.setstate(state)


def test_state_vector_answer_includes_expansion_and_normalization():
    service = StudyService(CurriculumRepository(Path("curriculum")), None)
    card = next(card for card in service.cards(2) if card.front == "Spin-½ state vector")
    assert service.formula_text(card) == f"{card.definition}; {card.key_rule}"
