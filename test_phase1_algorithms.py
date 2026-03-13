"""
Phase 1 algorithm unit tests — pure Python, no DB required.
Tests: Wilson Score, Hot Score, Levenshtein, Priority Aging, EWMA
"""

import math
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────
# 1. Wilson Score Lower Bound
# ─────────────────────────────────────────────────────────────

def wilson_lower_bound(upvotes, downvotes, z=1.96):
    n = upvotes + downvotes
    if n == 0:
        return 0.0
    p = upvotes / n
    return (
        (p + z*z/(2*n) - z * math.sqrt((p*(1-p) + z*z/(4*n))/n))
        / (1 + z*z/n)
    )


def score_to_priority(s):
    if s >= 150:
        return "Critical"
    if s >= 75:
        return "High"
    if s >= 20:
        return "Medium"
    return "Low"


def test_wilson():
    print("=== Wilson Score Tests ===")
    cases = [
        (0,   0,  "No votes → score 0, priority Low"),
        (1,   0,  "1 up / 1 total — low confidence"),
        (10,  0,  "10 up / 10 total — better confidence"),
        (90, 10,  "90% ratio, 100 votes — high"),
        (50, 50,  "50/50 split — near zero"),
        (100, 5,  "100 up, 5 down — high Wilson"),
        (200, 0,  "200 up, 0 down — very high"),
    ]
    for up, dn, desc in cases:
        w = wilson_lower_bound(up, dn)
        score = w * 200
        pri = score_to_priority(score)
        print(f"  up={up:<4} dn={dn:<4} wilson={w:.4f}  score={score:6.2f}  priority={pri}  ({desc})")

    assert wilson_lower_bound(0, 0) == 0.0
    assert wilson_lower_bound(1, 0) < wilson_lower_bound(10, 0), "More votes at same 100% ratio -> higher Wilson"
    # 50/50 split scores lower than 90/10 split (same total votes)
    assert wilson_lower_bound(50, 50) < wilson_lower_bound(90, 10), "50/50 should rank below 90/10"
    # 50/50 scores higher than 0/0 — engagement still matters even with mixed sentiment
    assert wilson_lower_bound(50, 50) > 0.0, "50/50 has positive signal (lower bound ~0.40)"
    # 1 upvote ranks below 10 upvotes at same ratio (sample size penalty)
    assert wilson_lower_bound(1, 0) < wilson_lower_bound(10, 0), "Sample size matters"
    print("  PASS: All Wilson Score assertions passed\n")


# ─────────────────────────────────────────────────────────────
# 2. Hacker News Hot Score
# ─────────────────────────────────────────────────────────────

def hot_score(upvotes, downvotes, age_hours):
    votes = max(1, upvotes - downvotes)
    return votes / (age_hours + 2) ** 1.8


def test_hot_score():
    print("=== Hacker News Hot Score Tests ===")
    complaints = [
        {"id": "A", "up": 5,   "dn": 0,  "age_h": 1,   "desc": "Fresh 5-vote post"},
        {"id": "B", "up": 50,  "dn": 0,  "age_h": 24,  "desc": "1-day old 50-vote post"},
        {"id": "C", "up": 5,   "dn": 0,  "age_h": 168, "desc": "Week-old 5-vote post"},
        {"id": "D", "up": 0,   "dn": 5,  "age_h": 1,   "desc": "Fresh downvoted post"},
        {"id": "E", "up": 100, "dn": 10, "age_h": 48,  "desc": "2-day old high-vote post"},
    ]
    for c in complaints:
        c["score"] = hot_score(c["up"], c["dn"], c["age_h"])

    complaints.sort(key=lambda x: x["score"], reverse=True)
    print("  Sorted by Hot Score (descending):")
    for c in complaints:
        print(f"  [{c['id']}] score={c['score']:.4f}  {c['desc']}")

    # Freshness dominates: same votes, newer always wins
    assert hot_score(5, 0, 1) > hot_score(5, 0, 168), "Fresh post beats week-old with same votes"
    assert hot_score(5, 0, 1) > hot_score(5, 0, 24), "1-hour beats 24-hour with same votes"
    # Higher votes win at same age
    assert hot_score(50, 0, 1) > hot_score(5, 0, 1), "50-vote beats 5-vote at same age"
    # Massive vote advantage can overcome age gap (100 votes vs 5 votes, 2-day vs 1-day)
    assert hot_score(100, 10, 48) > hot_score(5, 0, 24), "100-vote 2-day beats 5-vote 1-day"
    # Downvoted posts get floor score of 1 (max(1, ...)), not negative
    assert hot_score(0, 5, 1) > 0, "Downvoted posts still get minimum score > 0"
    print("  PASS: All Hot Score assertions passed\n")


# ─────────────────────────────────────────────────────────────
# 3. Levenshtein Distance
# ─────────────────────────────────────────────────────────────

def levenshtein(s, t):
    m, n = len(s), len(t)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if s[i-1] == t[j-1]:
                dp[j] = prev[j-1]
            else:
                dp[j] = 1 + min(prev[j], dp[j-1], prev[j-1])
    return dp[n]


FAKE_SPAM = ["spam", "idiot", "garbage", "hack", "abuse"]


def contains_spam(text):
    text_lower = text.lower()
    words = text_lower.split()
    for keyword in FAKE_SPAM:
        klen = len(keyword)
        if klen <= 3 or ' ' in keyword:
            if keyword in text_lower:
                return True, f"exact:{keyword}"
            continue
        max_dist = 2 if klen >= 6 else 1
        for word in words:
            if abs(len(word) - klen) > max_dist:
                continue
            if levenshtein(word, keyword) <= max_dist:
                return True, f"fuzzy:{keyword}~{word}"
    return False, None


def test_levenshtein():
    print("=== Levenshtein Distance Tests ===")
    lev_cases = [
        ("spam",  "spam",  0, "identical"),
        ("spam",  "spem",  1, "1 substitution"),
        ("spam",  "spm",   1, "1 deletion"),
        ("spam",  "spaam", 1, "1 insertion"),
        ("hack",  "h*ck",  1, "asterisk evasion"),
        ("spam",  "xyz",   4, "completely different (4 chars differ)"),
        ("",      "abc",   3, "empty vs 3-char"),
    ]
    for s, t, expected, desc in lev_cases:
        got = levenshtein(s, t)
        status = "PASS" if got == expected else f"FAIL (expected {expected})"
        print(f"  {status}  lev('{s}', '{t}') = {got}  ({desc})")
        assert got == expected

    spam_cases = [
        ("This is spaam content",    True,  "spaam -> spam (1 edit)"),
        ("Normal complaint text",    False, "clean text"),
        ("The food is garbage here", True,  "exact: garbage"),
        ("The idoit messed up",      False, "idoit -> idiot is transposition (2 ops), 5-char max_dist=1 -> no match"),
        ("The idiit messed up",      True,  "idiit -> idiot (1 substitution, 5-char max_dist=1)"),
        ("ha ck the system",         False, "split word should NOT match hack"),
        ("abuuse of the system",     True,  "abuuse -> abuse (1 edit, 5-char, max_dist=1)"),
    ]
    print("\n  Fuzzy spam detection:")
    for text, expected, desc in spam_cases:
        result, why = contains_spam(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}  '{text[:45]}' -> {result} ({why or 'clean'})  [{desc}]")
        assert result == expected, f"contains_spam({text!r}) = {result}, expected {expected}"

    print("  PASS: All Levenshtein assertions passed\n")


# ─────────────────────────────────────────────────────────────
# 4. Priority Queue with Aging
# ─────────────────────────────────────────────────────────────

def aging_score(priority_score, hours_open, upvotes):
    return priority_score + (hours_open / 24) * 10 + upvotes * 2


def test_priority_aging():
    print("=== Priority Queue with Aging Tests ===")
    cases = [
        ("A", 100, 0.5,  5,  "High priority, just assigned, few votes"),
        ("B",  20, 48,   2,  "Medium priority, 2 days old"),
        ("C",  75, 24,  10,  "High priority, 1 day old, 10 votes"),
        ("D",  10, 120,  0,  "Low priority, 5 days old — aging boost"),
        ("E",   0, 240,  0,  "No score, 10 days old — extreme aging"),
    ]
    for id_, ps, hours, ups, desc in cases:
        sc = aging_score(ps, hours, ups)
        print(f"  [{id_}] aging_score={sc:7.2f}  base={ps} hours={hours} upvotes={ups}  ({desc})")

    assert aging_score(10, 240, 0) > aging_score(10, 0, 0), "Aging increases score"
    assert aging_score(150, 0, 0) > aging_score(20, 24, 0), "Critical still beats aged Medium"
    # Low priority open 10 days (score=100+0=100) vs Medium priority fresh (score=20)
    assert aging_score(10, 240, 0) > aging_score(20, 0, 0), "10-day-old Low beats fresh Medium"
    print("  PASS: All Priority Aging assertions passed\n")


# ─────────────────────────────────────────────────────────────
# 5. EWMA
# ─────────────────────────────────────────────────────────────

def ewma(times, alpha=0.3):
    if not times:
        return 0.0
    result = times[0]
    for t in times[1:]:
        result = alpha * t + (1 - alpha) * result
    return result


def test_ewma():
    print("=== EWMA Tests ===")
    ewma_cases = [
        ([10, 10, 10, 10], 10.0, "Stable -> EWMA equals simple avg"),
        ([10, 5],          8.5,  "Recent drop: 0.3*5 + 0.7*10 = 8.5"),
        ([5, 10],          6.5,  "Recent spike: 0.3*10 + 0.7*5 = 6.5"),
        ([],               0.0,  "Empty list -> 0"),
    ]
    for times, expected, desc in ewma_cases:
        got = ewma(times)
        match = abs(got - expected) < 0.01
        status = "PASS" if match else f"FAIL (expected {expected})"
        print(f"  {status}  times={times}  ewma={got:.2f}  ({desc})")
        assert match, f"EWMA{times} = {got}, expected {expected}"

    # EWMA is sensitive to RECENT values (the last in the ordered series).
    # times=[100,100,100,1]: most recent = 1hr (fast); EWMA should show more improvement
    # than simple_avg which treats all four equally.
    times_recent_fast = [100, 100, 100, 1]
    e_recent_fast = ewma(times_recent_fast)
    avg_recent_fast = sum(times_recent_fast) / len(times_recent_fast)
    assert e_recent_fast < avg_recent_fast, (
        f"EWMA should weight recent fast resolution: ewma={e_recent_fast:.2f} avg={avg_recent_fast:.2f}"
    )
    print(f"  PASS  Recent-fast case: ewma={e_recent_fast:.2f} < avg={avg_recent_fast:.2f} (improvement weighted more)")

    # times=[1,1,1,100]: most recent = 100hr (spike); EWMA should reflect spike more than avg
    times_recent_spike = [1, 1, 1, 100]
    e_spike = ewma(times_recent_spike)
    avg_spike = sum(times_recent_spike) / len(times_recent_spike)
    assert e_spike > avg_spike, (
        f"EWMA should weight recent spike: ewma={e_spike:.2f} avg={avg_spike:.2f}"
    )
    print(f"  PASS  Recent-spike case: ewma={e_spike:.2f} > avg={avg_spike:.2f} (deterioration weighted more)")

    print("  PASS: All EWMA assertions passed\n")


# ─────────────────────────────────────────────────────────────
# Run all tests
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_wilson()
    test_hot_score()
    test_levenshtein()
    test_priority_aging()
    test_ewma()

    print("=" * 55)
    print("ALL PHASE 1 ALGORITHM TESTS PASSED")
    print("=" * 55)
