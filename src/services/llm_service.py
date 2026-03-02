"""
LLM service for Groq API integration.
Handles complaint categorization, rephrasing, spam detection, etc.
"""

import logging
import json
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from groq import Groq
from src.config.settings import settings
from src.config.constants import CATEGORIES, MIN_COMPLAINT_LENGTH

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations using Groq API"""

    def __init__(self):
        """Initialize LLM service with Groq client.

        Gracefully handles missing GROQ_API_KEY by setting client to None.
        All LLM methods fall back to keyword-based logic when the client
        is unavailable.
        """
        self.groq_client = None
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

        api_key = settings.GROQ_API_KEY
        if api_key and api_key.strip():
            try:
                self.groq_client = Groq(api_key=api_key)
                logger.info(f"LLM Service initialized with model: {self.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}. LLM features will use fallback logic.")
        else:
            logger.warning("GROQ_API_KEY is not set. LLM features will use keyword-based fallback logic.")
    
    # ==================== CATEGORIZATION ====================
    
    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError))
    )
    async def categorize_complaint(
        self,
        text: str,
        context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Categorize complaint using LLM.
        
        Args:
            text: Complaint text
            context: Student context (gender, stay_type, department)
        
        Returns:
            Dictionary with category, priority, reasoning
        """
        if not text or len(text.strip()) < MIN_COMPLAINT_LENGTH:
            logger.warning("Text too short for categorization")
            return self._fallback_categorization(text, context)

        if not self.groq_client:
            logger.info("Groq client unavailable, using fallback categorization")
            return self._fallback_categorization(text, context)

        prompt = self._build_categorization_prompt(text, context)

        try:
            # ✅ FIXED: Use timezone-aware datetime
            start_time = datetime.now(timezone.utc)
            
            # Call Groq API (synchronous, so wrap in asyncio.to_thread)
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Parse response
            content = response.choices[0].message.content
            
            # Try to extract JSON from response
            result = self._extract_json_from_response(content)
            
            if not result:
                logger.warning("Failed to parse LLM response as JSON, using fallback")
                return self._fallback_categorization(text, context)
            
            # Validate result
            if not self._validate_categorization_result(result):
                logger.warning("Invalid categorization result, using fallback")
                return self._fallback_categorization(text, context)

            # Ensure target_department is present (fallback to student's department)
            if "target_department" not in result or not result["target_department"]:
                result["target_department"] = context.get("department", "CSE")
                logger.info(f"No target_department in LLM response, using student's department: {result['target_department']}")

            # Ensure confidence is present
            if "confidence" not in result:
                result["confidence"] = 0.8  # Default confidence for successful LLM response

            # Add metadata
            result["tokens_used"] = response.usage.total_tokens
            result["processing_time_ms"] = int(processing_time)
            result["model"] = self.model
            result["status"] = "Success"

            # Deterministic overrides (applied in order):
            # 1. Hostel → Department if academic content detected
            result = self._apply_academic_override(text, result)
            # 2. Department → General if physical repair of shared resource
            result = self._apply_repair_general_override(text, result)

            logger.info(
                f"Categorization successful: {result['category']} "
                f"(Priority: {result['priority']}, Target Dept: {result['target_department']}, "
                f"Confidence: {result.get('confidence', 'N/A')}, Tokens: {result['tokens_used']})"
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return self._fallback_categorization(text, context)
        except Exception as e:
            logger.error(f"LLM categorization error: {e}")
            return self._fallback_categorization(text, context)
    
    def _build_categorization_prompt(self, text: str, context: Dict[str, str]) -> str:
        """
        Build prompt for categorization with department detection.

        Student metadata (gender, stay_type, department) is passed as SUPPLEMENTARY
        context but the LLM is explicitly instructed to treat complaint text as the
        PRIMARY signal. Metadata is only a tie-breaker for genuinely ambiguous text —
        never an override when the complaint content is clear.
        """
        department_names = (
            "Computer Science & Engineering (CSE), "
            "Electronics & Communication Engineering (ECE), "
            "Robotics and Automation (RAA), "
            "Mechanical Engineering (MECH), "
            "Electrical & Electronics Engineering (EEE), "
            "Electronics & Instrumentation Engineering (EIE), "
            "Biomedical Engineering (BIO), "
            "Aeronautical Engineering (AERO), "
            "Civil Engineering (CIVIL), "
            "Information Technology (IT), "
            "Management Studies (MBA), "
            "Artificial Intelligence and Data Science (AIDS), "
            "M.Tech in Computer Science and Engineering (MTECH_CSE), "
            "English (ENG), "
            "Physics (PHY), "
            "Chemistry (CHEM), "
            "Mathematics (MATH)"
        )

        # Build supplementary context block from whatever is available
        student_gender = context.get("gender", "")
        student_stay = context.get("stay_type", "")
        student_dept = context.get("department", "")
        supplementary_lines = []
        if student_gender:
            supplementary_lines.append(f"  • Student gender: {student_gender}")
        if student_stay:
            supplementary_lines.append(f"  • Student stay type: {student_stay}")
        if student_dept:
            supplementary_lines.append(f"  • Student department: {student_dept}")
        supplementary_block = "\n".join(supplementary_lines) if supplementary_lines else "  (not provided)"

        return f"""You are a complaint routing system at SREC engineering college.

PRIMARY RULE — Use the complaint TEXT as your main signal:
Categorise based on what the complaint is ABOUT, not on who submitted it.
A hostel student complaining about a classroom → Department/General, NOT hostel.
A day scholar complaining about mess food → Men's Hostel or Women's Hostel (text-driven).

SUPPLEMENTARY CONTEXT (use ONLY as a tie-breaker when complaint text is ambiguous):
{supplementary_block}

HOW TO USE SUPPLEMENTARY CONTEXT:
✅ USE IT when the complaint text alone is genuinely ambiguous — e.g. student says "the mess food
   is bad" without naming a hostel → use gender to determine Men's vs Women's Hostel.
✅ USE IT when the complaint mentions "my department lab" without naming the department → use
   student's department code to fill in the target_department field.
✅ USE IT when the complaint says "our hostel" without specifying gender → use student gender.
❌ NEVER use it to override clear textual evidence. If a hostel student says "the projector
   in the CSE lab is broken", classify as Department regardless of their stay_type.
❌ NEVER default to hostel just because the student is a hostel resident.
❌ NEVER default to the student's own department just because they are in that department —
   only use the department list to detect if the complaint names a specific department.

Complaint text:
"{text}"

Available departments: {department_names}

ROUTING DECISION — follow steps in order, stop at first match:

STEP 1 — Check for STUDENT BEHAVIORAL MISCONDUCT → "Disciplinary Committee":
Does the complaint describe ANY of:
• Violence/threats: ragging, bullying, physical fight, assault, brawl, threatening, stalking, harassment, sexual harassment
• Serious academic dishonesty: cheating in exam, copying, malpractice, plagiarism, impersonation, proxy attendance
• Classroom/campus disturbance: disturbing class, disrupting lecture, causing nuisance in class, misbehaving in class, shouting in class, making noise in class
• Unauthorized activities in academic spaces: celebrating in class, birthday party in class, cutting cake in class, eating food in class, playing music in class, watching videos in class
• General indiscipline: violating college rules, dress code violation, using mobile phone in class without permission, sleeping in class disruptively, disrespecting faculty or staff
→ YES → Category = "Disciplinary Committee"

PRE-STEP — PHYSICAL REPAIR/DAMAGE OVERRIDE (check this FIRST before all other steps):
If the complaint describes PHYSICAL DAMAGE, MALFUNCTION, or REPAIR NEED for a SHARED CAMPUS RESOURCE:
Repair language: broken, not working, damaged, repair, maintenance, out of order, stopped working, faulty,
  defective, needs replacement, leaking, burst, no power, no electricity, no water, not functioning
Shared resources (always General): projector, AC, air conditioner, fan, ceiling fan, light, tube light,
  bulb, electricity, power outlet, water tap, water pipe, furniture, chair, table, door, window,
  toilet, bathroom, washroom, drinking water, cooler
→ If BOTH repair language AND shared resource keyword present → Category = "General"
→ EXCEPTION: If item is specifically a lab computer, desktop PC, workstation, server, oscilloscope,
  PCB, circuit board, embedded system, CNC machine, lathe — these are specialized dept equipment → use STEP 2.

STEP 2 — Check for ACADEMIC / DEPARTMENT issue → "Department":
Does the complaint mention a problem with ACADEMIC SERVICES, CURRICULUM, or SPECIALIZED LAB EQUIPMENT:
• Specialized lab equipment: oscilloscope, PCB lab, fabrication, CNC, embedded systems, circuit boards
• Lab computers (desktop PCs, workstations, specific academic software/IDE)
• Software license missing, IDE/software not working, compiler issues
• Faculty/HOD request, curriculum, timetable, project submission, department office service
• Academic: exam schedule, course registration, observation book, lab record
• Placement, internship, career guidance, campus recruitment, T&P cell, TCS NQT, AMCAT, aptitude,
  soft skills training, mock interviews, campus drives, coding interview prep
NOTE: General repair of shared infrastructure (projector, AC, fan, furniture) → use PRE-STEP override above.
NOTE: If the complaint is about STUDENT BEHAVIOR in these spaces, use STEP 1 instead.
→ YES → Category = "Department"

PLACEMENT/CAREER COMPLAINTS — CRITICAL RULE:
If complaint mentions placement, internship, T&P, campus recruitment, TCS NQT, AMCAT, aptitude,
mock interviews, coding interview, career guidance, campus drives, soft skills:
→ target_department = ALWAYS the student's OWN department from supplementary context
→ NEVER use AIDS unless the complaint text EXPLICITLY mentions "Artificial Intelligence" or "Data Science"
→ If no department context provided, use "CSE" as fallback

STEP 3 — Check for HOSTEL FACILITY → hostel category:
Is the issue about something physically INSIDE a hostel building?
Strong hostel indicators: "hostel", "hostel room", "hostel mess", "mess food", "hostel bathroom",
"hostel water", "hostel electricity", "hostel warden", "hostel corridor", "hostel gate",
"dorm", "boarding", "my room" (when student is a hostel resident and text clearly implies hostel context).

IMPORTANT RULES FOR HOSTEL CLASSIFICATION:
• The word "room" alone does NOT indicate a hostel complaint. "Room in block C" means
  a classroom or common area — classify as Department or General, NOT hostel.
• "AC", "fan", "lights" alone do NOT indicate hostel — they appear in classrooms too.
• These are NEVER hostel complaints even if reported by a hostel resident:
  - Lab equipment, classrooms, projectors, computers, academic facilities
  - Campus canteen (not mess), campus library, campus wifi, sports grounds
  - Outdoor trees, campus roads, drainage, campus grounds, open areas
  - Faculty/HOD issues, timetable, exams, curriculum

For hostel complaints, determine gender using this priority order:
1. Explicit mention in text: "men's hostel", "boys' hostel" → "Men's Hostel"; "women's hostel", "girls' hostel", "ladies' hostel" → "Women's Hostel"
2. No explicit gender in text → use student's gender from supplementary context (Male → "Men's Hostel", Female → "Women's Hostel")
3. No text mention and no supplementary context → default to "Men's Hostel"

STEP 4 — Campus-wide facility → "General":
All campus outdoor/infrastructure issues NOT inside a hostel building and NOT academic and NOT behavioral: fallen trees, campus roads/drainage, parking, sports courts/grounds, campus wifi/internet, auditorium, open drinking water stations, bus/transport, campus gates, campus canteen, campus library building, general campus cleanliness, streetlights, rooms/areas that are not in a hostel building.

DEPARTMENT DETECTION (when category = "Department"):
Valid codes: CSE, ECE, MECH, CIVIL, EEE, IT, BIO, AERO, RAA, EIE, MBA, AIDS, MTECH_CSE, ENG, PHY, CHEM, MATH
- If complaint names a specific dept/lab (e.g. "ECE lab", "CSE printer", "English class", "physics lab", "chemistry lab", "maths class") → use that dept code
- ENG: complaints about English subject, English class, English faculty, English department
- PHY: complaints about Physics subject, physics lab, physics class, physics faculty
- CHEM: complaints about Chemistry subject, chemistry lab, chemistry class, chemistry faculty
- MATH: complaints about Mathematics/Maths subject, math class, mathematics faculty
- If complaint says "my department" or "our department" without naming it → use student's department from supplementary context
- Placement/internship/T&P/TCS NQT/coding interview complaints → ALWAYS use the student's own department from supplementary context; NEVER use AIDS unless text explicitly mentions AI or Data Science (or "CSE" if no context)
- If no department context at all → use "CSE" as the default
- NEVER assign a department solely because the student belongs to it when the complaint is about a different area

PRIORITY:
- Critical: immediate safety danger, violence, or injury risk
- High: many students affected, exam disrupted, key facility completely down
- Medium: moderate disruption to a subset of students or repeated behavioral issue
- Low: minor inconvenience or first-time minor behavioural issue

Respond ONLY with valid JSON (no markdown, no code blocks):
{{
  "category": "Men's Hostel|Women's Hostel|General|Department|Disciplinary Committee",
  "target_department": "CSE|ECE|MECH|CIVIL|EEE|IT|BIO|AERO|RAA|EIE|MBA|AIDS|MTECH_CSE|ENG|PHY|CHEM|MATH",
  "priority": "Low|Medium|High|Critical",
  "reasoning": "Max 40 words",
  "confidence": 0.0-1.0,
  "is_against_authority": false,
  "requires_image": false
}}

JSON:"""
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response (handles markdown code blocks)"""
        try:
            # Try direct JSON parse first
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            
            # Remove markdown code blocks
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            match = re.search(json_pattern, content, re.DOTALL)
            
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object in text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            match = re.search(json_pattern, content, re.DOTALL)
            
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            
            return None
    
    def _validate_categorization_result(self, result: Dict[str, Any]) -> bool:
        """Validate categorization result structure"""
        required_fields = ["category", "priority"]
        
        if not all(field in result for field in required_fields):
            return False
        
        valid_categories = ["Men's Hostel", "Women's Hostel", "General", "Department", "Disciplinary Committee"]
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        
        if result["category"] not in valid_categories:
            return False
        
        if result["priority"] not in valid_priorities:
            return False
        
        return True
    
    # Keywords that unambiguously indicate an academic/department issue.
    # If the LLM returns a hostel category but the text contains any of these,
    # we override to "Department" — this is deterministic and safe because these
    # phrases never appear in genuine hostel complaints.
    # NOTE: "projector" removed — a broken projector is a General repair issue, not Department.
    _ACADEMIC_OVERRIDE_KEYWORDS = [
        "lab ",       " lab",        "labs ",       "laboratory",
        "computer lab","cse lab",     "ece lab",     "it lab",
        "eee lab",    "mech lab",    "bio lab",     "aero lab",
        "seminar hall","lecture hall","classroom",
        "department office", "dept office",
        "faculty",    "professor",   " hod ",       "head of department",
        "lab record", "observation book", "lab observation",
        "project report", "project submission",
        "timetable",  "exam schedule", "course",    "curriculum",
        "software license", "software licence", "ide software",
        "av system",  "av technician",
        "server room","computing cluster", "lab in-charge",
        "oscilloscope","pcb ",        "fabrication lab", "workshop",
        "practicals", "practical exam",
        "printer" ,   "printing",
    ]

    # Physical repair keywords — if present alongside shared resource, override to General
    _REPAIR_KEYWORDS = [
        "broken", "not working", "not functioning", "damaged", "repair", "maintenance",
        "out of order", "stopped working", "faulty", "defective", "needs replacement",
        "need replacement", "leaking", "burst pipe", "no power", "no electricity",
        "power cut", "no water", "isn't working", "doesn't work", "not fixed",
        "still broken", "has been broken", "require repair", "requires repair",
    ]

    # Shared campus resources — repair of these → General (not Department)
    # Plain keywords matched as substrings (long enough to be unambiguous)
    _SHARED_RESOURCE_KEYWORDS = [
        "projector", "air conditioner", "air conditioning",
        "ceiling fan", "tube light", "fluorescent light", "bulb",
        "power outlet", "socket", "extension cord", "water tap", "water pipe",
        "pipe burst", "furniture", "toilet", "washroom", "bathroom", "urinal",
        "drinking water", "water cooler", "whiteboard", "blackboard",
    ]
    # Short words that need word-boundary matching (avoid false hits like "tab", "fan belt")
    _SHARED_RESOURCE_PATTERNS = [
        r"\bac\b", r"\bfan\b", r"\btap\b", r"\bchair\b", r"\bchairs\b",
        r"\btable\b", r"\btables\b", r"\bdoor\b", r"\bwindow\b", r"\bcooler\b",
    ]

    def _apply_repair_general_override(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        If the LLM returned 'Department' but the complaint is actually about
        physical repair/damage of shared campus infrastructure, override to 'General'.

        A broken projector, faulty AC, or damaged furniture is a campus maintenance
        issue (General), not a department academic issue, even if mentioned in a lab context.
        Exception: specialized lab equipment (computers, oscilloscopes, PCBs) stays Department.
        """
        import re as _re
        if result.get("category") != "Department":
            return result

        text_lower = text.lower()

        has_repair = any(kw in text_lower for kw in self._REPAIR_KEYWORDS)
        if not has_repair:
            return result

        has_shared_resource = (
            any(kw in text_lower for kw in self._SHARED_RESOURCE_KEYWORDS)
            or any(_re.search(pat, text_lower) for pat in self._SHARED_RESOURCE_PATTERNS)
        )
        if not has_shared_resource:
            return result

        result["category"] = "General"
        logger.info(
            "Repair override: 'Department' → 'General' "
            "(physical repair of shared resource detected)"
        )
        return result

    def _apply_academic_override(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic post-processing override.
        If the LLM returned a hostel category but the complaint text contains
        strong academic/department-facility keywords, reclassify as Department.
        This catches the common model bias where male/female hostel students get
        their academic lab/classroom complaints routed to hostel.
        """
        if result.get("category") not in ("Men's Hostel", "Women's Hostel"):
            return result   # Only override hostel mis-classifications

        text_lower = text.lower()
        for kw in self._ACADEMIC_OVERRIDE_KEYWORDS:
            if kw in text_lower:
                original = result["category"]
                result["category"] = "Department"
                logger.info(
                    f"Academic override: '{original}' → 'Department' "
                    f"(triggered by keyword '{kw.strip()}')"
                )
                break
        return result

    def _fallback_categorization(self, text: str, context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fallback categorization using keyword matching with student context and department detection"""
        text_lower = text.lower()

        # Keyword-based categorization
        category_keywords = {
            "Hostel": ["hostel", "hostel room", "mess food", "mess hall", "warden", "dorm", "hostel bathroom", "hostel water", "hostel block", "hostel corridor", "hostel gate"],
            "Department": ["lab", "classroom", "department", "academic", "faculty", "professor", "teacher", "lecture", "course", "exam", "lab equipment"],
            "Disciplinary Committee": ["ragging", "harassment", "bullying", "threat", "abuse", "assault", "violence", "discrimination", "disturbing class", "misbehaving", "indiscipline"],
            "General": ["canteen", "library", "playground", "ground", "parking", "transport", "bus", "wifi", "internet", "campus", "infrastructure", "tree", "road", "drainage", "streetlight", "gate"]
        }

        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score

        # Select category with highest score
        if category_scores:
            selected_category = max(category_scores, key=category_scores.get)
        else:
            selected_category = "General"

        # Map generic "Hostel" keyword match to a gender-specific hostel category.
        # Priority: (1) explicit gender words in text, (2) student's gender from context,
        # (3) default to Men's Hostel.
        if selected_category == "Hostel":
            text_lower_check = text.lower()
            if any(w in text_lower_check for w in ["women", "women's", "girls", "ladies", "female"]):
                selected_category = "Women's Hostel"
            elif any(w in text_lower_check for w in ["men", "men's", "boys", "male", "gents"]):
                selected_category = "Men's Hostel"
            elif context and context.get("gender", "").lower() in ("female", "f"):
                selected_category = "Women's Hostel"
            else:
                selected_category = "Men's Hostel"

        # ✅ NEW: Department detection using keywords
        department_keywords = {
            "CSE": ["cse", "computer science", "computer lab", "cs department"],
            "ECE": ["ece", "electronics", "communication", "ec department"],
            "MECH": ["mech", "mechanical", "workshop", "machine"],
            "CIVIL": ["civil", "construction", "surveying"],
            "EEE": ["eee", "electrical", "power", "circuits"],
            "IT": ["it", "information technology", "it lab"],
            "BIO": ["bio", "biomedical", "biomed"],
            "AERO": ["aero", "aeronautical", "aerospace"],
            "RAA": ["raa", "robotics", "automation"],
            "EIE": ["eie", "instrumentation"],
            "MBA": ["mba", "management"],
            "AIDS": ["aids", "ai", "data science", "artificial intelligence"],
            "MTECH_CSE": ["mtech", "m.tech"],
            "ENG": ["english", "english class", "english subject", "english faculty", "english department", "english teacher", "english professor"],
            "PHY": ["physics", "physics lab", "physics class", "physics subject", "physics faculty", "physics teacher"],
            "CHEM": ["chemistry", "chemistry lab", "chemistry class", "chem lab", "chemistry subject", "chemistry faculty"],
            "MATH": ["mathematics", "maths", "math class", "math subject", "mathematics faculty", "math teacher"],
        }

        # Detect target department from complaint text
        detected_department = None
        for dept_code, keywords in department_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_department = dept_code
                break

        # Fallback to student's department if no department detected
        target_department = detected_department or (context.get("department", "CSE") if context else "CSE")

        # Determine priority based on urgency keywords
        urgency_keywords = {
            "Critical": ["emergency", "urgent", "immediate", "critical", "dangerous", "unsafe"],
            "High": ["broken", "not working", "damaged", "leaking", "problem"],
            "Medium": ["issue", "concern", "needs", "improve"],
            "Low": ["suggestion", "request", "minor"]
        }

        selected_priority = "Medium"
        for priority, keywords in urgency_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                selected_priority = priority
                break

        fallback_result = {
            "category": selected_category,
            "target_department": target_department,
            "priority": selected_priority,
            "reasoning": "Keyword-based categorization (LLM fallback)",
            "confidence": 0.5,  # Lower confidence for fallback
            "is_against_authority": any(word in text_lower for word in ["faculty", "teacher", "professor", "staff", "warden", "hod"]),
            "requires_image": any(word in text_lower for word in ["broken", "damaged", "leaking", "dirty"]),
            "status": "Fallback"
        }

        # Apply same deterministic academic override to fallback path
        fallback_result = self._apply_academic_override(text, fallback_result)

        logger.info(
            f"Fallback categorization: {fallback_result['category']} (Priority: {selected_priority}, "
            f"Target Dept: {target_department})"
        )
        return fallback_result
    
    # ==================== REPHRASING ====================
    
    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError))
    )
    async def rephrase_complaint(self, text: str) -> Optional[str]:
        """
        Rephrase complaint to be professional and clear.

        Bug 3 fix: Returns None if the text appears to be gibberish/meaningless,
        so the caller can treat it as a spam indicator and stop processing.
        Returns the original text (not None) if the Groq client is unavailable.

        Args:
            text: Original complaint text

        Returns:
            Rephrased text string, or None if text is gibberish/meaningless
        """
        if not text or len(text.strip()) < 10:
            logger.warning("Text too short for rephrasing, returning original")
            return text

        if not self.groq_client:
            logger.info("Groq client unavailable, skipping rephrasing")
            return text

        prompt = self._build_rephrasing_prompt(text)

        try:
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower for more consistent rephrasing
                max_tokens=200,
                timeout=self.timeout
            )

            rephrased = response.choices[0].message.content.strip()

            # Remove any markdown formatting
            rephrased = rephrased.replace("**", "").replace("*", "")

            # Bug 3 fix: If the LLM signals gibberish/no-content (returns the
            # sentinel "GIBBERISH" or empty/too-short output), return None so the
            # submission pipeline can reject the complaint as spam.
            if rephrased.upper().startswith("GIBBERISH") or rephrased.upper().startswith("NO_CONTENT"):
                logger.warning(f"Rephraser detected gibberish input for text: {text[:60]!r}")
                return None

            # If rephrased text is too short or looks invalid, return original
            if len(rephrased) < 20 or rephrased.startswith("Error"):
                logger.warning("Rephrased text looks invalid, returning original")
                return text

            logger.info(f"Rephrasing successful (Original: {len(text)} chars → Rephrased: {len(rephrased)} chars)")
            return rephrased

        except Exception as e:
            logger.error(f"LLM rephrasing error: {e}")
            return text  # Return original if rephrasing fails

    def _build_rephrasing_prompt(self, text: str) -> str:
        """Build prompt for rephrasing.

        Bug 3 fix: Adds explicit instructions to return the sentinel 'GIBBERISH'
        instead of inventing content when the input has no coherent meaning.
        """
        return f"""Rephrase this student complaint into 1-2 short, clear sentences. Keep the original meaning intact.

Original:
"{text}"

IMPORTANT — Gibberish guard:
If the text has NO coherent meaning (random characters, keyboard mashing, meaningless word
sequences with no identifiable issue), respond with exactly: GIBBERISH
Do NOT invent or fabricate a complaint from meaningless input.

Rules (when text IS a real complaint):
- Output 1-2 concise sentences ONLY (max 50 words)
- Preserve the core issue and key details
- Fix grammar and spelling
- Keep it natural and professional
- Do NOT add new information
- Do NOT use bullet points or structured format
- Do NOT start with "The student" or "I would like to"

Provide ONLY the rephrased text (or GIBBERISH if applicable):"""
    
    # ==================== SPAM DETECTION ====================
    
    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError))
    )
    async def detect_spam(self, text: str) -> Dict[str, Any]:
        """
        Detect if complaint is spam or abusive.
        
        Args:
            text: Complaint text
        
        Returns:
            Dictionary with is_spam, confidence, reason
        """
        # Quick checks first
        if len(text.strip()) < MIN_COMPLAINT_LENGTH:
            return {
                "is_spam": True,
                "confidence": 1.0,
                "reason": f"Complaint too short (minimum {MIN_COMPLAINT_LENGTH} characters required)"
            }
        
        # Check for test/dummy content
        test_phrases = ["test", "testing", "asdf", "qwerty", "dummy", "sample"]
        if any(phrase in text.lower() for phrase in test_phrases) and len(text) < 50:
            return {
                "is_spam": True,
                "confidence": 0.9,
                "reason": "Appears to be test/dummy content"
            }
        
        if not self.groq_client:
            logger.info("Groq client unavailable, skipping LLM spam detection (assuming not spam)")
            return {
                "is_spam": False,
                "confidence": 0.5,
                "reason": "LLM unavailable, skipping spam detection"
            }

        prompt = self._build_spam_detection_prompt(text)

        try:
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower for more consistent detection
                max_tokens=200,
                timeout=self.timeout
            )
            
            content = response.choices[0].message.content
            result = self._extract_json_from_response(content)
            
            if not result or "is_spam" not in result:
                logger.warning("Invalid spam detection response, assuming not spam")
                return {
                    "is_spam": False,
                    "confidence": 0.5,
                    "reason": "Unable to determine (invalid response)"
                }
            
            logger.info(f"Spam detection: {result['is_spam']} (Confidence: {result.get('confidence', 'N/A')})")
            return result
            
        except Exception as e:
            logger.error(f"Spam detection error: {e}")
            # Default to not spam on error (better UX than blocking legitimate complaints)
            return {
                "is_spam": False,
                "confidence": 0.5,
                "reason": "Unable to determine (API error)"
            }
    
    def _build_spam_detection_prompt(self, text: str) -> str:
        """Build prompt for spam detection.

        Bug 3 fix: Explicitly instructs the LLM to flag gibberish/random text as
        spam rather than treating it as a complaint with meaning.
        """
        return f"""Detect if this complaint is spam, abusive, meaningless, or not genuine.

Complaint Text:
"{text}"

SPAM — mark is_spam=true for ANY of these:
- Random characters, keyboard mashing (e.g. "asdfgh jkl qwert uiop")
- Gibberish: meaningless word sequences with no coherent subject or issue
- Text that has no identifiable complaint or problem being reported
- Abusive, profane, or offensive language
- Joke, prank, or clearly sarcastic complaint with no real issue
- Purely personal attacks targeting specific individuals by name with no campus issue
- Test or dummy content (e.g. "test", "asdf", "testing 123")
- Advertisement or promotional content
- Completely irrelevant to campus life (e.g. celebrity news, personal life unrelated to college)

IMPORTANT — gibberish rule:
If the text consists of random characters, meaningless sequences, keyboard mashing,
or words arranged with no coherent meaning or identifiable problem, mark is_spam=true
with reason="gibberish". A complaint must describe a real, identifiable issue.

NOT Spam (do NOT flag these):
- Complaints with spelling errors, typos, or grammatical mistakes — these are still valid
- Valid concerns expressed with frustration or informal/casual language
- Complaints mentioning authorities in a professional or complaint context
- Short complaints that still describe a real issue (e.g. "AC broken in lab")
- Complaints in mixed Tamil/English (code-switching) that describe a real issue

Respond ONLY with valid JSON (no markdown):
{{
  "is_spam": true|false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation (max 30 words)"
}}

JSON Response:"""
    
    # ==================== IMAGE VERIFICATION ====================
    
    async def verify_image_relevance(
        self,
        complaint_text: str,
        image_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify if image is relevant to complaint.
        
        NOTE: This is a basic heuristic implementation.
        For production, use the image_verification_service.py with Groq Vision API.
        
        Args:
            complaint_text: Complaint text
            image_description: Optional image description
        
        Returns:
            Dictionary with is_relevant, confidence, reason
        """
        if not image_description:
            return {
                "is_relevant": True,
                "confidence": 0.7,
                "reason": "No image description provided, accepting by default"
            }
        
        # Check if description relates to complaint
        text_lower = complaint_text.lower()
        desc_lower = image_description.lower()
        
        # Remove common stopwords
        stopwords = {"the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "with", "and", "or", "but"}
        text_words = set(text_lower.split()) - stopwords
        desc_words = set(desc_lower.split()) - stopwords
        
        # Find common meaningful words
        common_words = text_words & desc_words
        
        # Calculate relevance score
        if len(text_words) == 0:
            relevance_score = 0
        else:
            relevance_score = len(common_words) / len(text_words)
        
        is_relevant = relevance_score > 0.1 or len(common_words) >= 2
        
        confidence = min(relevance_score * 2, 1.0)
        if len(common_words) >= 3:
            confidence = max(confidence, 0.8)
        
        logger.info(f"Image relevance: {is_relevant} (Confidence: {confidence:.2f}, Common words: {len(common_words)})")
        
        return {
            "is_relevant": is_relevant,
            "confidence": confidence,
            "reason": f"Found {len(common_words)} common keywords between complaint and image description"
        }
    
    # ==================== IMAGE REQUIREMENT DETECTION ====================

    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError))
    )
    async def check_image_requirement(
        self,
        complaint_text: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determine if complaint requires image evidence using LLM.

        Args:
            complaint_text: Complaint text to analyze
            category: Optional category hint

        Returns:
            Dictionary with image_required, reasoning, confidence
        """
        if not complaint_text or len(complaint_text.strip()) < MIN_COMPLAINT_LENGTH:
            logger.warning("Text too short for image requirement check")
            return {
                "image_required": False,
                "reasoning": "Complaint text too short to analyze",
                "confidence": 0.5
            }

        if not self.groq_client:
            logger.info("Groq client unavailable, using fallback image requirement check")
            return self._fallback_image_requirement(complaint_text)

        prompt = self._build_image_requirement_prompt(complaint_text, category)

        try:
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower for more consistent decisions
                max_tokens=300,
                timeout=self.timeout
            )

            content = response.choices[0].message.content
            result = self._extract_json_from_response(content)

            if not result or "image_required" not in result:
                logger.warning("Invalid image requirement response, using fallback")
                return self._fallback_image_requirement(complaint_text)

            logger.info(
                f"Image requirement check: {result['image_required']} "
                f"(Confidence: {result.get('confidence', 'N/A')})"
            )
            return result

        except Exception as e:
            logger.error(f"Image requirement check error: {e}")
            return self._fallback_image_requirement(complaint_text)

    def _build_image_requirement_prompt(self, text: str, category: Optional[str]) -> str:
        """Build prompt for image requirement detection"""
        category_hint = f"\nCategory: {category}" if category else ""

        return f"""Determine if this complaint requires a photo/image for proper verification.

Complaint:
"{text}"{category_hint}

Image IS REQUIRED only for:
- Something physically broken or structurally damaged (broken furniture, cracked walls, burst pipes)
- Exposed electrical hazards (dangling wires, sparking sockets)
- Visible facility damage (broken doors/windows, large stains, visible mould, water leaking)

Image is NOT REQUIRED for:
- Pest/hygiene reports (rats sighted, cockroaches present, insects seen) — these are service requests; you cannot photograph pests on demand
- Absent or insufficient staff (no cleaning staff, guard absent, night duty not performed)
- Schedule or policy violations (timings changed, rules not followed, no notice given)
- Service failures (repairs not done despite reports, no response from management, equipment non-functional)
- Academic or interpersonal issues (faculty problems, exams, harassment, bullying, ragging)
- Complaints about waiting for action (already reported but not resolved)
- Any complaint describing a service failure, scheduling issue, or lack of action

DEFAULT: image_required = false unless the complaint explicitly describes visible structural damage that a photo would prove.
When uncertain, ALWAYS choose false — never block a legitimate complaint over an image.

Respond ONLY with valid JSON (no markdown):
{{
  "image_required": true|false,
  "reasoning": "Max 40 words",
  "confidence": 0.0-1.0,
  "suggested_evidence": "What to photograph (only if true, else null)"
}}

JSON:"""

    def _fallback_image_requirement(self, text: str) -> Dict[str, Any]:
        """Fallback logic for image requirement detection"""
        text_lower = text.lower()

        # Keywords that typically require visual evidence
        requires_image_keywords = [
            "broken", "damaged", "leaking", "leak", "dirty", "filthy", "stain",
            "crack", "torn", "not working", "malfunctioning", "defective",
            "unhygienic", "unclean", "blocked", "clogged", "rusty", "peeling",
            "exposed wire", "hanging", "falling", "detached", "missing",
            "visible", "see", "look", "show", "picture", "photo"
        ]

        # Count matches
        matches = sum(1 for keyword in requires_image_keywords if keyword in text_lower)

        # Determine if image is required
        image_required = matches >= 2  # At least 2 strong indicators
        confidence = min(0.5 + (matches * 0.1), 0.9)

        logger.info(
            f"Fallback image requirement: {image_required} "
            f"(Matches: {matches}, Confidence: {confidence:.2f})"
        )

        return {
            "image_required": image_required,
            "reasoning": f"Keyword-based analysis detected {matches} visual problem indicators" if image_required else "No strong visual evidence requirements detected",
            "confidence": confidence,
            "suggested_evidence": "Photo showing the issue clearly" if image_required else None
        }

    # ==================== UTILITY METHODS ====================

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get LLM service statistics and configuration.

        Returns:
            Service statistics
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "max_retries": settings.LLM_MAX_RETRIES,
            "status": "operational" if self.groq_client else "fallback_mode"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Groq API connection.

        Returns:
            Connection test result
        """
        if not self.groq_client:
            return {
                "status": "unavailable",
                "model": self.model,
                "message": "Groq client not initialized (API key missing or invalid)"
            }

        try:
            # Use timezone-aware datetime
            start_time = datetime.now(timezone.utc)

            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": "Reply with: OK"}],
                temperature=0,
                max_tokens=10,
                timeout=5
            )
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return {
                "status": "success",
                "model": self.model,
                "response_time_ms": int(response_time),
                "message": "Groq API connection successful"
            }
            
        except Exception as e:
            logger.error(f"Groq API connection test failed: {e}")
            return {
                "status": "error",
                "model": self.model,
                "message": f"Connection failed: {str(e)}"
            }


# Create global instance
llm_service = LLMService()

__all__ = ["LLMService", "llm_service"]
