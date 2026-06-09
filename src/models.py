"""
Data models for the WC2026 Predictor.
Pure Pydantic — no st.* imports allowed in this module.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

# Configurable scoring constants — change here to affect the entire scoring engine.
GOLDEN_BOOT_BUDGET: int = 100
GOLDEN_BOOT_WINNER_PTS: int = 7   # awarded if any drafted player wins the Golden Boot
CHAMPION_PTS: int = 13
DARK_HORSE_PTS: int = 3           # awarded if the dark-horse pick reaches QF or further


class Round(str, Enum):
    R32 = "R32"
    R16 = "R16"
    QF = "QF"
    SF = "SF"
    F = "F"


# ── Reference / seed models ───────────────────────────────────────────────────

class UserProfile(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    created_at: datetime | None = None


class SeedTeam(BaseModel):
    id: int
    name: str
    group_letter: str
    flag_emoji: str | None = None
    is_dark_horse_eligible: bool = True


class SeedPlayer(BaseModel):
    id: int
    name: str
    team_name: str | None = None
    tier: int
    cost: int


class BonusQuestionDef(BaseModel):
    id: int
    question_text: str
    valid_options: list[str]
    correct_options: list[str] | None = None  # None until admin enters results
    point_value: int = 2


class LockStateRow(BaseModel):
    category: str
    is_locked: bool
    locked_at: datetime | None = None
    locked_by: str | None = None


# ── Prediction models ─────────────────────────────────────────────────────────

class GroupStagePrediction(BaseModel):
    """User's ranking of the 4 teams in one group, plus their third-place call."""
    group_letter: str
    predicted_ranking: list[str]       # [1st, 2nd, 3rd, 4th]
    third_place_advances: bool = False  # user predicts this group's 3rd advances

    @field_validator("predicted_ranking")
    @classmethod
    def ranking_has_four_unique_teams(cls, v: list[str]) -> list[str]:
        if len(v) != 4:
            raise ValueError("predicted_ranking must contain exactly 4 teams")
        if len(set(v)) != 4:
            raise ValueError("predicted_ranking must not contain duplicate teams")
        return v


class ChampionPick(BaseModel):
    """Upfront champion + optional dark horse, locked at tournament start."""
    champion: str
    dark_horse: str | None = None  # scores if the team reaches the quarterfinals (top 8)


class RealMatchup(BaseModel):
    """Admin-entered actual matchup for a knockout round."""
    id: int
    round: Round
    slot: int
    team_a: str
    team_b: str
    winner: str | None = None       # None until admin enters result
    is_penalty: bool = False


class RoundPick(BaseModel):
    """User's predicted winner for one real knockout matchup."""
    matchup_id: int
    predicted_winner: str


class GoldenBootSelection(BaseModel):
    """A player the user has drafted in the salary-cap golden boot."""
    player_id: int
    player_name: str
    cost: int


class BonusAnswer(BaseModel):
    """User's answer to one bonus question, validated against valid options."""
    question_id: int
    chosen_option: str
    valid_options: list[str]  # populated from BonusQuestionDef at parse time

    @model_validator(mode="after")
    def option_must_be_valid(self) -> BonusAnswer:
        if self.chosen_option not in self.valid_options:
            raise ValueError(
                f"'{self.chosen_option}' is not a valid option for question "
                f"{self.question_id}. Valid: {self.valid_options}"
            )
        return self


# ── Aggregate prediction model (input to scoring engine) ─────────────────────

class UserPredictions(BaseModel):
    """All predictions for one user — passed to the scoring engine."""
    user_id: UUID
    group_stage: list[GroupStagePrediction] = []
    champion_pick: ChampionPick | None = None
    bracket_picks: list[RoundPick] = []
    golden_boot: list[GoldenBootSelection] = []
    bonus_answers: list[BonusAnswer] = []

    @model_validator(mode="after")
    def third_place_count(self) -> UserPredictions:
        """Exactly 8 of 12 group third-place advances must be True when all groups are submitted."""
        if len(self.group_stage) == 12:
            count = sum(1 for g in self.group_stage if g.third_place_advances)
            if count != 8:
                raise ValueError(
                    f"Exactly 8 third-place advancers must be selected, got {count}"
                )
        return self

    @model_validator(mode="after")
    def golden_boot_within_budget(self) -> UserPredictions:
        total = sum(p.cost for p in self.golden_boot)
        if total > GOLDEN_BOOT_BUDGET:
            raise ValueError(
                f"Golden boot spend ${total} exceeds budget of ${GOLDEN_BOOT_BUDGET}"
            )
        return self


# ── Tournament result models (input to scoring engine) ───────────────────────

class GroupStageResult(BaseModel):
    """Admin-entered actual standings for one group."""
    group_letter: str
    final_ranking: list[str]          # [1st, 2nd, 3rd, 4th]
    third_place_advances: bool = False


class PlayerGoals(BaseModel):
    """Goals scored by one golden boot candidate."""
    player_id: int
    player_name: str
    goals_scored: int


class TournamentResults(BaseModel):
    """
    Aggregate of all admin-entered results — passed to the scoring engine.
    Fields are optional so partial data (mid-tournament) is valid.
    Bonus correct_options: dict of question_id -> list of correct answers
    (list supports ties — multiple correct answers).
    """
    group_stage: list[GroupStageResult] = []
    knockout: list[RealMatchup] = []       # only matchups with winner filled in
    player_goals: list[PlayerGoals] = []
    bonus_correct: dict[int, list[str]] = {}  # question_id -> correct option(s)


# ── Scoring output ────────────────────────────────────────────────────────────

class ScoringBreakdown(BaseModel):
    """Per-category point totals for one user. Output of the scoring engine."""
    user_id: UUID
    group_stage_pts: int = 0
    bracket_pts: int = 0
    champion_pts: int = 0
    golden_boot_pts: int = 0
    bonus_pts: int = 0
    total_pts: int = 0
    calculated_at: datetime | None = None

    @model_validator(mode="after")
    def total_matches_sum(self) -> ScoringBreakdown:
        expected = (
            self.group_stage_pts
            + self.bracket_pts
            + self.champion_pts
            + self.golden_boot_pts
            + self.bonus_pts
        )
        if self.total_pts != expected:
            raise ValueError(
                f"total_pts {self.total_pts} does not match category sum {expected}"
            )
        return self