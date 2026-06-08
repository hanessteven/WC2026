# Data Models (Pydantic)

## Overview
All data structures are defined using Pydantic for type safety and validation. These models are used throughout the application to ensure data consistency.

TODO: Define models.py with the following Pydantic classes:

### UserProfile
TODO: Fields - id (UUID), email (str), display_name (str), created_at (datetime)

### GroupStagePrediction
TODO: Fields - group_letter (str), predicted_order (list[str]), represents user's ranking of 4 teams in a group

### BracketPrediction
TODO: Fields - match_id (str), predicted_winner (str), stage (enum: R32, R16, QF, SF, F)

### GoldenBootSelection
TODO: Fields - player_name (str), cost (int), is_predicted (bool)

### BonusAnswer
TODO: Fields - question_id (int), answer (str), must validate against valid_options

### UserPredictions
TODO: Fields - user_id (UUID), group_stage (list[GroupStagePrediction]), bracket (list[BracketPrediction]), golden_boot (list[GoldenBootSelection]), bonus_answers (list[BonusAnswer]), submitted_at (datetime)

### TournamentResults
TODO: Fields - match_id (str), winner (str), loser (str), is_penalty (bool), goals_scored (int), results_date (datetime)

### ScoringBreakdown
TODO: Fields - user_id (UUID), group_stage_points (int), bracket_points (int), golden_boot_points (int), bonus_points (int), total_points (int), last_updated (datetime)

## Validation Rules
TODO: Document custom validators (e.g., ensure group predictions are unique teams, ensure golden boot selections fit within $100 budget)