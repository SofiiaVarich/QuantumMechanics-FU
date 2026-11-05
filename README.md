Quantum Tutor
Quantum Tutor
A private, bilingual (German–English) Telegram study bot for Quantum Mechanics, combining Quizlet-inspired flashcards, active recall, adaptive practice, spaced repetition, formula selection, derivations, exam simulations, reminders, and progress tracking.
Independent learning project. Quantum Tutor is not an official Freie Universität Berlin service or affiliated with Quizlet. Confirm examination rules, dates, rooms, permitted aids, and assessed material using official FU sources. Features marked Planned below are design goals, not claims about the current codebase.
Features and implementation status
Mode	Purpose	Status
🎯 Learn	Continuous adaptive multiple-choice questions with immediate explanations	Existing
⚖️ Laws & Rules	Self-graded physical laws, meanings, assumptions, and applications	Existing
🧮 Formulas	Self-graded equations with symbols, assumptions, and usage conditions	Existing
🗂 Topics	Select one of ten German chapter buttons and scope learning to it	Existing
🔁 Review	View due items under the current spaced-review schedule	Existing
📈 Progress	Track accuracy and mastery	Existing
🔔 Reminders	Personal study prompts at configured Berlin times	Existing
🃏 Flashcard ratings	Reveal an answer, then choose Repeat / Hard / Okay / Easy	Existing
✍️ Write	Type terms, formulas, and explanations without answer choices	Planned
🧠 Apply	Choose the correct formula for an unfamiliar physics problem	Planned
📐 Derive	Practice mathematical derivations and assumptions	Planned
📝 Test / Exam	Timed, mixed-topic practice with restricted hints	Planned
📊 Skill mastery	Track recall, understanding, application, derivation, and problem-solving separately	Planned

The Telegram interface uses a persistent bottom keyboard. /topics opens ten German-only chapter buttons. Selecting one makes it the active chapter; Learn, Laws & Rules, and Formulas then stay within that chapter. Chapters without reviewed records are clearly marked instead of receiving invented material. Answer and grading controls temporarily replace the keyboard; 🏠 Main menu clears the active chapter and exits the session. Commands remain available:
/start       Main menu
/learn       Adaptive multiple-choice practice
/laws        Physical laws and application rules
/formulas    Formula flashcards
/topics      Clickable German chapter selection
/review      Due reviews
/progress    Study statistics
Proposed commands (not yet implemented): /flashcards, /write, /apply, /derive, /test, /exam, /weak, /settings.
Learning philosophy
The bot follows a repeatable cycle:

Study → Recall without hints → Check → Explain the mistake → Rate difficulty → Schedule another review → Apply in a new context.

The system borrows general learning patterns familiar from Quizlet, but does not reproduce or claim to use Quizlet's proprietary algorithms.
1. Active recall
   Before revealing an answer, the learner must attempt to retrieve it. Recognition questions are useful for beginners but should eventually give way to typed answers, derivations, and independent problem-solving.
2. Multiple practice modes
   - Flashcards: front shows one atomic question; back gives a concise answer and optional explanation. Self-grade after reveal.
   - Learn: automatically graded multiple-choice questions with plausible distractors and immediate feedback.
   - Write (planned): enter the answer without options; normalize harmless notation differences and explain errors. Never silently treat a mathematically different expression as equivalent.
   - Apply (planned): select a formula from problem clues; identify assumptions and units before calculating.
   - Derive (planned): reconstruct derivations step by step, including hypotheses and boundary conditions.
   - Test (planned): mixed questions without teaching hints, followed by an error report.
   - Exam (planned): timed, closed-hint simulation reflecting verified course requirements and permitted aids.
3. Exercise cycle (current Learn mode)
4. Present a physical law or formula multiple-choice question with visual cues.
5. Accept a response through Telegram's bottom keyboard.
6. Grade automatically. After an incorrect choice, keep the same question active without revealing the answer.
7. Require a correct choice before showing the explanation and advancing.
8. Continue in the same category; display progress such as 2/200.
9. Increase the review interval for a correct first attempt or schedule an earlier review after a wrong attempt.
10. Allow 🏠 Main menu to leave at any time.
    Current scheduling: Repeat returns in about 10 minutes; Hard holds the current stage with a one-day interval; Okay advances one stage through 1, 3, 7, 14, 30, and 60 days; Easy advances two stages. Multiple-choice answers map to Okay or Repeat so recognition practice cannot claim the strongest recall rating.
11. Quizlet-inspired recall ratings (implemented)
    After revealing a flashcard answer, the learner chooses one of four ratings:
    Rating	Meaning	Scheduling intent
    🔁 Repeat	I forgot or could not answer	Retry soon, within the session
    🟠 Hard	Correct only with difficulty	Shorter review interval
    🔵 Okay	Correct with some effort	Normal interval
    🟢 Easy	Immediate, confident recall	Longer interval
These are Quantum Tutor controls, not a claim about Quizlet's exact scheduling implementation. Every new review event records its rating, response time, and scheduler version. Existing review rows and due dates remain unchanged during the additive SQLite migration; the nuanced scheduler applies when an item is answered again. These intervals are product defaults, not scientifically guaranteed optimal intervals.
5. Question difficulty and progression (planned)
A single physics concept should be tested at increasing cognitive depth:
Level	Example: Schrödinger equation	Skill
1. Recognize	Identify the equation among alternatives	Recognition
2. Recall	Write the equation without hints	Memory
3. Explain	Define the Hamiltonian and wavefunction	Understanding
4. Select	Determine when the stationary equation applies	Application
5. Derive	Derive the stationary eigenvalue equation using separation of variables	Derivation
6. Solve	Solve a new potential-well problem	Problem-solving
A correct recognition answer must not automatically mark derivation or problem-solving as mastered.
6. Separate skill mastery (planned)
For each topic, track distinct scores for:
- Physical laws, meanings, and conditions
- Formula recall
- Physical interpretation
- Formula selection and applicability
- Mathematical derivation
- Independent problem-solving
  Store the evidence behind each score: attempts, outcomes, question difficulty, response time, hints used, and recent performance. Avoid treating a percentage as an official exam-pass probability.
Suggested mastery labels: 🌱 Learning (new or unstable), 📘 Familiar (several successful recalls), 🏆 Mastered (consistent successful reviews across multiple intervals and appropriate question types). Mastery can decline when subsequent reviews fail.

The current implementation uses the existing three labels and its established review stages; the skill-specific interpretation is a planned enhancement.
7. Adaptive question selection (planned)
Prioritize questions in this order, with configurable weights:
1. Overdue reviews and recently missed questions.
2. Weak skills within the currently selected topic.
3. New questions within a manageable daily limit.
4. Mixed questions from previously studied chapters.
5. Occasional well-mastered questions to detect forgetting.
   Avoid showing distractors in a predictable order. Current Learn mode repeats the same question until it is answered correctly and withholds the explanation during retries. A future advanced mode may follow a mistake with a related variant before returning to the original concept. Do not reveal answers before a genuine recall attempt in assessment modes.
6. Exam readiness (planned)
   An exam-readiness dashboard should ask whether the learner can:
7. Define the concept precisely in German or English.
8. Recall and explain every symbol in its formulas.
9. State the assumptions and domain of validity.
10. Derive key results where required.
11. Select the right method from an unfamiliar prompt.
12. Solve a standard exercise independently.
13. Solve a modified or mixed-topic exercise.
14. Check dimensions, limiting cases, normalization, and physical plausibility.
15. Explain mistakes and correct them.
16. Complete representative problems under exam timing and permitted-aid constraints.
    A topic should not receive an exam-ready label based on flashcard accuracy alone. Require evidence from unfamiliar problems and timed practice, and present readiness as a study estimate rather than a guarantee of passing.
    Curriculum — FU Berlin Quantenmechanik WS 2026/27
This learning curriculum combines the official theoretical chapter sequence of Prof. Dr. Jens Eisert with the dated experimental lecture entries published by Prof. Dr. Katharina Franke. The single combined sequence below is a PROPOSED STUDY ORDER, not a university-published chronological teaching plan: individual dates for Eisert’s ten chapters have not been published. Do not interpret an undated topic as a cancelled or unscheduled class. The seven experimental schedule entries are expanded into separate study topics where a single lecture lists multiple concepts.

Combined study sequence (20 topics)
#	Published date	Lecturer	Topic (German / English)	Track / source status
01	Not specified	Prof. Dr. Jens Eisert	Einführung in die Quantenmechanik / Introduction	Theory chapter 1; study placement suggested
02	03.11.2026	Prof. Dr. Katharina Franke	Schwarzkörperstrahlung / Blackbody radiation	Experimental lecture; dated
03	05.11.2026	Prof. Dr. Katharina Franke	Stefan–Boltzmann-Gesetz / Stefan–Boltzmann law	Experimental lecture; dated
04	10.11.2026	Prof. Dr. Katharina Franke	Photoeffekt / Photoelectric effect	Experimental lecture; dated (shared session)
05	10.11.2026	Prof. Dr. Katharina Franke	Compton-Effekt / Compton effect	Experimental lecture; dated (shared session)
06	12.11.2026	Prof. Dr. Katharina Franke	Elektronenbeugung / Electron diffraction	Experimental lecture; dated
07	Not specified	Prof. Dr. Jens Eisert	Quantenzustände und Observablen / Quantum states and observables	Theory chapter 2; study placement suggested
08	17.11.2026	Prof. Dr. Katharina Franke	Statistische Deutung der Wellenfunktion / Statistical interpretation of the wavefunction	Experimental lecture; dated
09	Not specified	Prof. Dr. Jens Eisert	Quantendynamik / Quantum dynamics	Theory chapter 3; study placement suggested
10	Not specified	Prof. Dr. Jens Eisert	Dichteoperatoren / Density operators	Theory chapter 4; study placement suggested
11	Not specified	Prof. Dr. Jens Eisert	Drehimpuls und rotationsinvariante Probleme / Angular momentum and rotationally invariant problems	Theory chapter 5; study placement suggested
12	Not announced	Prof. Dr. Katharina Franke	Atommodelle / Atomic models	Experimental lecture; date pending (shared entry)
13	Not announced	Prof. Dr. Katharina Franke	Balmer-Serie / Balmer series	Experimental lecture; date pending (shared entry)
14	Not announced	Prof. Dr. Katharina Franke	Franck-Hertz-Versuch / Franck–Hertz experiment	Experimental lecture; date pending (shared entry)
15	Not specified	Prof. Dr. Jens Eisert	Störungstheorie / Perturbation theory	Theory chapter 6; study placement suggested
16	Not specified	Prof. Dr. Jens Eisert	Addition von Drehimpulsen / Addition of angular momenta	Theory chapter 7; study placement suggested
17	Not announced	Prof. Dr. Katharina Franke	Spin-Bahn-Kopplung / Spin–orbit coupling	Experimental lecture; date pending
18	Not specified	Prof. Dr. Jens Eisert	Teilchen in elektromagnetischen Feldern / Particles in electromagnetic fields	Theory chapter 8; study placement suggested
19	Not specified	Prof. Dr. Jens Eisert	Bellsches Theorem / Bell's theorem	Theory chapter 9; study placement suggested
20	Not specified	Prof. Dr. Jens Eisert	Atome, Moleküle, offene und komplexe Quantensysteme und Quantencomputer / Atoms, molecules, open and complex quantum systems, and quantum computers	Theory chapter 10; study placement suggested


Official FU source pages:
- Eisert (theory, WS 2026/27): https://www.physik.fu-berlin.de/en/einrichtungen/ag/ag-eisert/teaching/ws26-27/index.html
- Franke (experimental lecture dates, WS 2026/27): https://www.physik.fu-berlin.de/en/einrichtungen/ag/ag-franke/courses/26-WS-Quantenmechanik/index.html
Implementation guidance for /topics:
- Preserve the existing ten German chapter buttons and chapter IDs 1–10; do not silently renumber them to the 20-item combined study sequence or break existing progress.
- Add a separate experimental track or view for Franke's seven published lecture entries; multiple concepts in a single entry may have their own study cards while sharing the same lecture date.
- If adding a unified /syllabus view, use the combined sequence above with explicit lecturer, date, track, and source-status fields.
- Link experimental topics to theory chapters using optional cross-references, not by claiming those mappings are official FU chapter assignments.
- Chapters 1–3 currently have initial study records. Chapters 4–10 remain content skeletons. curriculum/experiments.json is an index of planned experimental content; listed topics do not imply fully populated, reviewed flashcards or exercises.
- Never claim an item is assessed in the examination without explicit instructor confirmation. Maintain a source-verified course coverage map separately from original practice questions.
Recommended question record (planned schema)
{
"id": "qm_ch03_schrodinger_stationary_01",
"chapter": 3,
"topic": "Schrodinger equation",
"skill": "formula_selection",
"difficulty": 3,
"language": "en",
"question": "When can a stationary-state eigenvalue equation be used?",
"answer": "For energy eigenstates of a time-independent Hamiltonian.",
"explanation": "A stationary state has a time-independent spatial wavefunction and a phase factor in time.",
"assumptions": ["Time-independent Hamiltonian"],
"source_url": null,
"source_type": "original_practice",
"reviewed": false
}
This JSON is a proposed conceptual example, not necessarily compatible with the current curriculum parser. A new schema requires a versioned migration and validation tests. For mathematical formulas, retain both a human-readable expression and a normalized representation where appropriate.
Recommended review record (planned schema)
{
"user_id": 123456789,
"question_id": "qm_ch03_schrodinger_stationary_01",
"rating": "hard",
"graded_correct": true,
"reviewed_at": "2026-11-05T19:00:00+01:00",
"due_at": "2026-11-06T19:00:00+01:00",
"response_ms": 15000,
"hints_used": 0,
"scheduler_version": 2
}
Use UTC internally for timestamps and convert to Europe/Berlin for display and reminder scheduling. The user ID above is a fictitious example, not a configuration value.
Quick start
Requirements
- Python 3.11 or newer
- A Telegram bot created through @BotFather
- Your numeric Telegram user ID
- An internet connection
1. Install
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e '.[dev]'
2. Configure
   cp .env.example .env
   Edit .env locally:
   TELEGRAM_BOT_TOKEN=your_new_private_token
   TELEGRAM_ALLOWED_USER_IDS=first_numeric_user_id,second_numeric_user_id
   DATABASE_PATH=data/quantum_tutor.db
   CURRICULUM_PATH=curriculum
   TZ=Europe/Berlin
   REMINDER_TIMES=05:30,20:00
   TELEGRAM_ALLOWED_USER_IDS accepts comma-separated numeric IDs. Every allowed account receives its own progress history and configured reminders. REMINDER_TIMES accepts comma-separated 24-hour times. Reminders are personal study prompts, not official timetable notifications.
   Security: Never paste a bot token into chats, source code, commits, screenshots, or logs. If exposed, revoke it immediately through @BotFather and create a replacement.
3. Run locally
   source .venv/bin/activate
   quantum-tutor
   Open the bot in Telegram and send /start. The process stops when the computer sleeps, shuts down, loses connectivity, or terminates.
   Keep the bot online
   On an always-on machine with Docker:
   docker compose up -d --build
   Check status and logs:
   docker compose ps
   docker compose logs -f bot
   Restart after changes:
   docker compose up -d --build
   Stop:
   docker compose down
   The Compose service uses restart: unless-stopped to restart after crashes and host reboots. Docker Desktop must be running on macOS; a sleeping Mac cannot provide reliable 24/7 reminders. Use a VPS or another continuously running server if needed.
   Development
   source .venv/bin/activate
   pytest
   src/quantum_tutor/
   ├── application/       # Study workflows and exercise generation
   ├── domain/            # Models and spaced-repetition rules
   ├── infrastructure/    # JSON curriculum and SQLite persistence
   ├── presentation/      # Telegram handlers and buttons
   ├── config.py          # Environment settings
   ├── scheduler.py       # Reminder jobs
   └── main.py            # Application composition and startup
curriculum/             # Terms, formulas, and chapter records
tests/                  # Automated tests
See [`ARCHITECTURE.md`](ARCHITECTURE.md) for design details.
Suggested implementation roadmap
Phase 1 — Preserve and test the baseline
- Verify current Learn, Laws & Rules, Formulas, Topics, Review, Progress, and reminders.
- Add regression tests for current scheduling and progress storage.
  Phase 2 — Rich flashcards and ratings
- [x] Add answer reveal and Repeat / Hard / Okay / Easy buttons.
- [x] Record rating, response time, scheduler version, and deterministic intervals.
- [ ] Add dedicated due-card and weak-card learning queues.
  Phase 3 — Written and conceptual practice
- Add typed answers, formula parsing, notation tolerance, and manual override for ambiguous grading.
- Add bilingual explanations, misconception tags, and formula-selection questions.
  Phase 4 — Physics depth
- Add derivation prompts, partial-credit rubrics, and problem-solving questions.
- Track mastery separately for each skill and topic.
  Phase 5 — Exam preparation
- Add timed tests, mixed-topic sessions, exam readiness diagnostics, and exportable progress reports.
- Map assessment content to verified FU sources and permitted-aid rules.
  Acceptance criteria for new learning features
- Every answer is graded consistently, and the correct explanation is available after submission.
- Ratings and due dates persist across bot restarts.
- Review scheduling is deterministic under a frozen clock and timezone-aware.
- Missed cards reappear without trapping the learner in an infinite loop.
- Repeated multiple-choice recognition cannot alone yield full topic mastery.
- Sessions can be exited with 🏠 Main menu.
- Old SQLite progress survives versioned migrations and can be backed up.
- Timed tests do not leak answers before submission.
- Private access restrictions apply to every new command and callback.
  Adding learning material
  Add records to the appropriate curriculum/chapter_NN.json. Every term, formula, or question needs a stable, globally unique ID because review history references it.
Content rules:
- Distinguish official course headings from original exercises and proposed study material.
- Include verified source URLs where available and a content review status.
- Never claim that a topic will appear on an exam without explicit instructor confirmation.
- Do not redistribute full lecture scripts or exercise sheets without permission.
- Store equations, assumptions, symbol definitions, usage conditions, examples, and common mistakes together.
- Write one focused retrieval question per flashcard; use multi-step tasks for derivations and problems.
- Check mathematical correctness, boundary conditions, units, and notation before publishing a question.
  Privacy and data
- Access is restricted to the comma-separated IDs in TELEGRAM_ALLOWED_USER_IDS.
- Learning history is stored locally in SQLite.
- .env, databases, virtual environments, and logs are excluded from Git.
- Telegram processes messages sent through the bot; avoid submitting sensitive personal information.
- Before deploying, back up the database and protect its file permissions.
- A future export/delete-history function should be explicit, user-controlled, and tested.
  Product goal
  Understand the physical laws. Recall the formulas. Recognize when to use them. Derive the results. Solve unfamiliar problems.
Quantum Tutor should optimize for durable understanding and exam-relevant problem-solving—not merely for a high flashcard streak.
