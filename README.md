# Quantum Mechanics FU — Telegram Learning Bot

A bilingual Telegram study bot for the FU Berlin quantum mechanics curriculum. It provides German–English terminology, formula recall, self-grading, spaced review, and progress statistics.

> This is an independent learning aid, not an official FU Berlin service. Verify examination rules, dates, permitted aids, and course requirements through official announcements and Campus Management.

## Implemented MVP

- `/start` — introduction and command menu
- `/topics` — all ten course chapter headings
- `/terms` — random bilingual terminology card
- `/formulas` — formula recall with usage guidance
- `/review` — number of due spaced-repetition items
- `/progress` — answer count and accuracy
- Inline reveal/self-grade flow
- SQLite progress persistence
- JSON curriculum repository with stable record IDs
- Initial content for Chapters 1–3 and skeletons for Chapters 4–10

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for package boundaries and extension guidance.

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Create a bot with Telegram's `@BotFather`, then put its token in `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=your_private_token
DATABASE_PATH=quantum_tutor.db
CURRICULUM_PATH=curriculum
TZ=Europe/Berlin
```

Run the bot:

```bash
quantum-tutor
```

Run tests:

```bash
pytest
```

Never commit `.env`, bot tokens, virtual environments, or database files.

## Curriculum coverage

1. Introduction
2. Quantum states and observables
3. Quantum dynamics
4. Density operators
5. Angular momentum and rotationally invariant problems
6. Perturbation theory
7. Addition of angular momenta
8. Particles in electromagnetic fields
9. Bell's theorem
10. Atoms, molecules, open and complex quantum systems, and quantum computers

`curriculum/experiments.json` also indexes the planned experimental topics: blackbody radiation, Stefan–Boltzmann law, photoelectric and Compton effects, electron diffraction, the statistical interpretation of the wavefunction, atomic models/Balmer series/Franck–Hertz experiment, and spin–orbit coupling.

## Content and attribution policy

Keep source URLs and distinguish official headings from original explanatory material. Do not copy full lecture scripts or exercise sheets without permission. Empty chapter records are intentional: they avoid presenting invented material as course-authorized content.

## Next milestones

- Populate verified Chapter 2 exercises and answer variants
- Turn `/review` into a due-item session
- Add formula-choice and worked-problem workflows
- Add reminders only after verified timetable data and user group selection exist
- Add mock exams clearly labeled as unofficial practice
