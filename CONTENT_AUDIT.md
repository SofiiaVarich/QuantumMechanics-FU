# Curriculum and answer audit

## Scope and limits

The initial audit inspected 476 imported concept cards and 12 standalone formula records for structural consistency and mathematical concerns. The expanded Chapter 5 workbook adds 24 cards, and the Chapter 6 script-only workbook adds another 38, and the deduplicated Chapter 2 LaTeX workbooks add five more, bringing the current concept total to 543. Its 83 learning rows and 29 BOX references have been checked for structure and source mapping; workbook verification notes remain supplied claims rather than independent PDF checks. Automated tests generate exercises for every card in Learn, Laws, and (where eligible) Formulas modes. This is not certification against the original lecture PDFs or an official examination syllabus. Imported source references remain user-supplied.

## Implemented corrections and clarifications

Original edited fields are retained under `content_corrections` in the corresponding topic JSON.

- **C8-012:** corrected the linear Zeeman sign to agree with the signed electron charge used by the surrounding cards.
- **C8-029–030:** positive cyclotron frequency and Landau spacing use the chapter's Gaussian-unit convention, including `1/c`; distinguished transverse orbital levels from spin and longitudinal energy.
- **C10-036:** restored the squared elementary charge in the Gaussian-unit nuclear Coulomb potential.
- **C10-011, C10-013–016:** made the interaction energy scale and initial environment explicit; distinguished the pure final plus state from the maximally mixed final computational state.
- **C10-022–023:** explicitly required complete positivity, trace preservation, and Kraus normalization.
- **C10-028, C10-030:** restored `1/ℏ` for an energy-valued Hamiltonian and gave a dimensionally consistent Lindblad generator.
- **C9-025:** restricted the stated contradiction to deterministic ±1 assignments rather than arbitrary stochastic conditional means.
- **EXP-041:** restricted the threshold claim to single-photon photoemission.
- **EXP-029:** identified the Balmer series by transitions to n=2, not by an exclusively visible spectrum.
- **EXP-008, EXP-016, EXP-020, EXP-034:** stated spectral-density, scattering, nonrelativistic acceleration, and potential-energy assumptions.
- **C10-052:** distinguished an exact zero-hopping product state from a finite-hopping approximation.

## Items that require the original PDFs

Twelve cards are marked under `content_review_required`. Their answer feedback explicitly displays the source-check warning.

- **C5-053:** associated Laguerre argument/scaling convention, Eq. 5.102.
- **C6-023, C6-025:** anharmonic-oscillator coefficients and numerical example depend on the exact Hamiltonian and unit conventions.
- **C6-044:** a special bound must not be mistaken for the general definition of relative boundedness.
- **C7-017–022:** computational-basis spin labels depend on the script's Pauli-matrix/basis ordering convention.
- **C10-063:** perturbation coefficient versus complete order-ψ² contribution.
- **C10-068:** occupation-sector restrictions and the special vacuum boundary.

These expressions were not silently replaced with a guessed source convention.

## Multiple-choice safeguards

- Correct answers are generated from the same record as the prompt.
- Duplicate and normalized-identical answers are excluded.
- Cards with identical concept names, known overlapping concepts, contained answer strings, and obvious near-identical definitions are excluded from one another's wrong choices.
- Related-topic distractors are preferred where possible.
- Formula mode uses actual equation/key-rule fields rather than generic descriptions.
- Wrong answers and Don't know persist in the account's Review queue.

The filters are conservative heuristics, **not a proof that every possible distractor is semantically false**. Further source review and curated distractors remain valuable. A correct recognition answer does not establish independent recall, derivation ability, or exam readiness.
