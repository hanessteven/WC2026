# 2026 World Cup Prediction Bracket

## Project Overview
This application is a specialized platform designed for group-based competition during the 2026 World Cup. It moves away from the traditional, winner-take-all bracket formats, instead implementing a balanced scoring system that rewards deep tournament knowledge and consistent predictive accuracy across all stages.

The platform provides a streamlined UI for users to submit their predictions—including group stage rankings, third-place qualifiers, knockout bracket progression, and a "Salary Cap" style Golden Boot draft.

## Business & Scoring Logic

The platform is driven by a custom Python-based scoring engine that ensures transparency and fairness. Our scoring is built on a **Fibonacci-weighted system** designed to keep participants competitive throughout the entire tournament, rather than letting a single "correct champion" pick dominate the leaderboard.

### 1. Scoring Methodology
Points are awarded progressively, emphasizing accuracy in later rounds:

| Stage / Category | Point Value |
| :--- | :--- |
| **Group Stage** | |
| Correct Qualifier (Top 2) | 1 pt per team |
| Correct Group Position (Bonus) | 1 pt per team |
| Correct 3rd Place Advancer | 2 pts per team |
| **Knockout Bracket** | |
| Round of 32 Winner | 1 pt |
| Round of 16 Winner | 2 pts |
| Quarterfinal Winner | 3 pts |
| Semifinal Winner | 5 pts |
| Final Winner | 8 pts |
| Tournament Champion | 13 pts |
| **Draft & Bonuses** | |
| Golden Boot (Per Goal) | 1 pt |
| Bonus Question Correct | 2 pts |

### 2. The Golden Boot "Salary Cap" Draft
To make the Golden Boot race more than just picking the tournament's top scorer, we utilize a budget-constrained selection model. 
* Each user is provided with a fixed **$100 virtual budget**.
* Players are tiered by cost based on their expected tournament output (e.g., Mbappe @ $30, Pulisic @ $10, sleepers @ $5).
* Users must strategically build a roster of multiple players, balancing high-cost stars against value picks.

### 3. Bonus Challenges
To maintain engagement throughout the tournament, we include multi-choice bonus questions that carry the weight of a Round of 16 match. These cover tournament-wide variables such as:
* Which host nation will advance the farthest?
* The volume of penalty-decided matches in the Round of 32.
* Confederation performance and group-stage scoring leaders.

## Technical Architecture
* **Frontend:** Streamlit for a responsive, clean, and interactive user experience.
* **Backend Logic:** Pure Python engine utilizing Pydantic for data validation.
* **Database:** PostgreSQL (via Supabase) for secure, scalable, and relational data management.
* **Deployment:** Hosted on Streamlit Community Cloud for seamless browser-based access.

---
*Built for individual use and competitive groups. Designed for accuracy, fairness, and fun.*