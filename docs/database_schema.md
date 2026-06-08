# Detailed Database Schema

## Tables

### users
TODO: Define columns - id (UUID, PK), email (string, unique), display_name (string), created_at (timestamp)

### predictions
TODO: Define columns - id (UUID, PK), user_id (FK to users), group_stage_json (JSONB), bracket_json (JSONB), golden_boot_json (JSONB), submitted_at (timestamp), updated_at (timestamp)

### tournament_results
TODO: Define columns - match_id (string, PK), match_name (string), stage (enum), winner (string), loser (string), is_penalty_win (boolean), goals_by_winner (int), updated_at (timestamp)

### bonus_answers
TODO: Define columns - id (UUID, PK), user_id (FK), question_id (int), answer (string), submitted_at (timestamp)

### bonus_question_definitions
TODO: Define columns - id (int, PK), question_text (string), valid_options (JSONB array), point_value (int)

## Indexes & Constraints
TODO: Document any indexes needed for performance (e.g., user_id on predictions for fast lookups during score calculation)

## Row-Level Security (RLS) Policies
TODO: Define RLS policies so users can only see/modify their own predictions

## Relationships Diagram
TODO: Add visual or text representation of foreign key relationships