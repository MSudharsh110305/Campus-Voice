"""
SREC-specific normalization map for complaint text preprocessing.
Expands shortforms, fixes typos, and maps campus-specific terminology
BEFORE sending text to the LLM for categorization.
"""

import re

# ── Department aliases ────────────────────────────────────────────────────────
DEPARTMENT_ALIASES = {
    # CSE (short code + expansions)
    "cse": "CSE", "comp sci": "CSE", "computer science": "CSE", "cs dept": "CSE",
    "cs department": "CSE", "cse dept": "CSE", "cse department": "CSE",
    "compsci": "CSE", "comp sc": "CSE",
    # IT
    "it": "IT", "information technology": "IT", "infotech": "IT", "it dept": "IT",
    "it department": "IT",
    # ECE
    "ece": "ECE", "electronics": "ECE", "ece dept": "ECE", "ece department": "ECE",
    "ec dept": "ECE", "e&c": "ECE",
    # EEE
    "eee": "EEE", "electrical": "EEE", "eee dept": "EEE", "eee department": "EEE",
    "ee dept": "EEE", "e&e": "EEE",
    # EIE
    "eie": "EIE", "instrumentation": "EIE", "eie dept": "EIE", "eie department": "EIE",
    "e&i": "EIE",
    # MECH
    "mech": "MECH", "mechanical": "MECH", "mech dept": "MECH", "mech department": "MECH",
    "me dept": "MECH",
    # CIVIL
    "civil": "CIVIL", "civil dept": "CIVIL", "civil department": "CIVIL", "ce dept": "CIVIL",
    "civil engineering": "CIVIL",
    # AERO
    "aero": "AERO", "aeronautical": "AERO", "aero dept": "AERO", "aero department": "AERO",
    "aerospace": "AERO",
    # BIO / BME
    "bio": "BIO", "biomedical": "BIO", "bme": "BIO", "bio dept": "BIO",
    "bio department": "BIO", "biomed": "BIO", "biomedical engineering": "BIO",
    # AIDS
    "aids": "AIDS", "aiml": "AIDS", "ai ml": "AIDS", "ai&ds": "AIDS", "ai ds": "AIDS",
    "ai and ds": "AIDS", "artificial intelligence": "AIDS",
    "data science": "AIDS", "aids dept": "AIDS", "aids department": "AIDS",
    "ai dept": "AIDS", "ai department": "AIDS",
    # RAA / Robotics
    "raa": "RAA", "robotics": "RAA", "raa dept": "RAA", "raa department": "RAA",
    "automation": "RAA", "robotics and automation": "RAA",
    "r&a": "RAA", "robo": "RAA",
    # MBA
    "mba": "MBA", "management": "MBA", "mba dept": "MBA", "mba department": "MBA",
    "business administration": "MBA",
    # MTECH
    "m.tech": "MTECH_CSE", "mtech": "MTECH_CSE", "m tech": "MTECH_CSE",
    "m.tech cse": "MTECH_CSE", "pg cse": "MTECH_CSE",
    # Science & Humanities (SH)
    "sh": "SH", "science and humanities": "SH", "s&h": "SH",
    "sh dept": "SH", "sh department": "SH",
    # Individual S&H subjects
    "maths": "MATH", "mathematics": "MATH", "math dept": "MATH",
    "math department": "MATH", "maths dept": "MATH",
    "physics": "PHY", "physics dept": "PHY", "physics department": "PHY",
    "phy dept": "PHY",
    "chemistry": "CHEM", "chem": "CHEM", "chemistry dept": "CHEM",
    "chemistry department": "CHEM", "chem dept": "CHEM", "chem lab": "CHEM laboratory",
    "english": "ENG", "english dept": "ENG", "english department": "ENG",
    "eng dept": "ENG",
}

# ── Facility aliases ──────────────────────────────────────────────────────────
FACILITY_ALIASES = {
    # Food / canteen
    "fc": "food court", "food court": "food court", "canteen": "canteen",
    "mess": "hostel mess", "mess hall": "hostel mess hall",
    # Hostels
    "gh": "mens hostel", "gents hostel": "mens hostel",
    "boys hostel": "mens hostel", "bh": "mens hostel",
    "lh": "womens hostel", "ladies hostel": "womens hostel",
    "girls hostel": "womens hostel",
    # Equipment / infra
    "ac": "air conditioner", "a/c": "air conditioner", "a.c": "air conditioner",
    "water doctor": "water dispenser", "water purifier": "water dispenser",
    "ro": "water purifier", "ro water": "purified water",
    "projector": "projector", "lcd": "projector",
    # Campus locations
    "lib": "library", "libr": "library", "reading room": "library reading room",
    "audi": "auditorium", "auditorium": "auditorium",
    "seminar hall": "seminar hall", "sem hall": "seminar hall",
    "playground": "playground", "ground": "sports ground",
    "parking": "parking area", "parking lot": "parking area",
    "main block": "main block", "admin block": "administrative block",
    "workshop": "workshop", "wd": "workshop",
    # Rooms / infra
    "cr": "classroom", "class room": "classroom",
    "washroom": "washroom", "toilet": "toilet", "wc": "washroom",
    "restroom": "restroom", "rest room": "restroom",
    "lab": "laboratory", "computer lab": "computer laboratory",
    "server room": "server room",
    # Transport
    "college bus": "college bus", "bus": "college bus",
    # Network
    "wifi": "wi-fi internet", "wi-fi": "wi-fi internet",
    "net": "internet", "lan": "wired internet",
}

# ── Role aliases ──────────────────────────────────────────────────────────────
ROLE_ALIASES = {
    "hod": "head of department", "h.o.d": "head of department",
    "head of dept": "head of department",
    "ca": "class advisor", "class advisor": "class advisor",
    "class incharge": "class advisor", "class in-charge": "class advisor",
    "ao": "administrative officer", "admin officer": "administrative officer",
    "dc": "disciplinary committee", "disc committee": "disciplinary committee",
    "sdw": "senior deputy warden", "senior warden": "senior deputy warden",
    "sub warden": "deputy warden", "asst warden": "deputy warden",
    "assistant warden": "deputy warden",
    "mam": "madam", "ma'am": "madam",
    "sir": "sir", "prof": "professor",
    "tp": "training and placement", "t&p": "training and placement",
    "placement cell": "training and placement cell",
    "placement officer": "training and placement officer",
    "principal": "principal", "dean": "dean",
}

# ── Complaint shortforms & typos ──────────────────────────────────────────────
COMPLAINT_ALIASES = {
    # Urgency
    "pls": "please", "plz": "please", "plss": "please",
    "asap": "urgent", "urgnt": "urgent", "urgt": "urgent",
    # Academics
    "reval": "revaluation", "re-eval": "revaluation",
    "ia": "internal assessment", "ia marks": "internal assessment marks",
    "ia exam": "internal assessment exam",
    "od": "on duty", "o.d": "on duty",
    "ct": "class test", "cat": "continuous assessment test",
    "sem": "semester", "sem exam": "semester exam",
    "arrear": "arrear exam", "arrears": "arrear exams",
    "supple": "supplementary exam",
    "cgpa": "CGPA", "gpa": "GPA",
    "att": "attendance", "attendance": "attendance",
    "obs book": "observation book", "obs": "observation book",
    "lab record": "laboratory record", "lab manual": "laboratory manual",
    "mini project": "mini project", "proj": "project",
    # Common typos
    "maintainance": "maintenance", "maintanance": "maintenance",
    "maintenence": "maintenance", "maintaince": "maintenance",
    "electricty": "electricity", "electrcity": "electricity",
    "toilett": "toilet", "toilete": "toilet",
    "cleanlness": "cleanliness", "cleaniness": "cleanliness",
    "complaitn": "complaint", "compliant": "complaint",
    "professer": "professor", "proffessor": "professor",
    "infrastucture": "infrastructure", "infastructure": "infrastructure",
    "harrasment": "harassment", "harasment": "harassment",
    "raging": "ragging", "raggging": "ragging",
    "brokn": "broken", "borken": "broken",
    "hostle": "hostel", "hostl": "hostel",
    "canteeen": "canteen", "cantten": "canteen", "cantin": "canteen",
    "libary": "library", "libraray": "library",
    "bathrrom": "bathroom", "bathrom": "bathroom",
    "wshroom": "washroom",
    "drinkin": "drinking", "drnking": "drinking",
    "wateer": "water", "wter": "water",
    "foood": "food", "fod": "food",
    # Misc
    "dept": "department", "dep": "department",
    "govt": "government", "mgmt": "management",
    "cctv": "CCTV camera", "cc camera": "CCTV camera",
    "gen": "general",
    "bc": "because", "bcoz": "because",
    "abt": "about", "thru": "through",
    "govt": "government",
}

# ── Merge all into single dict ────────────────────────────────────────────────
ALL_ALIASES = {}
ALL_ALIASES.update(COMPLAINT_ALIASES)
ALL_ALIASES.update(FACILITY_ALIASES)
ALL_ALIASES.update(ROLE_ALIASES)
# Department aliases kept separate — used for dept detection, not text expansion


def normalize_complaint_text(text: str) -> str:
    """
    Expand shortforms, fix typos, and normalize campus-specific terms.
    - Lowercases input
    - Matches longer phrases first (sorted by length descending)
    - Whole-word match only via \\b regex
    """
    result = text.lower()

    # Sort by key length descending so longer phrases match first
    sorted_aliases = sorted(ALL_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)

    for short, full in sorted_aliases:
        # Whole-word boundary match, case-insensitive
        pattern = r'\b' + re.escape(short) + r'\b'
        result = re.sub(pattern, full, result, flags=re.IGNORECASE)

    return result


def detect_department_from_text(text: str) -> str | None:
    """
    Detect target department code from complaint text using aliases.
    Returns department code (e.g., "ECE") or None if not detected.
    Matches longer phrases first.
    """
    text_lower = text.lower()

    # Sort by key length descending
    sorted_dept = sorted(DEPARTMENT_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)

    for alias, dept_code in sorted_dept:
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower, flags=re.IGNORECASE):
            return dept_code

    return None
