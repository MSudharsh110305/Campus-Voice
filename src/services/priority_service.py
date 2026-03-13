"""
Hybrid priority service for CampusVoice complaint submissions.

Replaces blind LLM-assigned priority with a transparent, multi-signal scoring system.
Every priority decision has a traceable reason.

Signal breakdown (max possible = 90 deterministic + 10 LLM = 100):
  Signal 1: Category baseline       (max 30)
  Signal 2: Urgency/safety keywords (max 25)
  Signal 3: Scope/affected pop.     (max 20)
  Signal 4: Recurrence/duration     (max 15)
  Signal 5: LLM semantic reasoning  (-10 to +10, optional)
             LLM has full SREC college context and examples.
             Adjusts up for missed safety/harassment/mass-impact issues.
             Adjusts down for trivially-low complaints misflagged by keywords.

Final score -> priority:
  >= 50  : Critical
  35-49  : High
  20-34  : Medium
  < 20   : Low
"""

import logging
import asyncio
import json
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Score -> priority mapping thresholds
# ---------------------------------------------------------------------------

def _score_to_priority(score: int) -> str:
    """Map a numeric score to a priority string."""
    if score >= 50:
        return "Critical"
    elif score >= 35:
        return "High"
    elif score >= 20:
        return "Medium"
    else:
        return "Low"


# ---------------------------------------------------------------------------
# Signal 1: Category baseline
# ---------------------------------------------------------------------------

_CATEGORY_SCORES = {
    "Disciplinary Committee": 30,
    "Men's Hostel": 20,
    "Women's Hostel": 20,
    "Department": 15,
    "General": 10,
}


def _signal_category(category_name: str) -> int:
    """Return category baseline score. Unknown categories default to General (10)."""
    return _CATEGORY_SCORES.get(category_name, 10)


# ---------------------------------------------------------------------------
# Signal 2: Urgency / safety keywords (highest matching group only)
# ---------------------------------------------------------------------------

# Ordered highest to lowest — evaluation stops at first match
_URGENCY_GROUPS = [
    # +25
    (25, [
        "health risk", "medical", "injury", "blood", "unconscious",
        "emergency", "danger",
    ]),
    # +25 (same tier, separate group for clarity)
    (25, [
        "fire", "flood", "gas leak", "electric shock", "electrocution",
    ]),
    # +20
    (20, [
        "unsafe", "hazard", "accident", "broken glass", "exposed wire",
        "harass", "harassment",  # added: harassment is a safety/urgency concern
    ]),
    # +15
    (15, [
        "urgent", "immediate", "asap", "help needed", "please fix today",
    ]),
    # +10
    (10, [
        "serious", "major problem", "critical issue", "not working at all",
    ]),
    # -5 (penalty group — match only if NO higher group matched)
    (-5, [
        "minor", "small issue", "suggestion", "inconvenience", "slightly",
    ]),
]


def _signal_urgency(text_lower: str) -> int:
    """
    Return the urgency score for the complaint text.
    Takes the highest matching group only (stops at first positive match).
    The -5 penalty group is only applied if no positive group matched.
    """
    for points, keywords in _URGENCY_GROUPS:
        for kw in keywords:
            if kw in text_lower:
                return points
    return 0


# ---------------------------------------------------------------------------
# Signal 3: Scope / affected population (highest matching group only)
# ---------------------------------------------------------------------------

_SCOPE_GROUPS = [
    # +20: whole-campus / whole-hostel scope
    (20, [
        "all students", "everyone", "whole hostel", "entire block",
        "all rooms", "all floors",
    ]),
    # +15: floor / multi-room scope, or named group of students
    (15, [
        "our floor", "multiple rooms", "many students", "most of us",
        # Named group of students (e.g. "female students", "junior students")
        # The word "students" (plural) after any adjective implies a group
        "female students", "male students", "junior students", "senior students",
        "all girls", "all boys",
    ]),
    # +10: class / batch scope
    (10, [
        "our class", "our batch", "our section",
        "students",  # generic plural "students" without a higher-tier qualifier
    ]),
    # +0: individual scope (explicit — "my room", "just me", "my desk")
    # These phrases are checked so that we never accidentally give +0 for
    # something that also matched a higher tier — but since we stop at first
    # match this group is effectively a no-op placeholder for documentation.
    (0, [
        "my room", "my desk", "just me",
    ]),
]


def _signal_scope(text_lower: str) -> int:
    """Return scope score. Takes highest matching group only."""
    for points, keywords in _SCOPE_GROUPS:
        for kw in keywords:
            if kw in text_lower:
                return points
    return 0


# ---------------------------------------------------------------------------
# Signal 4: Recurrence / duration (highest matching group only)
# ---------------------------------------------------------------------------

import re as _re

_RECURRENCE_GROUPS = [
    # +15: long-standing issue
    (15, [
        "since weeks", "since months", "months now", "still not fixed",
    ]),
    # +15: "for N days/weeks" via regex
    (15, []),  # handled specially below
    # +12: repeated occurrence
    (12, [
        "again", "repeated", "second time", "third time", "keeps happening",
    ]),
    # +10: always / daily
    (10, [
        "always", "every day", "daily problem", "never fixed",
    ]),
    # +8: previously reported
    (8, [
        "last week it happened", "previously reported",
    ]),
]

_RECURRENCE_DURATION_PATTERN = _re.compile(
    r"for\s+\d+\s+(day|days|week|weeks|month|months)", _re.IGNORECASE
)

# Matches "since N days/weeks/months" (e.g. "since 3 weeks", "since 2 months")
_RECURRENCE_SINCE_PATTERN = _re.compile(
    r"since\s+\d+\s+(day|days|week|weeks|month|months)", _re.IGNORECASE
)


def _signal_recurrence(text_lower: str) -> int:
    """Return recurrence score. Takes highest matching group."""
    # Check +15 long-standing keyword group
    for kw in _RECURRENCE_GROUPS[0][1]:
        if kw in text_lower:
            return 15

    # Check +15 duration regex ("for N days/weeks/months")
    if _RECURRENCE_DURATION_PATTERN.search(text_lower):
        return 15

    # Check +15 "since N days/weeks/months" (e.g. "since 3 weeks")
    if _RECURRENCE_SINCE_PATTERN.search(text_lower):
        return 15

    # Check +12 repeated occurrence keywords
    for kw in _RECURRENCE_GROUPS[2][1]:
        if kw in text_lower:
            return 12

    # Check +10 always/daily keywords
    for kw in _RECURRENCE_GROUPS[3][1]:
        if kw in text_lower:
            return 10

    # Check +8 previously reported keywords
    for kw in _RECURRENCE_GROUPS[4][1]:
        if kw in text_lower:
            return 8

    return 0


# ---------------------------------------------------------------------------
# Public API: deterministic (synchronous, no LLM, no DB)
# ---------------------------------------------------------------------------

def calculate_priority_signals(text: str, category_name: str) -> dict:
    """
    Compute deterministic priority signals without any LLM or DB call.

    This function is synchronous and fully testable in isolation.

    Args:
        text: Original complaint text (any case — normalised internally).
        category_name: Category string as assigned by the categorisation step
                       (e.g. "Men's Hostel", "Disciplinary Committee", ...).

    Returns:
        {
            "category_score": int,
            "urgency_score": int,
            "scope_score": int,
            "recurrence_score": int,
            "deterministic_total": int,
            "deterministic_priority": str,   # priority WITHOUT LLM adjustment
        }
    """
    if not text:
        text = ""

    text_lower = text.lower()

    cat_score = _signal_category(category_name)
    urgency_score = _signal_urgency(text_lower)
    scope_score = _signal_scope(text_lower)
    recurrence_score = _signal_recurrence(text_lower)

    total = cat_score + urgency_score + scope_score + recurrence_score
    deterministic_priority = _score_to_priority(total)

    return {
        "category_score": cat_score,
        "urgency_score": urgency_score,
        "scope_score": scope_score,
        "recurrence_score": recurrence_score,
        "deterministic_total": total,
        "deterministic_priority": deterministic_priority,
    }


# ---------------------------------------------------------------------------
# Public API: async — adds optional LLM contextual adjustment
# ---------------------------------------------------------------------------

async def calculate_initial_priority(
    text: str,
    category_name: str,
    groq_client: Optional[Any] = None,
) -> dict:
    """
    Full hybrid priority with optional LLM adjustment (Signal 5).

    Args:
        text: Original complaint text.
        category_name: Category string (e.g. "Men's Hostel").
        groq_client: An initialised Groq client instance (or None to skip LLM).

    Returns:
        {
            "priority": str,          # final priority string
            "score": int,             # final score (deterministic + llm_adjustment)
            "signals": dict,          # output of calculate_priority_signals()
            "llm_adjustment": int,    # -10 to +10, 0 if LLM skipped or failed
            "llm_reason": str,        # one-sentence reason from LLM
        }
    """
    signals = calculate_priority_signals(text, category_name)
    det_total = signals["deterministic_total"]

    llm_adjustment = 0
    llm_reason = "LLM not called"

    if groq_client is not None:
        try:
            det_priority = signals["deterministic_priority"]
            system_msg = (
                "You are the priority arbiter for CampusVoice, a complaint management system at SREC "
                "(Sri Ramakrishna Engineering College), an engineering college in India. "
                "Your job is to apply a semantic sanity-check on top of a rule-based score and adjust "
                "priority when the rules miss the real-world severity.\n\n"
                "PRIORITY LEVELS (final score thresholds):\n"
                "  Critical (score ≥ 50): Life-safety threat, harassment/ragging, complete loss of "
                "essential service affecting many, disciplinary violation in progress.\n"
                "  High    (score ≥ 35): Significant disruption, health risk, major infrastructure "
                "failure, exam-day disruption, repeated unresolved issues.\n"
                "  Medium  (score ≥ 20): Noticeable inconvenience, partial service disruption, "
                "single-room issue, administrative problem.\n"
                "  Low     (score  < 20): Minor suggestion, cosmetic issue, personal preference, "
                "easy one-time fix.\n\n"
                "ADJUST UP examples (under-scored by rules):\n"
                "  • Any mention of ragging, bullying, eve-teasing, sexual harassment → Critical\n"
                "  • Sewage overflow / flooding inside building → High\n"
                "  • Power failure in examination hall or lab during exam → Critical\n"
                "  • Food poisoning / contaminated food → Critical\n"
                "  • Drinking water unavailable for hours → High\n"
                "  • Structural damage, ceiling falling, exposed live wire → Critical\n"
                "  • Student threatening self-harm or expressing distress → Critical\n"
                "  • Mass illness or epidemic-like symptom → Critical\n\n"
                "ADJUST DOWN examples (over-scored by rules):\n"
                "  • Slow WiFi, minor classroom furniture request → Low\n"
                "  • Projector remote missing (not broken) → Low\n"
                "  • 'Urgent' used casually for a suggestion (e.g. 'urgently add a vending machine') → Low\n"
                "  • Single student complaining about personal schedule preference → Low\n"
                "  • Cosmetic issue (paint peeling, small crack in wall) → Low or Medium\n\n"
                "RULES:\n"
                "  1. If the text is unambiguously trivial, adjust DOWN (negative adjustment).\n"
                "  2. If the text describes a safety, harassment, or mass-impact issue that rules missed, "
                "adjust UP (positive adjustment).\n"
                "  3. If the deterministic priority already matches the true severity, return 0.\n"
                "  4. Your adjustment must keep the final score within 0–100.\n"
                "  5. Never adjust more than ±10 points; the rules handle the base signal.\n"
            )

            user_msg = (
                f"Complaint category: {category_name}\n"
                f"Deterministic score: {det_total} → rule-based priority: {det_priority}\n"
                f"Complaint text: \"{text[:600]}\"\n\n"
                f"Based on the actual meaning of this complaint, should the priority score be adjusted?\n"
                f'Reply ONLY with valid JSON (no markdown): '
                f'{{"adjustment": <integer from -10 to 10, multiples of 5 preferred>, "reason": "<one concise sentence>"}}'
            )

            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=120,
                timeout=12,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response (may have surrounding text)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                parsed = json.loads(content[json_start:json_end])
                raw_adj = int(float(parsed.get("adjustment", 0)))
                # Cap to allowed range: -10 to +10, snap to nearest 5
                raw_adj = max(-10, min(10, raw_adj))
                llm_adjustment = round(raw_adj / 5) * 5  # snap to -10,-5,0,5,10
                llm_reason = str(parsed.get("reason", "LLM adjustment applied"))[:200]
            else:
                llm_adjustment = 0
                llm_reason = "LLM response not parseable"

        except Exception as exc:
            logger.warning(f"Priority LLM adjustment failed: {exc}")
            llm_adjustment = 0
            llm_reason = "LLM unavailable"

    final_score = det_total + llm_adjustment
    final_priority = _score_to_priority(final_score)

    return {
        "priority": final_priority,
        "score": final_score,
        "signals": signals,
        "llm_adjustment": llm_adjustment,
        "llm_reason": llm_reason,
    }
