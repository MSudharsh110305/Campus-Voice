"""
Standalone test script for hybrid duplicate detection.

Run:          python test_duplicate_detection.py
Interactive:  python test_duplicate_detection.py -i
"""

import re
from itertools import combinations

# -- Stop words ----------------------------------------------------------------
_STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'in', 'on', 'at', 'of',
    'for', 'to', 'with', 'by', 'from', 'not', 'no', 'my', 'our', 'i',
    'we', 'it', 'its', 'this', 'that', 'very', 'so', 'and', 'or', 'but',
    'there', 'their', 'they', 'what', 'when', 'where', 'which', 'who',
    'how', 'all', 'also', 'just', 'get', 'got', 'still', 'please',
    'since', 'been', 'even', 'too', 'now', 'days', 'day', 'week',
    'month', 'months', 'time', 'has', 'always', 'never', 'need',
    'needs', 'want', 'due', 'said', 'told', 'every', 'each',
}

# -- Synonyms (must match complaints.py exactly) --------------------------------
_SYNONYMS = [
    (r'\ba\.c\b',               'air conditioner'),
    (r'\bac\b',                 'air conditioner'),
    (r'\bwi-fi\b',              'wireless internet'),
    (r'\bwifi\b',               'wireless internet'),
    (r'\bbroadband\b',          'internet'),
    (r'\bnet\b',                'internet'),
    (r'\bnetwork\b',            'internet'),
    (r'\bcctv\b',               'camera security'),
    (r'\btube light\b',         'bulb electricity'),
    (r'\btubelight\b',          'bulb electricity'),
    (r'\bswitchboard\b',        'socket switch'),
    (r'\bgeyser\b',             'hot water heater'),
    (r'\binverter\b',           'power backup electricity'),
    (r'\bgenerator\b',          'power backup electricity'),
    (r'\bups\b',                'power backup electricity'),
    (r'\bro\b',                 'water purifier'),
    (r'\bwater purifier\b',     'water purifier'),
    (r'\bwater cooler\b',       'water cooler'),
    (r'\bpurifier\b',           'water purifier'),
    (r'\brest room\b',          'toilet bathroom'),
    (r'\brestroom\b',           'toilet bathroom'),
    (r'\bwashroom\b',           'toilet bathroom'),
    (r'\bwc\b',                 'toilet bathroom'),
    (r'\bloo\b',                'toilet bathroom'),
    (r'\blavatory\b',           'toilet bathroom'),
    (r'\blatrine\b',            'toilet bathroom'),
    (r'\btoilets\b',            'toilet bathroom'),
    (r'\bbathrooms\b',          'toilet bathroom'),
    (r'\bcommode\b',            'toilet bathroom'),
    (r'\bcanteen\b',            'cafeteria'),
    (r'\bmess\b',               'cafeteria'),
    (r'\btiffin\b',             'meal food'),
    (r'\bsnacks\b',             'snack food'),
    (r'\bvending machine\b',    'snack food machine'),
    (r'\belectricity\b',        'electricity power'),
    (r'\belectrcity\b',         'electricity power'),  # transposed c/i typo
    (r'\bpower\b',              'electricity power'),
    (r'\blight\b',              'electricity power'),
    (r'\bblackout\b',           'electricity power outage'),
    (r'\bpower cut\b',          'electricity power outage'),
    (r'\boutage\b',             'electricity power outage'),
    (r'\bprofessor\b',          'faculty teacher'),
    (r'\bprof\b',               'faculty teacher'),
    (r'\bfaculty\b',            'faculty teacher'),
    (r'\blecturer\b',           'faculty teacher'),
    (r'\bsir\b',                'faculty teacher'),
    (r'\bmadam\b',              'faculty teacher'),
    (r'\bmaam\b',               'faculty teacher'),
    (r'\bmam\b',                'faculty teacher'),
    (r'\bhod\b',                'head department'),
    (r'\bvice principal\b',     'admin authority'),
    (r'\bprincipal\b',          'admin authority'),
    (r'\bwarden\b',             'hostel authority'),
    (r'\btnp\b',                'placement'),
    (r'\btpo\b',                'placement officer'),
    (r'\bcampus drive\b',       'placement'),
    (r'\boff campus\b',         'placement'),
    (r'\bdorm\b',               'hostel'),
    (r'\bpg\b',                 'hostel'),
    (r'\bclass room\b',         'classroom'),
    (r'\blecture hall\b',       'classroom hall'),
    (r'\blab\b',                'laboratory'),
    (r'\blabs\b',               'laboratory'),
    (r'\bblocks\b',             'block'),
    (r'\blectures\b',           'class lecture'),
    (r'\blecture\b',            'class lecture'),
    (r'\bclasses\b',            'class'),
    (r'\bexams\b',              'exam'),
    (r'\binternal exam\b',      'exam internal'),
    (r'\binternal\b',           'exam internal'),
    (r'\bclass test\b',         'exam test'),
    (r'\bassignments\b',        'assignment'),
    (r'\bbunking\b',            'absent class'),
    (r'\babsent\b',             'not attending'),
    (r'\bcleanliness\b',        'clean'),
    (r'\bcleaned\b',            'clean'),
    (r'\bcleaning\b',           'clean'),
    (r'\bunclean\b',            'dirty'),
    (r'\bfilthy\b',             'dirty'),
    (r'\bunhygienic\b',         'dirty hygiene'),
    (r'\bunhygenic\b',          'dirty hygiene'),   # missing 'i' typo
    (r'\bstinking\b',           'smell stink'),
    (r'\bsmelling\b',           'smell'),
    (r'\bsmells\b',             'smell'),
    (r'\bfoul\b',               'smell dirty'),
    (r'\bmaintenance\b',        'maintain'),
    (r'\bmaintained\b',         'maintain'),
    (r'\brepairing\b',          'repair fix'),
    (r'\brepaired\b',           'repair fix'),
    (r'\brepair\b',             'fix'),
    (r'\bfixed\b',              'fix'),
    (r'\bfixing\b',             'fix'),
    (r'\bnot working\b',        'break'),
    (r'\bworking\b',            'work'),
    (r'\bworks\b',              'work'),
    (r'\bbroken\b',             'break'),
    (r'\bbreaking\b',           'break'),
    (r'\bdamaged\b',            'damage'),
    (r'\bdamaging\b',           'damage'),
    (r'\bleaking\b',            'leak'),
    (r'\bleaky\b',              'leak'),
    (r'\bflooded\b',            'flood water'),
    (r'\bsupplied\b',           'supply'),
    (r'\bteaching\b',           'teach'),
    (r'\bdisturbing\b',         'disturb'),
    (r'\bharrassing\b',         'harass'),
    (r'\bharassing\b',          'harass'),
    (r'\bbullying\b',           'bully'),
    (r'\bragging\b',            'ragging'),
    (r'\battending\b',          'attend'),
    (r'\bthrown\b',             'throw garbage'),
    (r'\blittering\b',          'garbage dirty'),
    (r'\boverflowing\b',        'overflow'),
    (r'\bblocked\b',            'block'),
    (r'\bclogged\b',            'block drain'),
]

# -- Topic clusters ------------------------------------------------------------
_COMPLAINT_TOPICS = {
    "hygiene_sanitation": {
        "dirty", "clean", "hygiene", "sanitation", "garbage", "waste",
        "smell", "stink", "filthy", "sewage", "drain", "trash",
        "cockroach", "pest", "rat", "mice", "insect", "mold", "mould",
        "toilet", "bathroom", "latrine", "commode", "litter",
        "sweep", "swept", "mop", "mopped", "scrub",
    },
    "food_quality": {
        # "food" and "cafeteria" excluded — location tokens that cause false positives
        "meal", "menu", "taste", "tasty", "tasteless",
        "cook", "cooked", "serve", "serving", "veg", "nonveg",
        "breakfast", "lunch", "dinner", "rice", "roti", "curry",
        "stale", "expired", "quantity", "portion", "snack",
        "edible", "variety", "dish", "item", "tiffin", "sambar",
        "chapati", "quality",
    },
    "infrastructure": {
        "break", "damage", "fix", "leak", "crack",
        "door", "window", "roof", "wall", "ceiling",
        "table", "chair", "bench", "furniture", "paint",
        "peeling", "collapse", "maintain", "repair", "crumble",
    },
    "internet_connectivity": {
        "internet", "wireless", "connectivity",
        "connection", "bandwidth", "speed", "slow", "disconnect",
        "signal", "router", "lan", "hotspot",
    },
    "electricity_hvac": {
        "electricity", "fan", "cooling", "heating",
        "voltage", "socket", "switch", "bulb", "tube",
        "wiring", "circuit", "tripped", "outage",
        "conditioner",
    },
    "water_supply": {
        "water", "supply", "shortage", "drinking", "tap", "pipe",
        "pressure", "borewell", "tank", "overflow", "muddy", "purifier",
        "cooler", "flood",
    },
    "academic_faculty": {
        "faculty", "teacher", "class", "lecture",
        "attendance", "marks", "grade", "exam", "assignment",
        "syllabus", "course", "subject", "teach",
        "notes", "material", "practical", "curriculum",
        "attend", "absent", "internal", "test",
    },
    "discipline_harassment": {
        "ragging", "harassment", "harass", "bully", "threat", "abuse",
        "violence", "misbehave", "misconduct", "tease", "intimidate",
        "inappropriate", "verbal", "physical", "eve",
    },
    "placement_career": {
        "placement", "internship", "job", "company", "recruit",
        "interview", "offer", "career", "opportunity",
        "resume", "training", "drive",
    },
    "transport": {
        "bus", "transport", "vehicle", "auto", "cab", "route", "driver",
        "timing", "schedule", "commute", "fuel", "breakdown",
    },
    "security": {
        "security", "guard", "camera", "theft", "stolen",
        "lock", "entry", "access", "badge", "safe",
    },
    "library": {
        "book", "library", "journal", "reading", "reference",
        "return", "resource", "catalog",
    },
    "financial": {
        "scholarship", "stipend", "fee", "refund", "dues",
        "payment", "challan", "fine", "penalty",
    },
    "hostel_admin": {
        # "night" removed — too ambiguous, fires on "every night" in power/water complaints
        "curfew", "permission", "outing", "leave",
        "visitor", "warden", "authority", "rule", "regulation",
    },
}

_LOCATION_WORDS = {
    "hostel", "block", "floor", "building", "classroom", "laboratory",
    "department", "college", "campus", "ground", "field", "corridor",
    "hall", "gate", "parking", "workshop", "gym", "quarter", "court",
    "room", "area", "section", "wing",
}

# -- Core functions (must match complaints.py exactly) -------------------------

def _preprocess(text):
    t = (text or "").lower().strip()
    for pattern, replacement in _SYNONYMS:
        t = re.sub(pattern, replacement, t)
    t = re.sub(r"[^\w\s]", " ", t)
    return t

def _word_tokens(text):
    return {w for w in _preprocess(text).split() if len(w) > 2 and w not in _STOP_WORDS}

def _char_ngrams(text, n=3):
    # n=3 (trigrams): better typo tolerance — 1-char error destroys only 3
    # adjacent trigrams vs 4 quadgrams, so more grams survive to score.
    normalized = "".join(_preprocess(text).split())
    return {normalized[i:i+n] for i in range(len(normalized) - n + 1)} if len(normalized) >= n else set()

def _get_topic_clusters(text):
    tokens = set(_preprocess(text).split())
    return frozenset(c for c, kw in _COMPLAINT_TOPICS.items() if tokens & kw)

def _cluster_weight(ca, cb):
    if not ca or not cb:
        return 1.0
    return 1.3 if ca & cb else 0.30

def _topic_tokens(text):
    return _word_tokens(text) - _LOCATION_WORDS

def _bigram_jaccard(tokens_a, tokens_b):
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return 0.0
    ba = set(combinations(sorted(tokens_a), 2))
    bb = set(combinations(sorted(tokens_b), 2))
    return len(ba & bb) / len(ba | bb) if (ba | bb) else 0.0

def _levenshtein(s1, s2):
    if s1 == s2:
        return 0
    m, n = len(s1), len(s2)
    if abs(m - n) > 3:
        return abs(m - n)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if s1[i-1] == s2[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = temp
    return dp[n]

def _fuzzy_token_score(tokens_a, tokens_b):
    eligible_a = [t for t in tokens_a if len(t) >= 4]
    eligible_b = [t for t in tokens_b if len(t) >= 4]
    if not eligible_a or not eligible_b:
        return 0.0
    def _count_matched(src, tgt):
        matched = 0
        for t in src:
            thresh = 1 if len(t) <= 6 else 2
            for u in tgt:
                if abs(len(t) - len(u)) > thresh:
                    continue
                if _levenshtein(t, u) <= thresh:
                    matched += 1
                    break
        return matched
    return (_count_matched(eligible_a, eligible_b) / len(eligible_a)
            + _count_matched(eligible_b, eligible_a) / len(eligible_b)) / 2

def _hybrid_similarity(a, b):
    wa, wb = _word_tokens(a), _word_tokens(b)
    word_score = len(wa & wb) / len(wa | wb) if (wa | wb) else 0.0
    ta, tb = _topic_tokens(a), _topic_tokens(b)
    if ta and tb:
        topic_score = len(ta & tb) / len(ta | tb)
        bigram_score = _bigram_jaccard(ta, tb)
        fuzzy_score  = _fuzzy_token_score(ta, tb)
    else:
        topic_score  = word_score
        bigram_score = 0.0
        fuzzy_score  = _fuzzy_token_score(wa, wb)
    ca, cb = _char_ngrams(a), _char_ngrams(b)
    char_score = len(ca & cb) / len(ca | cb) if (ca | cb) else 0.0
    raw = (0.30 * word_score + 0.20 * topic_score
           + 0.10 * bigram_score + 0.15 * char_score + 0.25 * fuzzy_score)
    return min(1.0, raw * _cluster_weight(_get_topic_clusters(a), _get_topic_clusters(b)))


# -- Test cases ----------------------------------------------------------------
DETECTION_THRESHOLD  = 0.12
LIKELY_DUP_THRESHOLD = 0.25

TEST_CASES = [

    # ===== FALSE POSITIVE GUARD — same location, different topic ==============
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "food_court_restroom_vs_food_quality",
        "a": "The men's restroom in the food court is not being properly cleaned",
        "b": "The food at the food court is not satisfactory. The quality of the food is a concern.",
        "max": 0.12,
    },
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "food_court_restroom_vs_menu_variety",
        "a": "Men's restroom in the food court is dirty and smells bad",
        "b": "The food court's menu options are unvaried and lack diversity",
        "max": 0.12,
    },
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "hostel_restroom_vs_hostel_wifi",
        "a": "Restroom in hostel block A is unhygienic and not cleaned",
        "b": "WiFi internet is very slow in hostel block A cannot study",
        "max": 0.12,
    },
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "canteen_dirty_vs_canteen_food_quality",
        "a": "Canteen is full of cockroaches and very dirty unhygienic",
        "b": "Canteen food is stale and tasteless quantity is very less",
        "max": 0.15,
    },
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "classroom_ac_vs_classroom_attendance",
        "a": "AC in the classroom is not working we are sweating a lot",
        "b": "Professor is not marking attendance properly in our classroom",
        "max": 0.15,
    },
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "water_shortage_vs_wifi_slow",
        "a": "No water supply in hostel since morning we cannot even drink",
        "b": "Internet is very slow in hostel cannot attend online classes",
        "max": 0.12,
    },
    {
        "group": "FALSE POSITIVE GUARD",
        "label": "scholarship_vs_ragging",
        "a": "My scholarship amount has not been credited for three months",
        "b": "Senior students are ragging juniors in the hostel at night",
        "max": 0.10,
    },

    # ===== TRUE DUPLICATES — same issue, different phrasing ==================
    {
        "group": "TRUE DUPLICATE",
        "label": "restroom_not_clean_vs_near_identical",
        "a": "food court restroom not clean",
        "b": "The food court restroom was not clean. It needs to be cleaned regularly.",
        "min": 0.55,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "restroom_not_clean_vs_properly_cleaned",
        "a": "food court restroom not clean",
        "b": "The men's restroom in the food court is not being properly cleaned. Regular maintenance needed.",
        "min": 0.40,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "ac_synonym_expansion",
        "a": "AC not working in hostel room since three days",
        "b": "Air conditioner broken in my room not cooling at all",
        "min": 0.25,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "restroom_dirty_washroom_synonym",
        "a": "Restroom on third floor is very dirty and smells bad",
        "b": "Washroom in third floor is filthy and unhygienic please clean it",
        "min": 0.35,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "water_shortage_rephrased",
        "a": "Water supply in hostel is not available since this morning",
        "b": "No water in hostel block since last night severe shortage",
        "min": 0.18,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "wifi_slow_rephrased",
        "a": "WiFi is very slow in library cannot connect to internet",
        "b": "Internet connectivity issue in block B completely down cannot access",
        "min": 0.15,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "teacher_absent_rephrased",
        "a": "Professor not attending classes regularly since 2 months",
        "b": "Teacher is absent very frequently not teaching properly at all",
        "min": 0.15,
    },
    {
        "group": "TRUE DUPLICATE",
        "label": "food_quality_canteen_vs_mess",
        "a": "Food quality in canteen is very poor tasteless food served daily",
        "b": "Mess food is not satisfactory quality is bad every day",
        "min": 0.25,
    },

    # ===== INDIAN COLLEGE SHORT FORMS =========================================
    {
        "group": "INDIAN COLLEGE SHORT FORMS",
        "label": "sir_vs_professor",
        "a": "Sir is not coming to class for the past two weeks",
        "b": "Professor has not taken a single lecture this month",
        "min": 0.20,
    },
    {
        "group": "INDIAN COLLEGE SHORT FORMS",
        "label": "hod_vs_department_head",
        "a": "HOD is not responding to our complaints about lab equipment",
        "b": "The department head does not address student issues at all",
        "min": 0.14,
    },
    {
        "group": "INDIAN COLLEGE SHORT FORMS",
        "label": "tnp_vs_placement",
        "a": "TNP cell is not organizing any company visits this semester",
        "b": "Placement office has not arranged a single drive for final year",
        "min": 0.10,
    },
    {
        "group": "INDIAN COLLEGE SHORT FORMS",
        "label": "net_vs_wifi_slow",
        "a": "Net is very slow in hostel cannot stream anything",
        "b": "WiFi speed is too low in block B cannot even load pages",
        "min": 0.18,
    },
    {
        "group": "INDIAN COLLEGE SHORT FORMS",
        "label": "mam_vs_teacher",
        "a": "Mam is marking us absent even though we attended the class",
        "b": "Teacher is incorrectly marking attendance we were present",
        "min": 0.18,
    },

    # ===== TYPOS & SPELLING MISTAKES (Levenshtein) ============================
    {
        "group": "TYPOS & SPELLING MISTAKES",
        "label": "maintanence_typo",
        "a": "Restroom requires regular maintanence it is very dirty",
        "b": "Bathroom needs proper maintenance it is unhygienic",
        "min": 0.27,
    },
    {
        "group": "TYPOS & SPELLING MISTAKES",
        "label": "unhygenic_typo",
        "a": "The canteen is very unhygenic cockroaches everywhere",
        "b": "Canteen is unhygienic and dirty needs immediate cleaning",
        "min": 0.25,
    },
    {
        "group": "TYPOS & SPELLING MISTAKES",
        "label": "electrcity_typo",
        "a": "Electrcity keeps going off in our hostel room every night",
        "b": "Electricity power cut in hostel block happens very frequently",
        "min": 0.15,
    },
    {
        "group": "TYPOS & SPELLING MISTAKES",
        "label": "harrassing_misspelling",
        "a": "Senior students are harrassing juniors in the hostel corridor",
        "b": "Ragging and harassment by seniors is happening in hostel block",
        "min": 0.18,
    },
    {
        "group": "TYPOS & SPELLING MISTAKES",
        "label": "cleanlness_typo",
        "a": "The cleanlness of the hostel bathrooms is very poor",
        "b": "Cleanliness standard of hostel toilet is not being maintained",
        "min": 0.22,
    },

    # ===== COMPLETELY UNRELATED ===============================================
    {
        "group": "UNRELATED",
        "label": "professor_vs_internet",
        "a": "Professor is not attending class at all no lectures",
        "b": "Internet is too slow cannot access anything in library",
        "max": 0.10,
    },
    {
        "group": "UNRELATED",
        "label": "security_vs_food",
        "a": "Security guard misbehaved with student at main gate threatened",
        "b": "Mess food is stale and expired making students fall sick",
        "max": 0.10,
    },
    {
        "group": "UNRELATED",
        "label": "placement_vs_water",
        "a": "Placement cell is not organizing any company visits this semester",
        "b": "No water supply in hostel bathrooms since two days",
        "max": 0.10,
    },
    {
        "group": "UNRELATED",
        "label": "scholarship_vs_wifi",
        "a": "Scholarship not credited for three months financial problem",
        "b": "WiFi in library is too slow cannot submit assignments online",
        "max": 0.10,
    },
    {
        "group": "UNRELATED",
        "label": "bus_timing_vs_ragging",
        "a": "College bus is always late by one hour every morning",
        "b": "Senior students are ragging first year students in hostel",
        "max": 0.10,
    },
]


# -- Runner -------------------------------------------------------------------

def run_tests():
    passed = 0
    failed = 0
    current_group = None

    for t in TEST_CASES:
        if t["group"] != current_group:
            current_group = t["group"]
            print(f"\n{'-'*64}")
            print(f"  {current_group}")
            print(f"{'-'*64}")

        score = _hybrid_similarity(t["a"], t["b"])
        pct   = score * 100
        ca    = sorted(_get_topic_clusters(t["a"]))
        cb    = sorted(_get_topic_clusters(t["b"]))

        ok  = True
        if "min" in t and score < t["min"]:
            ok = False
        if "max" in t and score > t["max"]:
            ok = False

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        bound      = f">= {t['min']*100:.0f}%" if "min" in t else f"<= {t['max']*100:.0f}%"
        detection  = "SHOWN" if score >= DETECTION_THRESHOLD else "hidden"
        print(f"  [{status}] {t['label']}")
        print(f"         Score: {pct:.1f}%  (expected {bound})  [{detection}]")
        if not ok:
            print(f"         Clusters A: {ca or ['(none)']}")
            print(f"         Clusters B: {cb or ['(none)']}")
            print(f"         A: {t['a'][:80]}")
            print(f"         B: {t['b'][:80]}")

    total = passed + failed
    print(f"\n{'='*64}")
    print(f"  Result : {passed}/{total} passed {'OK' if not failed else 'FAILED'}")
    print(f"  Thresholds: show >= {DETECTION_THRESHOLD*100:.0f}%  |  warn >= {LIKELY_DUP_THRESHOLD*100:.0f}%")
    print(f"{'='*64}\n")
    return failed == 0


def interactive_check():
    print("\n-- Interactive checker (Ctrl+C to exit) --")
    while True:
        try:
            a = input("\nComplaint A: ").strip()
            b = input("Complaint B: ").strip()
            if not a or not b:
                continue
            score = _hybrid_similarity(a, b)
            ca    = sorted(_get_topic_clusters(a))
            cb    = sorted(_get_topic_clusters(b))
            wt    = _cluster_weight(frozenset(ca), frozenset(cb))
            # individual signals
            wa, wb = _word_tokens(a), _word_tokens(b)
            ta, tb = _topic_tokens(a), _topic_tokens(b)
            ws = len(wa & wb) / len(wa | wb) if (wa | wb) else 0
            ts = len(ta & tb) / len(ta | tb) if (ta | tb) else 0
            fs = _fuzzy_token_score(ta or wa, tb or wb)
            print(f"\n  Score      : {score*100:.1f}%")
            print(f"  Clusters A : {ca or ['(none)']}")
            print(f"  Clusters B : {cb or ['(none)']}")
            print(f"  Cluster wt : {wt}x")
            print(f"  Word Jac   : {ws*100:.1f}%  |  Topic Jac: {ts*100:.1f}%  |  Fuzzy: {fs*100:.1f}%")
            if score >= LIKELY_DUP_THRESHOLD:
                print("  Decision   : LIKELY DUPLICATE — warn student")
            elif score >= DETECTION_THRESHOLD:
                print("  Decision   : Show as candidate")
            else:
                print("  Decision   : Not shown (below threshold)")
        except KeyboardInterrupt:
            print("\nDone.")
            break


if __name__ == "__main__":
    import sys
    print("CampusVoice — Hybrid Duplicate Detection Test Suite")
    print("=" * 64)
    all_passed = run_tests()
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive_check()
    sys.exit(0 if all_passed else 1)
