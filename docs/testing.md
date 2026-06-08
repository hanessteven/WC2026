# Testing Strategy

## Unit Testing
TODO: Framework (pytest), test structure, and where test files live (tests/ directory)

## Scoring Engine Tests
The scoring engine in `src/scoring.py` must be thoroughly tested independently of Streamlit.

### Test Cases for Partial Tournament Data
TODO: Document test scenarios where:
- Only group stage results are available
- Group stage + some bracket matches are complete
- User predictions are scored incrementally as tournament progresses
- Scores update when new results are added (idempotent scoring)

Example test structure:
```python
# TODO: Implement
def test_scoring_with_partial_results():
    # Setup: User predictions for entire tournament
    # Setup: Only R32 results available
    # Assert: Score reflects only R32 points
    # Setup: Add R16 results
    # Assert: Score updates to include R16 points
```

### Test Cases for Bonus Questions with Ties
TODO: Test scenarios where:
- Two host nations tie for advancing furthest (both answers correct)
- Multiple groups tie for highest scoring (all tied answers are correct)
- Edge cases (all teams score equally, no clear winner)

## Integration Tests
TODO: Tests that verify the full flow - user submits predictions → results are added → scores are calculated and returned correctly

## Test Data
TODO: Create fixtures or factory functions for:
- Complete user predictions
- Partial tournament results at various stages
- Edge case tournament scenarios (many penalties, unusual advancement patterns)

## Running Tests
TODO: Command to run entire test suite, specific tests, and coverage reporting