import os
import json
import time
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

from questions import QUESTIONS, OPTIONS, PILLAR_WEIGHTS

load_dotenv()

# read the API key from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPORTS_FILE = os.path.join(os.path.dirname(__file__), "reports.json")

app = FastAPI(title="CARES MVP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Answer(BaseModel):
    qid: int
    option: str


class AssessmentIn(BaseModel):
    child_name: str
    child_age: int
    parent_contact: str
    answers: List[Answer]


def ensure_reports_file():
    if not os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_reports() -> List[Dict[str, Any]]:
    ensure_reports_file()
    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_report(obj: Dict[str, Any]):
    reps = load_reports()
    reps.append(obj)
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reps, f, indent=2)


def compute_scores(answers: List[Dict]) -> Dict[str, Any]:
    # Map qid->choice
    ans_map = {a['qid']: a['option'] for a in answers}

    # Prepare pillar accumulators
    pillar_acc = {p: 0.0 for p in PILLAR_WEIGHTS.keys()}
    pillar_weight_sum = {p: 0.0 for p in PILLAR_WEIGHTS.keys()}
    zero_answers = 0
    red_flags = []

    # helper to get choice score
    score_map = {o['key']: o['score'] for o in OPTIONS}

    for q in QUESTIONS:
        qid = q['id']
        pillar = q['pillar']
        weight = q['weight']
        opt = ans_map.get(qid)
        if opt is None:
            # unanswered -> treat as worst (0)
            s = 0
        else:
            s = score_map.get(opt, 0)
        pillar_acc[pillar] += s * weight
        pillar_weight_sum[pillar] += 3 * weight
        if s == 0:
            zero_answers += 1

        # Red-flag checks (specific question ids)
        if qid == 1 and s == 0:
            red_flags.append("Q1_cheating_high")
        if qid == 4 and s == 0:
            red_flags.append("Q4_shares_passwords")
        if qid == 7 and s == 0:
            red_flags.append("Q7_never_asks_before_sharing")
        if qid == 9 and s == 0:
            red_flags.append("Q9_posts_personal_info_often")
        if qid == 11 and s == 0:
            red_flags.append("Q11_follow_risky_instructions")
        if qid == 14 and s == 0:
            red_flags.append("Q14_share_private_photo")
        if qid == 20 and s == 0:
            red_flags.append("Q20_passes_ai_as_own")

    # combined severe privacy risk: Q7 A plus Q9 A
    # already appended individually; check combined
    q7 = next((a for a in answers if a['qid'] == 7), None)
    q9 = next((a for a in answers if a['qid'] == 9), None)
    if q7 and q9:
        if score_map.get(q7['option'], 0) == 0 and score_map.get(q9['option'], 0) == 0:
            red_flags.append("combined_privacy_severe")

    # soft flag: 3 or more zero answers across pillars
    if zero_answers >= 3:
        red_flags.append("soft_many_zero_answers")

    pillar_percent = {}
    for p in pillar_acc:
        raw = pillar_acc[p]
        maxv = pillar_weight_sum[p] if pillar_weight_sum[p] > 0 else 1
        pct = (raw / maxv) * 100
        pillar_percent[p] = round(pct, 1)

    # Overall score weighted
    overall = 0.0
    for p, wt in PILLAR_WEIGHTS.items():
        overall += pillar_percent[p] * wt / 100.0
    overall = round(overall, 1)

    # Category rules
    category = "TRANSITION"
    if overall < 40 or len(red_flags) > 0:
        category = "NOT READY"
    elif overall >= 70:
        category = "AI-READY"

    # Risk summaries: compute simple derived scores 0-100
    def risk_from_questions(qids: List[int]) -> int:
        vals = []
        for qid in qids:
            a = next((x for x in answers if x['qid'] == qid), None)
            if not a:
                vals.append(0)
            else:
                vals.append(score_map.get(a['option'], 0))
        # invert (lower score = higher risk)
        if not vals:
            return 0
        avg = sum(vals) / len(vals)
        return int(round((avg / 3.0) * 100))

    risks = {
        "cheating_risk": 100 - risk_from_questions([1, 20, 11]),
        "privacy_risk": 100 - risk_from_questions([4, 7, 9, 14]),
        "impulse_hallucination_risk": 100 - risk_from_questions([3, 6, 8, 12]),
        "supervision_gap": 100 - risk_from_questions([10, 19]),
    }

    return {
        "pillar_percentages": pillar_percent,
        "overall_score": overall,
        "category": category,
        "red_flags": red_flags,
        "risks": risks,
    }


def build_summary_payload(child_info: Dict[str, Any], answers: List[Dict]) -> str:
    lines = []
    lines.append(f"Child: {child_info.get('child_name')} (age {child_info.get('child_age')})")
    lines.append(f"Parent contact: {child_info.get('parent_contact')}")
    lines.append("\nAnswers:")
    # attach question text and chosen option
    for a in answers:
        q = next((q for q in QUESTIONS if q['id'] == a['qid']), None)
        opt = a.get('option')
        lines.append(f"Q{a['qid']}: {q['text'] if q else 'unknown'} -> {opt}")

    lines.append("\nPlease return a JSON object with fields: score, category, insights (short narrative), improvement_plan (30/60/90 day bullets), header_summary, observations (3 bullets), why_this_matters (1 sentence), recommended_family_rules (5 bullets), follow_up (next assessment date + whether consultant recommended), monitor_confidence (line with confidence 0-100).")

    return "\n".join(lines)


def call_openrouter(prompt: str) -> Dict[str, Any]:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set on server")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    # Stronger system prompt to encourage clean, parseable JSON with detailed fields
    system_msg = (
        "You are a world-class child-development consultant, licensed child psychologist, and AI-safety specialist writing for CARES. "
        "Adopt a professional, evidence-based, and deeply empathetic tone: concise but thorough, actionable, and suitable for inclusion in a formal report for caregivers and school counsellors. "
        "Return only valid JSON (no extra explanatory text) unless explicitly asked. The JSON must include the following top-level fields: header_summary (string), professional_paragraph (string), observations (array of 3 strings), "
        "why_this_matters (string), improvement_plan (object with keys '30_days','60_days','90_days' each an array of 3 concise bullets), "
        "recommended_family_rules (array of 5 short rules), follow_up (object with next_assessment_date and consultant_recommended), "
        "monitor_confidence (number 0-100), counselor_notes (string), suggested_resources (array of {title, url}), and a compact 'score' and 'category'. "
        "The field 'professional_paragraph' must be a polished, evidence-linked paragraph (3-6 sentences) that: summarizes key findings, links them briefly to pillar results or specific indicators (by pillar or QID), interprets likely behavioral or developmental implications, states immediate priority actions for caregivers, and sets a clear next-step timeline. "
        "Also include an optional 'raw_observations' string if helpful. Output should be JSON only."
    )

    example = (
        "Example JSON:\n```json\n{\n  \"score\": 72,\n  \"category\": \"AI-READY\",\n  \"header_summary\": \"This 12-year-old shows strong digital habits with minor supervision needs.\",\n  \"professional_paragraph\": \"This child demonstrates practical understanding of digital safety with clear areas for guided improvement. Based on pillar scores (DH strong, CC moderate) and specific indicators (occasional oversharing and password risk), immediate priorities are to reinforce password safety, set clearer share rules, and run supervised AI review sessions twice weekly. These steps are recommended to reduce privacy risk while building critical thinking skills; a 90-day follow-up is advised to monitor progress.\",\n  \"observations\": [\"Observation 1\", \"Observation 2\", \"Observation 3\"],\n  \"why_this_matters\": \"Short risk sentence.\",\n  \"improvement_plan\": {\n    \"30_days\": [\"Do X\", \"Do Y\", \"Do Z\"],\n    \"60_days\": [\"Do A\", \"Do B\", \"Do C\"],\n    \"90_days\": [\"Do L\", \"Do M\", \"Do N\"]\n  },\n  \"recommended_family_rules\": [\"Rule1\",\"Rule2\",\"Rule3\",\"Rule4\",\"Rule5\"],\n  \"follow_up\": {\"next_assessment_date\": \"2025-11-01\", \"consultant_recommended\": \"Optional\"},\n  \"monitor_confidence\": 78,\n  \"counselor_notes\": \"Short professional note.\",\n  \"suggested_resources\": [{\"title\": \"Resource 1\", \"url\": \"https://example.org\"}]\n}\n```"
    )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": example},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1000,
        "temperature": 0.1,
    }
    # Allow a longer timeout for AI responses (60s)
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"OpenRouter API error: {resp.status_code} {resp.text}")

    data = resp.json()

    # Try to extract textual content from model
    # The exact path depends on API response structure
    content = None
    try:
        content = data.get('choices', [])[0].get('message', {}).get('content')
    except Exception:
        content = None

    return {
        "raw": data,
        "text": content,
    }


def try_parse_ai_text_to_json(text: str):
    """Try to extract JSON from a model text response. Handles code fences and surrounding text.

    Returns parsed JSON object or None.
    """
    if not text or not isinstance(text, str):
        return None

    # Remove common markdown fences and whitespace
    cleaned = text.strip()

    # If contains ```json ... ``` or ``` ... ```, extract inner block
    import re

    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Otherwise, try to find first { ... } JSON substring
    brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
    if brace_match:
        candidate = brace_match.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # As a last resort, try to load the whole text
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def synthesize_report(parsed: Dict[str, Any], scores: Dict[str, Any], child: Dict[str, Any], answers: List[Dict[str, Any]]):
    """Ensure all expected fields exist by synthesizing reasonable defaults when the model output is incomplete."""
    out = {} if parsed is None else dict(parsed)

    overall = scores.get('overall_score', 0)
    category = scores.get('category', 'UNKNOWN')
    red_flags = scores.get('red_flags', [])
    pillars = scores.get('pillar_percentages', {})
    risks = scores.get('risks', {})

    # header_summary
    if not out.get('header_summary'):
        name = child.get('child_name') or 'The child'
        out['header_summary'] = f"{name} is assessed as {category} with a score of {overall}."

    # professional_paragraph: richer, evidence-linked, expert narrative
    if not out.get('professional_paragraph'):
        name = child.get('child_name') or 'The child'
        # Determine top risks and pillar strengths/weaknesses
        top_risk = None
        top_risk_value = 0
        if risks:
            risk_items = sorted(risks.items(), key=lambda x: x[1], reverse=True)
            if risk_items:
                top_risk, top_risk_value = risk_items[0][0].replace('_', ' '), risk_items[0][1]

        # find strongest and weakest pillars
        pillar_lines = []
        if pillars:
            sorted_p = sorted(pillars.items(), key=lambda x: x[1], reverse=True)
            best = sorted_p[0]
            worst = sorted_p[-1]
            pillar_lines.append(f"strongest area: {best[0]} ({best[1]}%)")
            pillar_lines.append(f"area for improvement: {worst[0]} ({worst[1]}%)")

        # red-flag summary
        rf_line = ''
        if red_flags:
            rf_line = f"Notable immediate concerns: {', '.join(red_flags)}."

        # Compose a 3-5 sentence professional paragraph
        sentences = []
        sentences.append(f"{name} scored {overall} ({category}) on the CARES assessment.")
        if pillar_lines:
            sentences.append(f"Performance shows {pillar_lines[0]} with {pillar_lines[1]}.")
        # Only mention a primary risk if it exceeds a reasonable threshold (avoid false alarms for very small risks)
        RISK_MENTION_THRESHOLD = 40
        if top_risk and top_risk_value >= RISK_MENTION_THRESHOLD:
            sentences.append(f"The primary risk signal is {top_risk} ({top_risk_value}%), which suggests prioritized attention to behaviours that increase privacy or academic risk.")
        if rf_line:
            sentences.append(rf_line)

        # Immediate priorities and tone: if overall is very high and there are no red flags, produce a short, positive paragraph
        if overall >= 90 and not red_flags and (not top_risk or top_risk_value < RISK_MENTION_THRESHOLD):
            sentences = [
                f"{name} scored {overall} ({category}) on the CARES assessment, demonstrating excellent digital habits across measured pillars.",
                "No immediate safety concerns identified; continue current supervision and digital routines.",
                "A routine 90-day check-in is suggested to ensure sustained habits."
            ]
        else:
            sentences.append("Immediate priorities for caregivers: 1) re-affirm clear 'ask-before-share' rules; 2) remove password-sharing risks and set simple account controls; 3) run brief supervised AI-review sessions to practice source-checking and attribution.")
            sentences.append("These recommendations are concise, evidence-aligned, and intended to reduce urgent risk while building skills; schedule a 90-day follow-up to review progress and adapt the plan.")

        para = ' '.join(sentences)
        out['professional_paragraph'] = para

    # observations: three short bullets
    if not out.get('observations'):
        obs = []
        # highest and lowest pillar
        if pillars:
            sorted_p = sorted(pillars.items(), key=lambda x: x[1], reverse=True)
            best = sorted_p[0]
            worst = sorted_p[-1]
            obs.append(f"Strength: highest pillar {best[0]} at {best[1]}%.")
            obs.append(f"Area to improve: lowest pillar {worst[0]} at {worst[1]}%.")
        # red flags or risk summary
        if red_flags:
            obs.append(f"Red flags: {', '.join(red_flags)} — immediate attention recommended.")
        else:
            # add a risk sentence
            risk_items = sorted(risks.items(), key=lambda x: x[1], reverse=True)
            if risk_items:
                top_risk = risk_items[0]
                obs.append(f"Primary concern: {top_risk[0].replace('_',' ')} ({top_risk[1]}).")
            else:
                obs.append("No immediate high-risk indicators detected.")
        # ensure three bullets
        while len(obs) < 3:
            obs.append("")
        out['observations'] = obs[:3]

    # why_this_matters
    if not out.get('why_this_matters'):
        out['why_this_matters'] = (
            "This assessment highlights behaviour and supervision gaps that may expose the child to privacy, safety, or academic risks; "
            "acting on the improvement plan reduces these risks and builds sustainable, safe AI habits."
        )

    # improvement_plan: 30/60/90 day actionable bullets
    if not out.get('improvement_plan'):
        # Base plans on top risk areas
        top_risks = sorted(risks.items(), key=lambda x: x[1], reverse=True)
        top_names = [r[0] for r in top_risks[:3]]

        out['improvement_plan'] = {
            '30_days': [
                'Set clear family AI rules and routines (ask-before-use; no password sharing).',
                'Practice one supervised AI session daily to review outputs together.',
                'Teach one skill: identifying questionable content (source check).'
            ],
            '60_days': [
                'Introduce short weekly reflections: did AI help or cause issues?',
                'Create a simple checklist for homework authenticity and source verification.',
                'Add minor independence tasks with checkpoints (e.g., request permission for new app).'
            ],
            '90_days': [
                'Gradually increase independent use with periodic reviews and accountability.',
                'Co-create a family document of rules and consequences around AI and privacy.',
                'Schedule a follow-up assessment and review progress against initial risks.'
            ]
        }

    # recommended_family_rules
    if not out.get('recommended_family_rules'):
        out['recommended_family_rules'] = [
            'Do not share passwords or OTPs with anyone.',
            'Always ask a parent before installing new apps or sharing photos/locations.',
            'Label AI-generated content and get approval before submission.',
            'Use privacy settings: keep accounts private and block/report strangers.',
            'Establish screen-free times (meals, 1 hour before bed).'
        ]

    # follow_up
    if not out.get('follow_up'):
        from datetime import datetime, timedelta
        next_date = (datetime.utcnow() + timedelta(days=90)).date().isoformat()
        out['follow_up'] = {
            'next_assessment_date': next_date,
            'consultant_recommended': 'Recommended' if red_flags else 'Optional'
        }

    # monitor_confidence
    if out.get('monitor_confidence') is None:
        # base confidence on overall score and presence of red flags
        base = int(round(overall))
        penalty = min(len(red_flags) * 10, 50)
        conf = max(10, base - penalty)
        out['monitor_confidence'] = conf

    # counselor_notes
    if not out.get('counselor_notes'):
        nf = ' ; '.join(red_flags) if red_flags else 'No critical red flags.'
        out['counselor_notes'] = f"Counselor note: Review top concerns: {nf}"

    # suggested_resources
    if not out.get('suggested_resources'):
        out['suggested_resources'] = [
            {'title': 'Child Online Safety Guide', 'url': 'https://www.commonsense.org'},
            {'title': 'Teaching Digital Literacy', 'url': 'https://www.digitalcitizenship.org'},
        ]

    # ensure score & category present
    out.setdefault('score', overall)
    out.setdefault('category', category)

    return out


@app.post("/assess")
def assess(payload: AssessmentIn):
    # compute derived scores
    answers = [a.dict() for a in payload.answers]
    scores = compute_scores(answers)

    # build prompt and call model
    summary = build_summary_payload(payload.dict(), answers)
    try:
        ai = call_openrouter(summary)
    except HTTPException:
        # Save a minimal report and re-raise
        report = {
            "id": int(time.time() * 1000),
            "timestamp": time.time(),
            "child": payload.dict(),
            "scores": scores,
            "ai": None,
        }
        save_report(report)
        raise

    # Attempt to parse AI text as JSON, including JSON inside code fences or surrounding text
    parsed_ai_json = None
    if ai.get('text'):
        parsed_ai_json = try_parse_ai_text_to_json(ai['text'])
        if parsed_ai_json is None:
            # fallback: include text under 'narrative'
            parsed_ai_json = {"narrative": ai['text']}

    # Ensure we have a full structured report by synthesizing missing fields
    final_ai = synthesize_report(parsed_ai_json if isinstance(parsed_ai_json, dict) else {}, scores, payload.dict(), answers)

    # response to frontend: prefer final_ai (synthesized full structure), but include raw ai data
    response_obj = {
        "score": scores['overall_score'],
        "category": scores['category'],
        "header_summary": final_ai.get('header_summary'),
        "professional_paragraph": final_ai.get('professional_paragraph'),
        "observations": final_ai.get('observations'),
        "why_this_matters": final_ai.get('why_this_matters'),
        "improvement_plan": final_ai.get('improvement_plan'),
        "recommended_family_rules": final_ai.get('recommended_family_rules'),
        "follow_up": final_ai.get('follow_up'),
        "monitor_confidence": final_ai.get('monitor_confidence'),
        "counselor_notes": final_ai.get('counselor_notes'),
        "suggested_resources": final_ai.get('suggested_resources'),
        "raw_ai": ai,
        "pillars": scores['pillar_percentages'],
        "risks": scores['risks'],
        "red_flags": scores['red_flags'],
    }

    # Save full raw request/response
    report = {
        "id": int(time.time() * 1000),
        "timestamp": time.time(),
        "child": payload.dict(),
        "answers": answers,
        "scores": scores,
        "ai_raw": ai,
        "ai_parsed": parsed_ai_json,
        "ai_structured": final_ai,
    }
    save_report(report)

    return response_obj


@app.get("/reports")
def get_reports():
    reps = load_reports()
    # return list with minimal metadata
    out = [
        {"id": r.get('id'), "timestamp": r.get('timestamp'), "child": r.get('child', {}).get('child_name'), "scores": r.get('scores')}
        for r in reps
    ]
    return out


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    reps = load_reports()
    r = next((x for x in reps if x.get('id') == report_id), None)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


@app.get("/health")
def health():
    """Health check for load balancers / platforms."""
    return {
        "status": "ok",
        "service": "CARES backend",
        "timestamp": time.time()
    }


@app.get("/")
def root():
    return {"message": "CARES backend is running", "version": "0.1.0"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv('BACKEND_HOST', '127.0.0.1'), port=int(os.getenv('BACKEND_PORT', 8000)), reload=True)
