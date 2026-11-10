# Quantum Tutor

A Telegram bot **and Mini App**, with public or allowlist-restricted access, for quantum mechanics, sharing one curriculum and progress database. The chat bot handles study sessions and reminders; the Mini App adds a visual course browser, typeset formulas, answer buttons, review, and progress screens.

This is an independent learning project, **not an official Freie Universität Berlin service or affiliated with Quizlet**. Recognition practice supports study but does not establish independent recall, derivation ability, problem-solving skill, or exam readiness. Confirm examination coverage, dates, rooms, and permitted aids with official FU sources.

## Using the bot

Send `/start` to open the main menu. Full navigation controls are shown on the main menu, not on question or completion keyboards.

| Command / mode | Current behavior |
|---|---|
| `/learn` — Learn | Choose a topic and practice its whole card set with multiple-choice answers. |
| `/formulas` — Formulas | Choose a topic and practice its equation-bearing cards, including imported concepts and standalone formulas. Verbal-only cards are omitted. |
| `/laws` — Laws & Rules | Choose a topic and practice its whole set of laws, concepts, and rules. |
| `/topics` — Chapters & Experiments | Choose an explicitly labeled **Chapter 1–10** or **Experiment** by name. Experiment entries include their supplied date or Termin offen. Selecting one starts its whole set; no subsection-selection step is required. |
| `/review` — Review | Start a cross-topic set containing currently missed cards and scheduled cards that are due. |
| `/progress` — Progress | Show the current account's study statistics. |

### Questions and completion

- **Every equation-bearing card uses readable formula choices in every mode**, including Learn, Laws & Rules, and Review. Verbal cards use definition/meaning choices. Formula buttons omit appended assumptions; feedback retains the meaning, assumptions, and applicable source warnings.
- Question keyboards contain **answer choices, Don't know, and Main menu only**. There are no mode-switching, Chapters & Experiments, or Review shortcuts on these keyboards.
- Wrong answers and **Don't know** show feedback, requeue the card at the back of the active set, and immediately save it as missed for Review. If it is the only remaining card, it can appear again immediately.
- A correct answer completes that unique card in the current set and advances automatically. Retries do not inflate the set size or completion percentage.
- On completion, the keyboard contains **Main menu only**. Tap it to return to full navigation. Main menu also lets you leave an unfinished session.

Telegram **chat** buttons use Unicode/plain text. The **Mini App** uses KaTeX for formulas. Answer buttons preserve the exact answer text using escaped LaTeX text mode; they do not replace it with a broader or different equation from card metadata. Feedback additionally typesets supplied mathematical LaTeX. This means answer buttons are not yet fully converted to structural LaTeX fractions and matrices. Unsupported notation or unavailable KaTeX falls back to the readable original text, rather than displaying a red parser error. Original formulas and renderer metadata remain in the curriculum.

Chapter 2 regression checks exclude equivalent spectral-theorem/unitary-diagonalization answers and overlapping spin-measurement/projection-postulate answers from each other's distractor pools. The spin-state-vector answer explicitly includes both the state expansion and normalization. Grading checks the selected index in the server-generated question, not the rendered HTML. These fixes address reproduced ambiguities; automatic distractor selection is still heuristic, not a proof that every alternative in every chapter is false.

### Review, progress, and reminders

Missed cards are available in Review immediately, even before their scheduled retry time. Correctly answered cards remain saved with a future due date and return when due. Review includes both concept and standalone formula cards; unknown or retired IDs are skipped without deleting their history.

Multiple-choice success maps to the internal **Okay** rating; wrong answers and Don't know map to **Repeat**. Repeat schedules a retry in about ten minutes, while Okay advances through review intervals of 1, 3, 7, 14, 30, and 60 days. Historical Hard/Easy scheduler support is not a four-button rating step in the current whole-topic flow.

Progress and review history are private to each allowed account and shared across modes through stable card IDs. Topic percentages refresh when the picker opens and reflect available cards with a currently successful saved review state. A later mistake can reduce progress; repeated attempts do not inflate it. These are recognition-progress indicators, not separate skill mastery or exam-pass estimates.

SQLite review history and schedules survive restarts. Active sessions and their queues are in memory and do not. Reminders are personal study prompts at configured local times, not official timetable notifications; reminder messages use the full main menu.

## Curriculum and source status

The active catalog is **`curriculum/topic_1.json` through `curriculum/topic_20.json`**, covering 20 topics. Theory chapter IDs 1–10 and experimental topic IDs 11–20 are stable; do not renumber them into a proposed chronological study order. The duplicate legacy `chapter_01.json`–`chapter_10.json` and `experiments.json` catalog is retired, not an additional source to load or maintain.

Current catalog snapshot:

- **543 imported concept cards**: 495 theory cards across Chapters 2–10 and 48 experimental cards.
- **12 standalone formula cards**, for **555 active cards total**, with stable, globally unique IDs.
- **109 source sections/subsections** indexed in [`curriculum/script_contents.tsv`](curriculum/script_contents.tsv) and represented in theory topic outlines, including supplied page references. An outline entry does not imply that a lesson or exercise exists for it.
- **72 image-based formula records** remain staged separately in `curriculum/imported/`. They are not active exercises and are not included in the 555-card total. Keep these staged records and the source index.

Topic sets combine the topic's eligible concept and standalone formula cards. Source sections remain metadata for organization and compatibility, rather than an extra navigation step. Imported IDs, source references, original titles, workbook metadata, and raw formulas are retained where supplied. German interface translations and mappings of shared experimental lecture entries to separate topics are authored organization, not official FU assignments. Spreadsheet progress does not replace account history.

### Official sources and supplied dates

- [Prof. Dr. Jens Eisert — theoretical quantum mechanics, WS 2026/27](https://www.physik.fu-berlin.de/en/einrichtungen/ag/ag-eisert/teaching/ws26-27/index.html)
- [Prof. Dr. Katharina Franke — experimental quantum mechanics, WS 2026/27](https://www.physik.fu-berlin.de/en/einrichtungen/ag/ag-franke/courses/26-WS-Quantenmechanik/index.html)

The theory sequence follows ten chapter headings; individual theory chapter dates have not been supplied. Experimental topic buttons show the supplied dates: blackbody radiation 03.11.2026, Stefan–Boltzmann law 05.11.2026, photoelectric and Compton effects 10.11.2026, electron diffraction 12.11.2026, and statistical interpretation of the wavefunction 17.11.2026. Atomic models, Balmer series, Franck–Hertz experiment, and spin–orbit coupling show **Termin offen** rather than guessed dates.

**These dates and source references are supplied information, not independently verified announcements.** Shared dates can correspond to one lecture split into several study topics. Any interleaving of theory and experiments is a proposed study order, not a university-published chronological teaching plan. Missing dates do not imply cancelled classes.

The script index is user-supplied, not an independently checked PDF extraction. Experimental workbook cards are standard-reference practice material and have **not been verified against Franke's slides**. Workbook claims of script verification remain supplied claims, not independent verification by this project.

### Correctness audit and limitations

See [`CONTENT_AUDIT.md`](CONTENT_AUDIT.md) for **21 corrected/clarified records**, **12 source-dependent cards flagged for review**, and multiple-choice safeguards. Corrected originals are retained in `content_corrections`; uncertain records use `content_review_required` and display a source-check warning in feedback. Documented corrections take precedence over earlier claims of exact import preservation.

Software consistency checks and mathematical review are **not full verification against the original lecture PDFs** or certification of examination coverage. Distractor filters reduce duplicate, overlapping, and ambiguous choices but do not prove every distractor is semantically false. Check source conventions, units, assumptions, and boundary conditions when studying.

## Telegram Mini App

### Interactive Spheres — Chapter and Experiment Navigation

**Crystal Atlas version 9:** The authenticated Mini App opens directly on the Atlas landing page, with cyan chapter spheres, mint experiment spheres, and the supplied design's interactive WebGL crystal. A static topic list remains an accessible alternative. The supplied HTML is the visual reference; its placeholder questions are not used. Three.js r128 loads from a pinned CDN URL; a CSS crystal remains visible if the library or WebGL is unavailable. Small spheres use liquid-metal mini crystals with readable number chips, rendered through one shared WebGL renderer. Orbit paths have stronger outlines and glow. Dragging the large crystal produces direction-preserving momentum that gradually slows to a stop; there is no automatic reversal or idle spin. Stale releases, cancelled gestures, page hiding, and reduced-motion preferences stop momentum. Animation pauses when the page is hidden and respects reduced-motion preferences. Learn, Formulas, Laws, Review, and progress remain accessible from the Atlas.

Every sphere (*Kugel*) in the Quantum Atlas represents **exactly one chapter or experiment** and acts as a clickable entry point to its exercises.

- **10 Chapter Spheres (01–10):** Each sphere is assigned to one specific quantum mechanics chapter.
- **10 Experiment Spheres (E1–E10):** Each sphere is assigned to one specific experimental topic.
- **Unique Mapping:** Every sphere has its own stable topic ID, title, description, and exercise collection. Descriptions must reflect the corresponding curriculum, not placeholder content.
- **Click Interaction:** Clicking or touching a sphere opens the exercises belonging exclusively to that chapter or experiment, filtered by the selected study mode where applicable.
- **Exercise Content:** Questions, formulas, concepts, and explanations must be loaded through the existing exercise system from the corresponding curriculum file.
- **Independent Progress:** Each chapter and experiment displays its own learning progress for the authenticated account, using the existing saved review history.
- **Orbital Animation:** All 20 spheres move along their respective orbits while remaining clickable. Respect reduced-motion preferences by keeping spheres stationary when requested.

#### Topic Mapping

| Sphere | Stable topic ID | Curriculum | Content |
|---|---|---|---|
| 01–10 | 1–10 | `curriculum/topic_1.json` – `curriculum/topic_10.json` | Quantum mechanics chapters 1–10 |
| E1–E10 | 11–20 | `curriculum/topic_11.json` – `curriculum/topic_20.json` | Experimental topics 1–10 |

For experiment sphere E*n*, the stable topic ID is **10 + n**. Sphere labels are display names, not new curriculum IDs.

#### Required Behavior

**When a student taps Sphere 03, only Chapter 3 exercises must open (`topic_id: 3`). When a student taps Sphere E05, only Experiment 5 exercises must open (`topic_id: 15`).**

The central **Q** may start a general study session, but it must not override the individual sphere-to-topic mapping. Whole-course sessions must be an explicit, separate action.

The interface must use the existing authenticated Quantum Tutor exercise system rather than placeholder questions. Each sphere must preserve its assigned topic throughout animation, selection, and navigation. Animation may change a sphere's position, but never its identity, click target mapping, or curriculum source. Sphere selection must submit its stable topic ID to the existing `/api/session` endpoint; the server remains responsible for authentication, card selection, grading, retries, and saved progress.


Configure `MINI_APP_URL=https://your-public-host/`, deploy the `web` service, and restart `bot`. Telegram then offers a **Study App** menu button, an **Open Mini App** reply-keyboard button, and `/app` to show the launcher. Existing chat commands keep working.

The Mini App provides Learn, Formulas, Laws, whole-topic or whole-course sets, chapter/experiment browsing, missed/due review (optionally scoped to a topic), completion, progress, and resume while the web service remains running. Answers are submitted once using short-lived per-question nonces. Wrong answers and Don't know requeue cards. Feedback stays visible until Next is tapped; completion shows Main menu. Web and chat use separate in-memory active queues but share saved SQLite history.

### Authentication and privacy

Open the Mini App **inside Telegram**, not as an ordinary browser link. Every API request validates the HMAC signature and age of Telegram `initData`, then checks the same access policy as the bot: any authenticated Telegram account in public mode, or allowlisted accounts in private mode. Forged, stale, future-dated, or duplicate-field login data are rejected. There is no demo-user fallback, client-supplied trusted user ID, API token in frontend code, or cookie login. The public `/healthz` endpoint contains no personal data; curriculum/progress/session API routes require authentication. API responses are not cached, per-user requests are limited, and answer keys are withheld before submission.

The Telegram SDK loads from `telegram.org`; pinned KaTeX 0.16.11 assets/fonts load from jsDelivr. Those hosts receive normal asset requests; study API data stays on your service. Math rendering disables trusted HTML features and uses text fallback when the renderer is unavailable. User authorization expires after one hour; close and reopen the Mini App to refresh it. Web session state expires after two idle hours and resets on deployment; saved answers persist.

### HTTPS hosting

The `web` service listens on port 8080 and binds the host port to **127.0.0.1 only**. Publish it through a reverse proxy or Cloudflare Tunnel with HTTPS. Use `http://web:8080` as the origin for a tunnel on the same Compose network, or `http://127.0.0.1:8080` for a host-based proxy. The bot and web service share the same named SQLite data volume; only `bot` polls Telegram.

For a temporary live preview:

```sh
docker compose --profile preview up -d --build
docker compose logs --tail=100 preview
```

The optional `preview` service uses a Cloudflare Quick Tunnel. Its `trycloudflare.com` address is public HTTPS but **not a permanent production address**: it can change when the tunnel restarts and has no availability guarantee. Set `MINI_APP_URL` to the emitted address, then recreate `bot`. For reliable production use, configure a permanent hostname/tunnel route once, set that stable URL, and stop the preview service. Do not share Cloudflare credentials or bot tokens in chat.

### Finding your Mini App address

Run these commands on the server, from the project directory:

```sh
cd /home/sofiia/workspace/QuantumMechanics-FU
docker compose --profile preview up -d --build
docker compose logs --tail=100 preview
```

Copy the **actual `https://….trycloudflare.com` URL printed in the logs**. Do not use `your-current-address.trycloudflare.com`: that is an example, not a working hostname. Edit the server's `.env` with `nano .env`, set `MINI_APP_URL` to the actual URL, then apply it:

```sh
docker compose up -d --force-recreate bot web
```

Open the bot in Telegram and send `/app` or `/start`. If Docker says “no configuration file provided,” you are not in the directory containing `compose.yaml`, or the updated project has not been deployed there. A temporary tunnel can change its address after restart; use a permanent HTTPS hostname for long-term hosting. Local edits are not automatically deployed to the server.

## Setup

Requirements: Python **3.11+**, a Telegram bot created through **@BotFather**, numeric Telegram user IDs for permitted accounts, and internet access.

From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

Create a local `.env` file with these settings, replacing the illustrative token and IDs with your private values:

```dotenv
TELEGRAM_BOT_TOKEN=replace_with_private_bot_token
PUBLIC_ACCESS=true
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321
DATABASE_PATH=data/quantum_tutor.db
CURRICULUM_PATH=curriculum
TZ=Europe/Berlin
REMINDER_TIMES=05:30,20:00
# Optional confirmed exam date, YYYY-MM-DD; leave blank until known:
EXAM_DATE=
# Optional until the HTTPS Mini App address is configured:
MINI_APP_URL=
```

- `PUBLIC_ACCESS=true` allows any Telegram user to study in a private chat with the bot and open the authenticated Mini App. Telegram signature checks and separate per-account progress remain mandatory; this does not enable anonymous browser access. Set `PUBLIC_ACCESS=false` to restore allowlist-only access. Only `true` and `false` are accepted.
- Public users are not automatically subscribed to reminders. Configured `TELEGRAM_ALLOWED_USER_IDS` remain the reminder recipients; this list may be empty in public mode.
- `TELEGRAM_ALLOWED_USER_IDS` accepts comma-separated numeric IDs. Each allowed account has its own progress, review history, and reminders. The legacy singular `TELEGRAM_ALLOWED_USER_ID` is also accepted when the plural setting is absent.
- `REMINDER_TIMES` accepts comma-separated 24-hour times in the configured timezone.
- `EXAM_DATE` optionally adds a days-until-exam countdown to reminders, calculated in `TZ`. On the date it says “Exam today”; after the date the countdown is omitted. Leave blank until the exam date is confirmed.
- Keep `DATABASE_PATH` under `data/` for Docker persistence with the supplied Compose configuration.
- Never put tokens in commits, chats, screenshots, or logs. Revoke an exposed token through @BotFather and replace it.

### Local development: one poller per token

**The deployed server already polls Telegram. Do not run a local bot with the same token while the server is active.** Use a separate development bot/token, or deliberately stop the server's bot before starting locally. Only one polling process may use a token at a time.

With a separate token, or after stopping the existing poller:

```sh
. .venv/bin/activate
quantum-tutor
```

Open the bot in Telegram and send `/start`. A local process stops serving when the computer sleeps, loses connectivity, or the process exits. Local SQLite data is separate from the deployed Docker volume unless explicitly migrated.

## Server deployment and persistent data

The Docker deployment is on **`ssh.sofiia.dev`**, with repository workspace **`/home/sofiia/workspace/QuantumMechanics-FU`**. Use authorized SSH access and run the following from that workspace; credentials and tokens must remain outside this guide and version control.

```sh
# Build/deploy, or rebuild after updates
docker compose up -d --build

# Inspect status and recent logs
docker compose ps
docker compose logs --tail=100 bot

# Stop the server poller before using its token locally
docker compose down
```

The `bot` and `web` services read `.env`, use `restart: unless-stopped`, and mount the named **`quantum-tutor-data`** volume at `/app/data`. With `DATABASE_PATH=data/quantum_tutor.db`, review history survives container replacement and ordinary `docker compose down` / `up` cycles. **Do not use `docker compose down -v` unless you intend to delete persisted data.**

Back up SQLite consistently before deployments or migrations and protect database and `.env` permissions. A rebuild does not restore an in-memory study queue, but saved progress and review schedules remain. Continuous reminders require an always-on host and Docker service; a sleeping development laptop is not a substitute.

## Development and adding content

Run the existing automated suite from the repository root:

```sh
. .venv/bin/activate
pytest
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for design details. The main code areas are:

```text
src/quantum_tutor/
├── application/       Study workflows and exercise generation
├── domain/            Models, study sets, and spaced-repetition rules
├── infrastructure/    JSON curriculum and SQLite persistence
├── presentation/      Telegram handlers and keyboards
├── config.py          Environment settings
├── scheduler.py       Reminder jobs
├── web/               Signed Telegram authentication, HTTP API, and Mini App static files
└── main.py            Bot startup and application composition
curriculum/            Active topic JSON, source index, staged imports
tests/                 Automated tests
```

Add active material to the appropriate **`curriculum/topic_N.json`**, where `N` is the topic number, not a duplicate legacy catalog. Preserve stable, globally unique card IDs because saved history refers to them. Keep equations, meanings, symbols, assumptions, and usage conditions together; retain provenance and explicitly flag source-dependent claims. Do not promote staged image records to active exercises without suitable content and display support.

Distinguish official headings from original practice, check mathematical correctness and notation, and never claim examination coverage without instructor confirmation. Do not redistribute full lecture scripts or exercise sheets without permission.

Typed answers, derivation practice, unfamiliar-problem application, timed tests/exams, and skill-specific mastery are **future directions**, not current features. Multiple-choice completion alone must not be represented as mastery of those skills.

## Attribution and privacy

The project borrows general active-recall and spaced-repetition learning patterns, not Quizlet's proprietary algorithms. Course headings and supplied references are attributed to their sources above; imported material retains its source metadata and caveats.

Access is restricted to configured Telegram user IDs. Learning history is stored in SQLite on the machine running the bot; Telegram processes messages sent through it. Avoid submitting sensitive personal information. Keep `.env`, databases, virtual environments, and logs out of version control, restrict their file permissions, and protect backups. Do not assume a user-facing history export/delete command exists.
