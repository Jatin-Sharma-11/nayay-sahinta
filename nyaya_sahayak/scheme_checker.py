"""
Government scheme eligibility checker for Nyaya-Sahayak.
Matches user profile to relevant central/state government schemes using LangExtract + LLM.
"""

from __future__ import annotations
import sys, json
from pathlib import Path
from typing import Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from nyaya_sahayak.config import SCHEMES_JSON_PATH
from nyaya_sahayak.llm_client import chat

# ── Scheme Database ─────────────────────────────────────────────────────────────
BUILT_IN_SCHEMES = [
    {"id":"PM_AWAS","name":"PM Awas Yojana (PMAY)","hindi_name":"प्रधानमंत्री आवास योजना",
     "category":"Housing","ministry":"MoHUA",
     "description":"Affordable housing for urban/rural poor. Subsidy on home loans.",
     "eligibility":{"income_max_lpa":18,"age_min":18,"beneficiary":"EWS/LIG/MIG families","asset":"No pucca house"},
     "benefit":"Subsidy up to ₹2.67 lakh on home loan","url":"https://pmaymis.gov.in"},
    {"id":"MGNREGS","name":"MGNREGA","hindi_name":"मनरेगा",
     "category":"Employment","ministry":"MoRD",
     "description":"100 days guaranteed wage employment per year for rural households.",
     "eligibility":{"age_min":18,"location":"Rural","work_type":"Manual labour"},
     "benefit":"100 days employment @ ₹220-350/day (state-wise)","url":"https://nrega.nic.in"},
    {"id":"PM_JAN","name":"PM Jan Dhan Yojana","hindi_name":"प्रधानमंत्री जन धन योजना",
     "category":"Banking","ministry":"MoF",
     "description":"Zero-balance bank account with RuPay debit card and ₹2 lakh accident insurance.",
     "eligibility":{"age_min":10,"documents":"Aadhaar/PAN/Voter ID"},
     "benefit":"Free bank account + ₹2L accident cover + ₹30K life cover","url":"https://pmjdy.gov.in"},
    {"id":"AYUSHMAN","name":"Ayushman Bharat PM-JAY","hindi_name":"आयुष्मान भारत",
     "category":"Health","ministry":"MoHFW",
     "description":"Health insurance cover of ₹5 lakh per family per year for secondary/tertiary care.",
     "eligibility":{"income_max_lpa":2.5,"secc":"Listed in SECC 2011 database","family_size":"Any"},
     "benefit":"₹5 lakh/family/year health cover at empanelled hospitals","url":"https://pmjay.gov.in"},
    {"id":"PM_KISAN","name":"PM Kisan Samman Nidhi","hindi_name":"पीएम किसान",
     "category":"Agriculture","ministry":"MoA",
     "description":"Direct income support of ₹6,000/year to small and marginal farmers.",
     "eligibility":{"occupation":"Farmer","land_holding_max_acres":5,"documents":"Land record + Aadhaar"},
     "benefit":"₹6,000/year in 3 instalments","url":"https://pmkisan.gov.in"},
    {"id":"NIRBHAYA","name":"Nirbhaya Fund Schemes","hindi_name":"निर्भया फंड",
     "category":"Women Safety","ministry":"MoWCD",
     "description":"Multiple schemes for safety, rehabilitation of women survivors of violence.",
     "eligibility":{"gender":"Female","situation":"Survivor of sexual/domestic violence"},
     "benefit":"Legal aid, rehabilitation, one-stop centres, helpline 181","url":"https://wcd.nic.in"},
    {"id":"SAKSHAM","name":"Saksham Yojana (Divyang)","hindi_name":"सक्षम योजना",
     "category":"Disability","ministry":"MoSJE",
     "description":"Scholarship and assistance for differently-abled students.",
     "eligibility":{"disability_pct_min":40,"age_max":25,"education":"Post-matric"},
     "benefit":"Scholarship ₹3,500-₹38,500/year based on course","url":"https://scholarships.gov.in"},
    {"id":"PM_MUDRA","name":"PM MUDRA Yojana","hindi_name":"मुद्रा योजना",
     "category":"MSME/Business","ministry":"MoF",
     "description":"Collateral-free loans for small businesses and entrepreneurs.",
     "eligibility":{"business_type":"Non-farm enterprise","loan_max_lakh":20},
     "benefit":"Loans: Shishu (≤50K), Kishore (50K-5L), Tarun (5L-20L)","url":"https://mudra.org.in"},
    {"id":"SUKANYA","name":"Sukanya Samriddhi Yojana","hindi_name":"सुकन्या समृद्धि योजना",
     "category":"Girl Child","ministry":"MoF",
     "description":"Savings scheme for girl child with higher interest rate and tax benefits.",
     "eligibility":{"gender":"Female","age_max":10},
     "benefit":"8.2% interest, tax-free, maturity at age 21","url":"https://ssymis.gov.in"},
    {"id":"UJJWALA","name":"PM Ujjwala Yojana","hindi_name":"उज्ज्वला योजना",
     "category":"LPG/Energy","ministry":"MoPNG",
     "description":"Free LPG connection to women from BPL households.",
     "eligibility":{"gender":"Female","income":"BPL household","no_lpg":True},
     "benefit":"Free LPG connection + first cylinder","url":"https://pmuy.gov.in"},
    {"id":"SCHOLARSHIP_SC","name":"Post-Matric Scholarship (SC/ST)","hindi_name":"अनुसूचित जाति/जनजाति छात्रवृत्ति",
     "category":"Education","ministry":"MoSJE/MoTA",
     "description":"Scholarship for SC/ST students pursuing post-matric education.",
     "eligibility":{"caste":"SC or ST","income_max_lpa":2.5,"education":"Post-matric"},
     "benefit":"Full tuition + maintenance allowance","url":"https://scholarships.gov.in"},
    {"id":"LEGAL_AID","name":"National Legal Services Authority (NALSA)","hindi_name":"राष्ट्रीय विधिक सेवा प्राधिकरण",
     "category":"Legal Aid","ministry":"MoLJ",
     "description":"Free legal services to marginalized citizens.",
     "eligibility":{"any":["SC/ST","Woman","Child","Disabled","Income below ₹3L/year","Victim of disaster/trafficking"]},
     "benefit":"Free lawyer, legal advice, Lok Adalat access","url":"https://nalsa.gov.in"},
]


class SchemeChecker:
    """Match user profile to government schemes."""

    def __init__(self):
        self.schemes = []

    def load(self) -> "SchemeChecker":
        if SCHEMES_JSON_PATH.exists():
            self.schemes = json.loads(SCHEMES_JSON_PATH.read_text(encoding="utf-8"))
        else:
            self.schemes = BUILT_IN_SCHEMES
            SCHEMES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            SCHEMES_JSON_PATH.write_text(json.dumps(BUILT_IN_SCHEMES, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Schemes] Loaded {len(self.schemes)} schemes")
        return self

    # ── Rule-Based Pre-filter ───────────────────────────────────────────────────

    def _rule_match_score(self, scheme: dict, profile: dict) -> int:
        """Simple rule-based scoring (higher = better match)."""
        score = 0
        el = scheme.get("eligibility", {})

        age = int(profile.get("age", 99))
        income = float(profile.get("annual_income_lpa", 999))
        gender = profile.get("gender", "").lower()
        occupation = profile.get("occupation", "").lower()
        caste = profile.get("caste", "").lower()
        location = profile.get("location", "").lower()
        has_disability = profile.get("has_disability", False)
        is_survivor = profile.get("is_violence_survivor", False)
        needs_legal_aid = profile.get("needs_legal_aid", False)
        is_student = profile.get("is_student", False)
        has_land = profile.get("has_agricultural_land", False)
        is_entrepreneur = profile.get("is_entrepreneur", False)
        has_girl_child = profile.get("has_girl_child", False)
        is_bpl = profile.get("is_bpl", False)
        no_lpg = profile.get("no_lpg", False)

        # Income check
        if "income_max_lpa" in el and income <= el["income_max_lpa"]: score += 3
        # Age check
        if "age_min" in el and age >= el["age_min"]: score += 1
        if "age_max" in el and age <= el["age_max"]: score += 1
        # Gender
        if "gender" in el:
            if el["gender"].lower() == gender: score += 3
        # Occupation
        if "occupation" in el and el["occupation"].lower() in occupation: score += 3
        # Caste
        if "caste" in el:
            el_caste = el["caste"].lower()
            if "sc" in el_caste and "sc" in caste: score += 4
            if "st" in el_caste and "st" in caste: score += 4
        # Location
        if "location" in el and el["location"].lower() in location: score += 2
        # Disability
        if has_disability and scheme["category"] == "Disability": score += 5
        # Violence survivor
        if is_survivor and scheme["category"] == "Women Safety": score += 5
        # Legal aid
        if needs_legal_aid and scheme["category"] == "Legal Aid": score += 5
        # Student
        if is_student and scheme["category"] == "Education": score += 3
        # Farmer
        if has_land and scheme["category"] == "Agriculture": score += 4
        # Entrepreneur
        if is_entrepreneur and scheme["category"] == "MSME/Business": score += 4
        # Girl child
        if has_girl_child and scheme["category"] == "Girl Child": score += 5
        # BPL
        if is_bpl and scheme["category"] == "LPG/Energy" and no_lpg: score += 5
        if is_bpl: score += 1  # Small bonus for BPL across schemes
        # NALSA any-match
        if "any" in el:
            for cond in el["any"]:
                cond_l = cond.lower()
                if ("sc" in cond_l and "sc" in caste) or ("st" in cond_l and "st" in caste): score += 3; break
                if "woman" in cond_l and "f" in gender: score += 3; break
                if "child" in cond_l and age < 18: score += 3; break
                if "disabled" in cond_l and has_disability: score += 3; break

        return score

    # ── Main Eligibility Check ──────────────────────────────────────────────────

    def check_eligibility(self, profile: dict, language: str = "en") -> dict:
        """
        Match profile to schemes. Returns top matches + LLM explanation.
        
        Profile keys (all optional):
          age, annual_income_lpa, gender, caste, location (urban/rural),
          occupation, is_student, has_disability, is_violence_survivor,
          needs_legal_aid, has_agricultural_land, is_entrepreneur,
          has_girl_child, is_bpl, no_lpg
        """
        scored = []
        for scheme in self.schemes:
            score = self._rule_match_score(scheme, profile)
            if score > 0:
                scored.append({**scheme, "_score": score})

        scored.sort(key=lambda x: x["_score"], reverse=True)
        top_matches = scored[:5]  # Top 5

        # Build LLM explanation
        profile_str = json.dumps({k: v for k, v in profile.items() if v}, ensure_ascii=False)
        schemes_str = "\n".join([f"- {s['name']}: {s['benefit']}" for s in top_matches]) or "None found"

        if language == "hi":
            prompt = f"""उपयोगकर्ता की प्रोफ़ाइल: {profile_str}

मिलान की गई सरकारी योजनाएं:
{schemes_str}

कृपया इन योजनाओं के बारे में सरल हिंदी में बताएं और आवेदन कैसे करें यह भी समझाएं।"""
        else:
            prompt = f"""User profile: {profile_str}

Matched government schemes:
{schemes_str}

Explain these schemes in simple language and how the user can apply. 
Mention any documents they may need."""

        explanation = chat([{"role": "user", "content": prompt}], language=language, max_tokens=600)

        return {
            "matched_schemes": top_matches,
            "total_matched": len(scored),
            "explanation": explanation,
            "profile": profile,
        }

    def get_categories(self) -> list[str]:
        return sorted(set(s["category"] for s in self.schemes))


# ── Singleton ────────────────────────────────────────────────────────────────────
_checker: Optional[SchemeChecker] = None

def get_checker() -> SchemeChecker:
    global _checker
    if _checker is None:
        _checker = SchemeChecker().load()
    return _checker


if __name__ == "__main__":
    checker = get_checker()
    result = checker.check_eligibility({
        "age": 25, "gender": "female", "annual_income_lpa": 1.5,
        "caste": "SC", "location": "rural", "is_student": True
    })
    for s in result["matched_schemes"]:
        print(f"[{s['_score']}] {s['name']}: {s['benefit']}")
