"""Bonus Questions — pre-tournament multiple-choice predictions."""
import streamlit as st

from src.auth import get_current_user
from src.predictions import (
    is_locked,
    load_bonus_answers,
    load_bonus_questions,
    save_bonus_answers,
)

UNANSWERED_SENTINEL = "— select an answer —"

user = get_current_user()

st.title("❓ Bonus Questions")
st.caption(
    "Answer every question for **2 pts** each. All questions must be answered before saving. "
    "Locked at tournament start — get your picks in early."
)

locked = is_locked("bonus")
if locked:
    st.warning("🔒 Bonus questions are locked — shown read-only.")

# ── Load data ──────────────────────────────────────────────────────────────────
questions = load_bonus_questions()
saved: dict[int, str] = load_bonus_answers(user["id"])

if not questions:
    st.info("No bonus questions have been seeded yet.")
    st.stop()

# ── Render questions ───────────────────────────────────────────────────────────
selections: dict[int, str | None] = {}

for i, q in enumerate(questions):
    qid: int = q["id"]
    options: list[str] = q["valid_options"]
    saved_answer = saved.get(qid)

    st.markdown(f"**Q{i + 1}. {q['question_text']}**")

    if locked:
        # Read-only: show the saved answer as plain text
        if saved_answer:
            st.markdown(f"Your answer: **{saved_answer}**")
        else:
            st.markdown("_No answer recorded._")
        selections[qid] = saved_answer
    else:
        display_options = [UNANSWERED_SENTINEL] + options
        current_index = (
            display_options.index(saved_answer)
            if saved_answer and saved_answer in display_options
            else 0
        )
        chosen = st.radio(
            label=f"q_{qid}",
            options=display_options,
            index=current_index,
            key=f"bonus_{qid}",
            label_visibility="collapsed",
        )
        selections[qid] = chosen if chosen != UNANSWERED_SENTINEL else None

    st.divider()

# ── Save ───────────────────────────────────────────────────────────────────────
if not locked:
    unanswered = [
        f"Q{i + 1}"
        for i, q in enumerate(questions)
        if selections.get(q["id"]) is None
    ]

    if unanswered:
        st.warning(f"Please answer all questions before saving. Missing: {', '.join(unanswered)}")

    save_disabled = bool(unanswered)
    if st.button("💾 Save Answers", type="primary", use_container_width=True, disabled=save_disabled):
        answers_to_save = {qid: opt for qid, opt in selections.items() if opt is not None}
        try:
            save_bonus_answers(user["id"], answers_to_save)
            st.success(f"✅ Answers saved — {len(answers_to_save)} of {len(questions)} questions answered.")
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't save: {e}")