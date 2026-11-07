# Quantum Tutor
A private, bilingual (German–English) Telegram study bot for Quantum Mechanics, combining Quizlet-inspired flashcards, active recall, adaptive practice, spaced repetition, formula selection, derivations, exam simulations, reminders, and progress tracking.
Independent learning project. Quantum Tutor is not an official Freie Universität Berlin service or affiliated with Quizlet. Confirm examination rules, dates, rooms, permitted aids, and assessed material using official FU sources. Features marked Planned below are design goals, not claims about the current codebase.
Features and implementation status
Mode	Purpose	Status
🎯 Learn	Continuous adaptive multiple-choice questions with immediate explanations	Existing
⚖️ Laws & Rules	Self-graded physical laws, meanings, assumptions, and applications	Existing
🧮 Formulas	Self-graded equations with symbols, assumptions, and usage conditions	Existing
🗂 Topics	One menu for theory and experiments; select a topic to study all its cards together	Existing
🔁 Review	Practice missed and due cards from all topics in one automatic set	Existing
📈 Progress	Track accuracy and mastery	Existing
🔔 Reminders	Personal study prompts at configured Berlin times	Existing
🃏 Flashcards	Reveal an answer, then choose Know / Don't know	Existing
✍️ Write	Type terms, formulas, and explanations without answer choices	Planned
🧠 Apply	Choose the correct formula for an unfamiliar physics problem	Planned
📐 Derive	Practice mathematical derivations and assumptions	Planned
📝 Test / Exam	Timed, mixed-topic practice with restricted hints	Planned
📊 Skill mastery	Track recall, understanding, application, derivation, and problem-solving separately	Planned

The Telegram interface uses a persistent bottom keyboard. `/topics` opens a single menu with ten theory chapters and ten experimental topics—no duplicate chapter/subsection selection step. Selecting a topic immediately starts one automatic multiple-choice set containing all its concept cards and standalone formula cards. Original IDs are deduplicated; existing history is preserved. Empty topics are clearly marked. Finishing returns to the topic menu with refreshed percentages. Older subsection button messages still work for compatibility, but subsections are no longer required in normal navigation.

`/review` starts a separate cross-topic set: currently missed cards are available immediately (even before their scheduled ten-minute retry), alongside all due cards. Correctly answered cards remain saved with a future due date and return to Review when due. Formula cards are included as well as concept cards. Unknown/retired IDs are skipped without deleting their history. Reviews and queues are private to each account; active sessions are in memory, while review schedules survive restarts. Counters measure completion of the current set, not exam readiness.

Answer controls temporarily replace the keyboard; 🏠 Main menu exits a session. Commands remain available:
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
### Chapter 2 concept cards

The 29 cards from `QM_Chapter2_Concept_Cards_Updated.xlsx` are included in the whole-topic set when Chapter 2 is selected, together with its standalone formula cards. Subsection assignments are retained for organization and compatibility with older buttons; no subsection selection is required.

1. Choose the definition matching the concept from the answer buttons, or tap **Don't know**. There is no reveal-and-self-rating step in subsection sets.
2. Wrong answers and **Don't know** show the definition/key rule, then send the card to the back of the queue. If it is the only remaining card, it is presented again immediately.
3. A correct answer completes that unique card for the set and automatically presents the next card.
4. Prompts show `1/5 · 0% completed in this set`. The numerator is completed unique cards plus the current card; retries do not increase the denominator or completion percentage.
5. Once all cards are completed, the bot shows `100%` and returns to the single topic menu.

Set completion means successful multiple-choice recognition during this session—not durable mastery or exam readiness. Correct choices are automatically graded as Okay internally; wrong choices and Don't know are Repeat. Other flashcard modes use only Know / Don't know controls; the four-level scheduler is retained internally for historical compatibility. Every rating still updates persistent spaced-review history independently. The active queue is in memory and resets after a bot restart or when starting another set; users can exit through Main menu or Topics at any time. Original workbook wording and formulas are preserved without translation. Spreadsheet status is source metadata only. These are physics concept cards, not translation exercises. The separate 72-image formula workbook remains staged.

### Chapter 4 concept cards

The 50 cards from `QM_Chapter4_Concept_Learning_Cards.xlsx` are active under Chapter 4. They retain the original definitions and formulas without translation. Workbook numeric IDs are prefixed as `C4-001` through `C4-050` to avoid collisions with other chapters. Equation references, priorities, original section titles, and supplied source references are retained in `concept_metadata`. Spreadsheet progress does not reset account history.

| Section | Cards |
|---|---:|
| 4.1 Motivation | 3 |
| 4.2.1 Traces | 7 |
| 4.2.2 Density operators of pure states | 6 |
| 4.2.3 General density operators | 6 |
| 4.2.4 Examples | 5 |
| 4.2.5 Non-uniqueness of ensemble representations | 3 |
| 4.3 Von-Neumann equation | 3 |
| 4.4 Measurement for density operators | 4 |
| 4.5.1 Mixing quantum states | 3 |
| 4.5.2 Partial traces | 5 |
| 4.5.3 Entangled states | 5 |

Selecting a subsection automatically starts its multiple-choice set. Incorrect answers and Don't know return later; correct answers advance. Parent sections include their descendant cards. Source references are supplied by the workbook, not independently verified against the original lecture PDF.

### Chapter 5 concept cards

The 59 cards from `QM_Chapter5_Concept_Learning_Cards.xlsx` are active in Chapter 5. Original card IDs, concept names, formulas, and meanings are preserved without translation. Formula fields become key rules; meaning fields become definitions. Equation and supplied source references are retained in `concept_metadata`. Spreadsheet progress does not reset account history. The reattached Chapter 4 workbook was checked against the existing 50 cards and matched, so no duplicate import was needed.

| Subsection | Cards |
|---|---:|
| 5.1.1 Definition | 6 |
| 5.1.2 Angular momentum operator as generator of rotations | 3 |
| 5.1.3 Spectrum of the angular momentum operator | 12 |
| 5.1.4 Angular momentum operator in the position representation | 14 |
| 5.2.1 General considerations | 7 |
| 5.2.2 Spectrum of the hydrogen atom | 10 |
| 5.2.3 Orbitals of the hydrogen atom | 7 |

Subsections start automatic multiple-choice sets with saved progress; incorrect answers and Don't know requeue cards. Feedback includes both the meaning and formula. Workbook references are user-supplied, not independently verified against the lecture PDF.

### Chapter 6 concept cards

The 47 cards from `QM_Chapter6_Concept_Learning_Cards.xlsx` are available in Chapter 6. Original card IDs, concept names, formulas, and meanings are preserved without translation. Equation and supplied source references are stored in `concept_metadata`; spreadsheet progress does not reset user history.

| Section | Directly assigned cards |
|---|---:|
| 6.1 Time independent perturbation theory | 3 |
| 6.1.1 Non-degenerate situation | 16 |
| 6.1.2 An example: The anharmonic oscillator | 6 |
| 6.1.3 Degenerate situation | 5 |
| 6.2.1 Interaction picture | 8 |
| 6.2.2 Applications: Transitions of first order | 4 |
| 6.3 Some words on more general concepts of perturbation | 5 |

Selecting 6.1 starts a 30-card set including descendant subsections; selecting 6.2 starts its 12 descendant cards. Individual subsections start their own sets. Multiple-choice answers advance automatically; wrong answers and Don't know return later. Feedback includes both meaning and formula. Workbook source references have not been independently verified against the lecture PDF.

### Chapter 7 concept cards

The 47 cards from `QM_Chapter7_Concept_Learning_Cards.xlsx` are available in Chapter 7. Original concept names, formulas, meanings, and card IDs are preserved without translation. Equation and supplied source references are stored in `concept_metadata`; spreadsheet progress does not reset user history.

| Subsection | Cards |
|---|---:|
| 7.1.1 Spin operators | 6 |
| 7.1.2 Stating the general problem | 8 |
| 7.1.3 Coupling of two spins | 11 |
| 7.2.1 Possible values | 10 |
| 7.2.2 Glebsch-Gordan coefficients (original heading) | 2 |
| 7.2.3 An optional remark on group theory | 7 |
| 7.2.4 Adding orbital angular momentum and a spin | 3 |

Selecting 7.1 starts a 25-card set; selecting 7.2 starts a 22-card set. Individual subsections start their own automatic multiple-choice sets. Wrong answers and Don't know requeue cards; feedback includes both meaning and formula. Workbook references have not been independently verified against the lecture PDF.

### Chapter 9 concept cards

The 33 cards from `QM_Chapter9_Concept_Learning_Cards.xlsx` are available in Chapter 9. Original IDs, concept names, formula/definition fields, and meanings are preserved without translation. Equation and supplied source references are stored in `concept_metadata`. Spreadsheet progress does not reset user history.

| Section | Cards |
|---|---:|
| 9.1 Introduction | 2 |
| 9.2 The historical setting | 4 |
| 9.3.1 Correlation tables | 4 |
| 9.3.2 Properties of correlation tables | 5 |
| 9.3.3 Local hidden variables | 5 |
| 9.4 Deriving the Bell inequality | 11 |
| 9.5 Violation of the Bell inequalities | 2 |

Selecting 9.3 starts its 14 descendant cards. Individual sections start their own automatic multiple-choice sets. Wrong answers and Don't know return later; feedback includes both the meaning and formula/definition. Workbook references have not been independently verified against the lecture PDF.

### Chapter 8 concept cards

The 31 cards from `QM_Chapter8_Concept_Learning_Cards.xlsx` are available in Chapter 8. Original concepts, formulas, meanings, and IDs are preserved without translation. The workbook's coupling expressions, including their `1/c` factors, are retained rather than converted to another unit convention. Equation and supplied source references are stored in `concept_metadata`; spreadsheet progress does not reset user history.

| Section | Cards |
|---|---:|
| 8.1 Hamilton operator of spinless particles | 6 |
| 8.2.1 Hamiltonian of a particle in a constant magnetic field | 5 |
| 8.2.2 Normal Zeeman effect | 5 |
| 8.2.3 Anomalous Zeeman effect | 5 |
| 8.3.1 Aharanov Bohm effect (original heading) | 3 |
| 8.3.2 Flux quantization in superconductors | 4 |
| 8.3.3 Landau levels | 3 |

Selecting 8.2 starts a 15-card set; selecting 8.3 starts a 10-card set. Individual subsections start their own automatic multiple-choice sets. Wrong answers and Don't know return later; feedback includes meaning and formula. Workbook references have not been independently verified against the lecture PDF.

### Chapter 10 concept cards

The 71 cards from `QM_Chapter10_Concept_Learning_Cards.xlsx` are available in Chapter 10, covering all 11 named subsections. Original concept names, formulas/key ideas, meanings, and IDs are preserved without translation. Equation references, priorities, and supplied source references are stored in `concept_metadata`; spreadsheet progress does not reset user history.

| Subsection | Cards |
|---|---:|
| 10.1.1 Reduced system dynamics | 8 |
| 10.1.2 Decoherence | 10 |
| 10.1.3 Quantum channels | 8 |
| 10.1.4 Markovian evolution and exponential decay | 9 |
| 10.2.1 Alkali atoms | 3 |
| 10.2.2 Helium atom | 1 |
| 10.3.1 Quantum many-body systems and condensed matter | 4 |
| 10.3.2 Bose-Hubbard model | 9 |
| 10.3.3 Mean field theory | 16 |
| 10.4.1 Quantum key distribution and the BB84 scheme | 2 |
| 10.4.2 Quantum computing | 1 |

Parent sections start combined sets: 10.1 has 35 cards, 10.2 has 4, 10.3 has 29, and 10.4 has 3. Individual subsections start their own automatic multiple-choice sets. Single-card sets use distractors from the wider concept collection and repeat immediately after Don't know until answered correctly. Feedback includes meaning and formula/key idea. Workbook references have not been independently verified against the lecture PDF.

### Experimental concept cards

The 48 cards from `QM_Experimental_Topics_Concept_Learning_Cards.xlsx` are included in the existing experimental topics. Original IDs (`EXP-001`–`EXP-048`), concept names, and meanings are preserved. Raw workbook formulas are stored in `concept_metadata.original_formula`; display formulas use equivalent plain-text notation rather than unsupported raw LaTeX. Source references and the workbook's explicit **not verified against Franke slides** status are retained. These are standard-reference practice materials, not verified official course cards.

| Topic | Supplied date | Imported concept cards |
|---|---|---:|
| Schwarzkörperstrahlung | 03.11.2026 | 10 |
| Stefan–Boltzmann-Gesetz | 05.11.2026 | 5 |
| Photoeffekt | 10.11.2026 | 4 |
| Compton-Effekt | 10.11.2026 | 4 |
| Elektronenbeugung | 12.11.2026 | 5 |
| Statistische Deutung der Wellenfunktion | 17.11.2026 | 7 |
| Atommodelle | Termin offen | 3 |
| Balmer-Serie | Termin offen | 3 |
| Franck-Hertz-Versuch | Termin offen | 2 |
| Spin-Bahn-Kopplung | Termin offen | 5 |

The workbook groups some topics into shared lecture entries. Splitting those cards between the existing topic buttons is an authored organizational mapping, not an official FU chapter assignment. Each imported ID occurs once. Topic sets also include existing standalone formula cards, so their total can exceed the imported concept count. Missed experimental cards enter the shared Review section immediately; due cards return according to their saved schedules. Workbook progress never resets either account's history.

The reattached Chapter 8 (31 cards) and Chapter 10 (71 cards) workbooks were checked against existing card IDs, sections, names, meanings, and formulas and matched; no duplicate imports were needed.

### Saved topic and subsection progress

Topic buttons show account-specific percentages, refreshed whenever the topic menu opens and after a set completes. Subsection metadata is retained but a separate contents-selection step is no longer displayed. The percentage is the number of available cards with a currently successful saved review state divided by the number of available cards. Topic totals include concept cards and formulas; subsection totals include concept cards assigned to that section or its descendants. A subsequent wrong answer reduces progress. Duplicate attempts do not inflate it. Empty sections show `— no cards` rather than claiming coverage or mastery. Percentages indicate learned/recognition progress, **not** durable understanding or exam readiness. Saved progress survives restarts; active set queues remain temporary. Old keyboard labels still route correctly after percentages change.

### Experimental dates in the topic selector

Experimental topic buttons show the supplied teaching date before the topic name, for example `🔬 03.11.2026 · Schwarzkörperstrahlung`. Undated experimental topics show `Termin offen`; no dates are guessed. These dates remain user-supplied rather than independently verified announcements. Photoeffekt and Compton-Effekt share 10.11.2026.

### Detailed script contents

All 109 sections and subsections supplied for `QMChapter1.pdf` through `QMChapter10.pdf` are recorded in `curriculum/script_contents.tsv` and the active theory topic records, including page references. Selecting a theory chapter now starts all its cards together, rather than displaying another subsection-selection menu. Section headings and page references remain in the curriculum data. PDF filenames and translation notices are not displayed. Original English titles are retained in the data; German translations are authored for the interface. Supplied spellings such as “Glebsch-Gordan” and “Aharanov Bohm” remain in the original-title fields, while display titles use Clebsch–Gordan and Aharonov–Bohm.

These are user-supplied contents, not independently checked PDF extracts or claims of examination coverage. Indexing every section does **not** mean every section already has lessons or exercises. The 10 experimental topic buttons remain available alongside the 10 theory chapters. The workbook’s 72 image-based records remain staged separately.

Implementation guidance for /topics:
- Preserve the existing ten German chapter buttons and chapter IDs 1–10; do not silently renumber them to the 20-item combined study sequence or break existing progress.
- The bottom topic selector now includes ten numbered theory chapters and ten 🔬 experimental topic buttons. Shared lecture entries may have separate topic buttons while retaining the same date. Theory IDs 1–10 are unchanged; experimental topics use internal IDs 11–20.
- `curriculum/topic_*.json` is the active catalog; legacy `chapter_*.json` files are retained as a fallback and are not loaded alongside it. Existing formula IDs are preserved. Supplied dates are labeled as user-provided in the bot until independently verified.
- If adding a unified /syllabus view, use the combined sequence above with explicit lecturer, date, track, and source-status fields.
- Link experimental topics to theory chapters using optional cross-references, not by claiming those mappings are official FU chapter assignments.
- Theory chapters 1–4 have initial authored study records. Some experimental topics also have formula cards; other listed topics remain unpopulated and are clearly marked in the bot. The workbook import remains staged, not enabled as exercises. Topic visibility does not imply complete learning or exam coverage.
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
