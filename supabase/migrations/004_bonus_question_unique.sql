-- 004_bonus_question_unique.sql
-- Adds unique constraint on bonus_question_defs.question_text so the loader can upsert idempotently.
alter table bonus_question_defs add constraint bonus_question_defs_text_unique unique (question_text);