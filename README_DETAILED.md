# CARES — Detailed README

This document explains how the CARES MVP works: scoring logic, formulas, pillars, thresholds, red-flag rules, AI integration (OpenRouter), request/response schema, file locations, and how to run the app locally.

## Overview

CARES is an assessment tool that uses a short 20-question multiple-choice survey to evaluate a child's digital-safety and AI-readiness across several pillars. The backend computes deterministic scores and then calls an LLM (OpenRouter model) to produce a human-friendly, structured professional report. The server stores the raw model response and a synthesized, validated report to guarantee a complete output even when the model returns truncated or invalid JSON.

Key components:
- Backend: FastAPI (`server/main.py`)
- Frontend: React (Vite) in `client/`
- Storage: flat JSON file `server/reports.json` (append-only list of assessments)
- AI model: OpenRouter model `tngtech/deepseek-r1t2-chimera:free` (called from `server/main.py`)

## Files of interest

- `server/main.py` — API endpoints, scoring, AI integration, parsing, and synthesizer fallback.
- `server/questions.py` — list of 20 questions, per-question `pillar` and `weight`, `OPTIONS` mapping, and `PILLAR_WEIGHTS`.
- `server/reports.json` — stored assessment objects. Each entry includes raw model response (`ai_raw`), parsed model JSON if parseable (`ai_parsed`), and guaranteed structured output (`ai_structured`).
- `client/src/pages/Assessment.jsx` and `client/src/pages/Results.jsx` — frontend form & result rendering.

## Terms & definitions

- Option score: Each answer option maps to an integer score in `OPTIONS` (0..3). Higher is better.
- Question weight: Each question has a `weight` multiplier indicating its importance within its pillar.
- Pillar: A domain like `E` (ethics/behavior), `DH` (digital hygiene), `CC` (critical cognition), `TE` (technology literacy), `SG` (supervision). `PILLAR_WEIGHTS` maps pillars to percent weights that together sum to 100.
- Pillar percentage: A 0–100 number representing normalized performance within that pillar.
- Overall score: A weighted sum of pillar percentages using `PILLAR_WEIGHTS`. Range 0–100.
- Category: One of `NOT READY`, `TRANSITION`, `AI-READY` determined by overall score and red flags.
- Red flags: Specific question-level alerts that cause immediate concern.
- ai_raw / ai_parsed / ai_structured:
  - `ai_raw` — the full JSON response returned by the OpenRouter API saved verbatim.
  - `ai_parsed` — the parsed JSON parsed from the model's textual response when possible (or `{"narrative": <text>}` fallback).
  - `ai_structured` — final guaranteed structured report produced by merging parsed model output with a deterministic synthesizer; always present and complete.

## Scoring formula (exact)

1. Per-question score mapping (from `server/questions.py` OPTIONS):
   - A -> 0
   - B -> 1
   - C -> 2
   - D -> 3

2. For each question:
   - Multiply the chosen option score `s` by the question `weight`.
   - Example: if `s=2` and `weight=1.5`, contribution = 3.0

3. For each pillar p:
   - Sum `s * weight` across all questions in that pillar -> numerator
   - Sum `3 * weight` across those questions -> maximum possible for that pillar (because D=3 is max) -> denominator
   - Pillar percentage = (numerator / denominator) * 100
   - The code computes and rounds each pillar percentage to 1 decimal.

   Formula: pillar_pct_p = round((sum_q(s_q * w_q) / sum_q(3 * w_q)) * 100, 1)

4. Overall score:
   - overall = sum_p (pillar_pct_p * PILLAR_WEIGHTS[p] / 100)
   - Rounded to 1 decimal.

5. Category rules (deterministic):
   - If overall < 40 OR any red flag exists -> category = `NOT READY`
   - Else if overall >= 70 -> category = `AI-READY`
   - Else -> category = `TRANSITION`

6. Red-flag rules (implemented exact checks):
   - Q1 score 0 -> `Q1_cheating_high`
   - Q4 score 0 -> `Q4_shares_passwords`
   - Q7 score 0 -> `Q7_never_asks_before_sharing`
   - Q9 score 0 -> `Q9_posts_personal_info_often`
   - Q11 score 0 -> `Q11_follow_risky_instructions`
   - Q14 score 0 -> `Q14_share_private_photo`
   - Q20 score 0 -> `Q20_passes_ai_as_own`
   - Combined severe privacy: if Q7 and Q9 both score 0 -> `combined_privacy_severe`
   - Soft flag: if 3 or more zero answers across all questions -> `soft_many_zero_answers`

7. Risks: grouped risk scores 0–100 computed as:
   - For a group of question ids, we compute average of the per-question option scores (0..3), divide by 3 (to normalize), multiply by 100, and then invert as a risk percent (i.e., risk = 100 - normalized_score_percent).
   - Example risk groups used: `cheating_risk`, `privacy_risk`, `impulse_hallucination_risk`, `supervision_gap`.

## Example small calculation

Suppose one question in pillar `E` has weight 2 and the user chose option `D` (score 3):
- Contribution: 3 * 2 = 6
- Max for that question: 3 * 2 = 6
- Pillar percentage contribution from that question = 6 / 6 = 1.0 -> 100%

If that pillar has only that question, pillar_pct = 100. Overall score is then computed using `PILLAR_WEIGHTS`.

## Categories & what they mean (short)

- NOT READY: Immediate supervisory or behavioral intervention recommended (overall <40 or presence of red flags).
- TRANSITION: Some skills exist; targeted guidance and family rules are recommended.
- AI-READY: The child demonstrates good digital habits and can safely increase independence with periodic monitoring.

## AI integration & how model output is used

- Model call happens in `server/call_openrouter()` using OpenRouter's Chat Completions endpoint.
- Model used: `tngtech/deepseek-r1t2-chimera:free` with a low temperature (0.1) to encourage deterministic output and `max_tokens=1000`.
- The server sends a strong system prompt requesting JSON-only output and includes an explicit example JSON structure.

### Parsing strategy

- The server expects the model to return JSON, but in practice models sometimes include extra text or return truncated output. To handle this robustly, the server uses `try_parse_ai_text_to_json(text)` which:
  1. Looks for a JSON object inside markdown fences (```json { ... } ```).
  2. If not found, searches for the first `{ ... }` substring and attempts to parse it.
  3. If parsing fails, it attempts to parse the entire text as JSON.
  4. If no JSON is parseable, it stores the full text under `ai_parsed = { "narrative": <text> }`.

### Synthesis fallback

- After parsing, the server calls `synthesize_report(parsed, scores, child, answers)` which ensures all expected fields exist (header_summary, professional_paragraph, observations, why_this_matters, improvement_plan with `30_days/60_days/90_days`, recommended_family_rules, follow_up, monitor_confidence, counselor_notes, suggested_resources, score, category).
- The synthesizer uses the deterministic `scores` and simple rules to fill any missing fields. This guarantees the frontend always receives a full, professional structured report even when the model output is invalid or truncated.

## API Endpoints

1. POST /assess
   - Request body: JSON with `child_name`, `child_age`, `parent_contact`, and `answers` array of `{ qid, option }`.
   - Example request body:

```json
{
  "child_name": "Alex",
  "child_age": 12,
  "parent_contact": "parent@example.org",
  "answers": [
    {"qid": 1, "option": "C"},
    {"qid": 2, "option": "B"},
    ... (20 total) ...
  ]
}
```

   - Response: a structured object that includes deterministic `score`, `category`, `header_summary`, `professional_paragraph`, `observations`, `improvement_plan`, `recommended_family_rules`, `follow_up`, `monitor_confidence`, `counselor_notes`, `suggested_resources`, `raw_ai`, `pillars`, `risks`, and `red_flags`.

   - Side effect: a saved report object is appended to `server/reports.json` with fields: `id`, `timestamp`, `child`, `answers`, `scores`, `ai_raw`, `ai_parsed`, `ai_structured`.

2. GET /reports
   - Returns list of saved reports' metadata (id, timestamp, child name, scores)

3. GET /reports/{report_id}
   - Returns the full saved report object from `server/reports.json`.

## Example response skeleton (front-end receives)

```json
{
  "score": 56.5,
  "category": "TRANSITION",
  "header_summary": "Alex is assessed as TRANSITION with a score of 56.5.",
  "professional_paragraph": "Alex demonstrates ... (empathetic paragraph)",
  "observations": ["Obs 1", "Obs 2", "Obs 3"],
  "why_this_matters": "One-sentence risk description.",
  "improvement_plan": {"30_days": ["..."], "60_days": ["..."], "90_days": ["..."]},
  "recommended_family_rules": ["Rule 1", "Rule 2", "Rule 3", "Rule 4", "Rule 5"],
  "follow_up": {"next_assessment_date": "2025-12-01", "consultant_recommended": "Recommended"},
  "monitor_confidence": 65,
  "counselor_notes": "Counselor note...",
  "suggested_resources": [{"title":"Resource","url":"https://..."}],
  "raw_ai": { ... full OpenRouter response ... },
  "pillars": { "E": 56.7, "DH": 62.5, "CC": 48.3, "TE": 70.0, "SG": 55.0 },
  "risks": { "cheating_risk": 66, "privacy_risk": 55, "impulse_hallucination_risk": 40, "supervision_gap": 72 },
  "red_flags": ["Q4_shares_passwords"]
}
```

> Note: `raw_ai` contains the full response from OpenRouter (the server preserves it verbatim). The structured fields are always present thanks to the synthesizer.

## How reports are saved (`server/reports.json`)

Each saved report is appended to the list stored in `server/reports.json`. Example saved object keys:
- `id` (millisecond timestamp)
- `timestamp` (epoch float)
- `child` (the `AssessmentIn` object)
- `answers` (array)
- `scores` (deterministic scoring output)
- `ai_raw` (the raw OpenRouter response)
- `ai_parsed` (attempted parsed JSON or `{"narrative": ...}`)
- `ai_structured` (final synthesized JSON used to respond to frontend)

This design allows debugging/troubleshooting of the model output while guaranteeing a stable user experience.

## How to run locally (PowerShell on Windows)

1. Backend

Open a PowerShell window, change directory to `server`, create a virtualenv, and install dependencies (if `requirements.txt` exists):

```powershell
cd C:\Users\hardi\OneDrive\Desktop\idk\server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set environment variables

Create a `.env` file in `server` (or set the `OPENROUTER_API_KEY` environment variable) with:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

3. Start the backend (development mode with reload):

```powershell
# from server directory
python main.py
# or explicitly
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

4. Frontend

Open another PowerShell in the `client` directory and run:

```powershell
cd C:\Users\hardi\OneDrive\Desktop\idk\client
npm install
npm run dev
```

The app expects the backend at `http://localhost:8000`. The frontend Axios client is configured to call that by default.

## Environment & secrets

- The only secret required is `OPENROUTER_API_KEY` (put in `server/.env`).
- The backend uses `python-dotenv` (via `load_dotenv()` in `server/main.py`) to pick up `.env`.

## Troubleshooting

- 500 on `/assess`: check `OPENROUTER_API_KEY` is set and valid.
- Long model calls / timeouts: model requests set a 60s timeout in the server. Increase client timeout if needed.
- Truncated model JSON: the server attempts to parse fenced JSON and fallbacks to a synthesizer. Inspect `server/reports.json` to see `ai_raw` and `ai_parsed` for debugging.

## Important design notes and rationale

- Deterministic scoring keeps the critical safety assessment reproducible and auditable. The AI is used to add human-friendly narrative, observations, and tailored step-wise improvement plans — but it does not drive the numeric result.
- The synthesizer fallback ensures the product never returns empty or confusing fields to caregivers; it produces empathetic and actionable text when the model output is missing or malformed.
- The architecture favors simplicity for an MVP: JSON file persistence and a single backend controller that both computes scores and orchestrates AI calls.

## Next steps (suggestions)

- Add schema validation for model JSON (e.g., JSON Schema) and fail-safe tests.
- Implement proper DB persistence instead of `reports.json` for real usage and to support multi-user auth.
- Implement PDF export using a server-side renderer (we have a PDF stub in the UI currently).
- Add unit tests for `compute_scores()` and `synthesize_report()`.

---

If you'd like, I can:
- Add an example POST payload + a concrete saved `reports.json` entry showing `ai_raw`, `ai_parsed`, and `ai_structured` for a single run.
- Generate unit tests that assert the scoring formulas and the red-flag rules.

Which of these would you like next?