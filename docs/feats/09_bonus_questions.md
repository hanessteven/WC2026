# 09 — Bonus Questions

**Status:** 🔲 Not started
**Depends on:** 03, 04, 05

## Goal
Render the seeded multiple-choice bonus questions and capture each user's answer.

## Requirements
- Render each question from `bonus_question_defs` with its valid options.
- User selects exactly one option per question.
- **Validate** answers against the question's option list before saving.
- Save & edit until the `bonus` lock (feature 10); read-only when locked.

## Scoring impact (see [../bonus_questions.md](../bonus_questions.md) & [../scoring_rules.md](../scoring_rules.md))
- 2 points per correct answer.
- **Tie handling:** when a question's outcome ties, the admin records *multiple* correct options, and **all** users who picked *any* of the correct options receive full points.

## Acceptance criteria
- Answers persist, validate against options, and lock correctly.
- Scoring honors multiple-correct (tie) answers — covered by tests in feature 12.

## TODO
- Final question wording and options (cross-ref `bonus_questions.md`).