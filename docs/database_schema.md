# Detailed Database Schema

Migration files: `supabase/migrations/001_schema.sql`, `002_rls.sql`, ..., `007_result_finalization_locks.sql`

## Tables

### profiles
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | FK → auth.users(id), cascades on delete |
| email | text | not null |
| display_name | text | nullable; set after first login |
| created_at | timestamptz | default now() |

Auto-created by trigger `on_auth_user_created` when a user signs up.

### allowed_emails
| Column | Type | Notes |
|--------|------|-------|
| email | text PK | whitelist for magic-link sign-in |

### seed_groups
| Column | Type | Notes |
|--------|------|-------|
| letter | char(1) PK | 'A'–'L' |

### seed_teams
| Column | Type | Notes |
|--------|------|-------|
| id | serial PK | |
| name | text unique | not null |
| group_letter | char(1) | FK → seed_groups(letter) |
| flag_emoji | text | optional |

### seed_players
| Column | Type | Notes |
|--------|------|-------|
| id | serial PK | |
| name | text | not null |
| team_name | text | FK → seed_teams(name) |
| tier | int | 1 = most expensive |
| cost | int | virtual dollars |

### bonus_question_defs
| Column | Type | Notes |
|--------|------|-------|
| id | serial PK | |
| question_text | text | not null |
| valid_options | jsonb | array of strings |
| correct_options | jsonb | null until admin enters results; array supports ties |
| point_value | int | default 2 |

### lock_state
| Column | Type | Notes |
|--------|------|-------|
| category | text PK | `group_stage`, `champion`, `golden_boot`, `bonus`, `R32`, `R16`, `QF`, `SF`, `F` |
| is_locked | bool | default false |
| locked_at | timestamptz | nullable |
| locked_by | text | admin email, nullable |

Pre-seeded with all 9 categories, all unlocked.

### real_bracket
| Column | Type | Notes |
|--------|------|-------|
| id | serial PK | |
| round | text | `R32`, `R16`, `QF`, `SF`, `F` |
| slot | int | 1-based slot within the round |
| team_a | text | not null |
| team_b | text | not null |
| winner | text | null until admin enters result |
| is_penalty | bool | default false |

Unique constraint on (round, slot).

### results_group_stage
| Column | Type | Notes |
|--------|------|-------|
| group_letter | char(1) PK | FK → seed_groups(letter) |
| final_ranking | jsonb | `[1st, 2nd, 3rd, 4th]` team name array |
| third_place_advances | bool | true if this group's 3rd-placer is one of the 8 advancers |
| updated_at | timestamptz | |

### results_player_goals
| Column | Type | Notes |
|--------|------|-------|
| player_id | int PK | FK → seed_players(id) |
| goals_scored | int | default 0 |
| updated_at | timestamptz | |

### results_group_lock
| Column | Type | Notes |
|--------|------|-------|
| group_letter | char(1) PK | 'A'–'L' |
| is_locked | bool | default false; admin toggles to finalize group results |

Pre-seeded with all 12 groups, all unlocked. Prevents accidental edits to group results after they're entered.

### results_golden_boot_lock
| Column | Type | Notes |
|--------|------|-------|
| id | int PK | always 1 (CHECK constraint) |
| is_locked | bool | default false; admin toggles to finalize golden boot results |

Single-row table. Pre-seeded unlocked. Prevents accidental edits to golden boot goals after the top scorer is finalized.

### predictions_group_stage
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| user_id | uuid | FK → profiles(id), cascade |
| group_letter | char(1) | FK → seed_groups(letter) |
| predicted_ranking | jsonb | `[1st, 2nd, 3rd, 4th]` team name array |
| third_place_advances | bool | user predicts this group's 3rd-placer advances |
| updated_at | timestamptz | |

Unique on (user_id, group_letter). Exactly 8 of 12 `third_place_advances = true` enforced in app logic.

### predictions_champion
| Column | Type | Notes |
|--------|------|-------|
| user_id | uuid PK | FK → profiles(id), cascade |
| champion | text | not null |
| dark_horse | text | optional |
| updated_at | timestamptz | |

### predictions_bracket
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid | FK → profiles(id), cascade |
| matchup_id | int | FK → real_bracket(id) |
| predicted_winner | text | not null |
| updated_at | timestamptz | |

Unique on (user_id, matchup_id).

### predictions_golden_boot
| Column | Type | Notes |
|--------|------|-------|
| user_id | uuid | FK → profiles(id), cascade |
| player_id | int | FK → seed_players(id) |

PK on (user_id, player_id). Budget (≤ $100) enforced in app logic.

### predictions_bonus
| Column | Type | Notes |
|--------|------|-------|
| user_id | uuid | FK → profiles(id), cascade |
| question_id | int | FK → bonus_question_defs(id) |
| chosen_option | text | must be in valid_options (app validation) |
| updated_at | timestamptz | |

PK on (user_id, question_id).

### scores
| Column | Type | Notes |
|--------|------|-------|
| user_id | uuid PK | FK → profiles(id), cascade |
| group_stage_pts | int | default 0 |
| bracket_pts | int | default 0 |
| champion_pts | int | default 0 |
| golden_boot_pts | int | default 0 |
| bonus_pts | int | default 0 |
| total_pts | int | default 0 |
| calculated_at | timestamptz | |

Written only by scoring engine via service-role key.

## Indexes
| Table | Column(s) | Reason |
|-------|-----------|--------|
| seed_teams | group_letter | group roster lookups |
| predictions_group_stage | user_id | scoring engine per-user fetch |
| predictions_bracket | user_id | scoring engine per-user fetch |
| predictions_bracket | matchup_id | find all picks for a matchup |
| predictions_golden_boot | user_id | scoring engine per-user fetch |
| predictions_bonus | user_id | scoring engine per-user fetch |
| scores | total_pts DESC | leaderboard ordering |

## RLS Summary
| Table | Anon-key read | Anon-key write |
|-------|--------------|----------------|
| profiles | all authenticated | own row only |
| allowed_emails | all authenticated | service role only |
| seed_* / bonus_question_defs | all authenticated | service role only |
| lock_state / real_bracket / results_* | all authenticated | service role only |
| predictions_* | own rows only | own rows only |
| scores | all authenticated | service role only |