"""
IPC ↔ BNS section comparator.
Provides scenario-based comparison and direct section number translation.
Uses PageIndex dual-query (BNS + IPC) + Sarvam-M for synthesis.
"""

from __future__ import annotations
import sys, re
from pathlib import Path
from typing import Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from nyaya_sahayak.config import IPC_BNS_MAPPING_PATH, ROOT
from nyaya_sahayak.llm_client import chat, compare_sections
from nyaya_sahayak.rag_engine import get_engine

# ── IPC→BNS Mapping Table ────────────────────────────────────────────────────────
# Comprehensive hand-crafted mapping (IPC section → BNS section)
_BUILTIN_MAPPING = [
    # Offences against life
    {"ipc_section":"299","ipc_name":"Culpable Homicide","bns_section":"100","bns_name":"Culpable Homicide","category":"Life","note":""},
    {"ipc_section":"300","ipc_name":"Murder","bns_section":"101","bns_name":"Murder","category":"Life","note":""},
    {"ipc_section":"302","ipc_name":"Punishment for Murder","bns_section":"103","bns_name":"Punishment for Murder","category":"Life","note":"New: group murder by caste/religion → death/life"},
    {"ipc_section":"304","ipc_name":"Culpable Homicide Not Murder","bns_section":"105","bns_name":"Culpable Homicide Not Amounting to Murder","category":"Life","note":""},
    {"ipc_section":"304A","ipc_name":"Death by Negligence","bns_section":"106","bns_name":"Causing Death by Negligence","category":"Life","note":"New: hit-and-run clause added (10 yr)"},
    {"ipc_section":"304B","ipc_name":"Dowry Death","bns_section":"80","bns_name":"Dowry Death","category":"Women","note":""},
    {"ipc_section":"306","ipc_name":"Abetment of Suicide","bns_section":"108","bns_name":"Abetment of Suicide","category":"Life","note":""},
    {"ipc_section":"307","ipc_name":"Attempt to Murder","bns_section":"109","bns_name":"Attempt to Murder","category":"Life","note":""},
    {"ipc_section":"309","ipc_name":"Attempt to Commit Suicide","bns_section":"REPEALED","bns_name":"Decriminalized","category":"Life","note":"Attempt to suicide decriminalized in BNS"},
    # Offences against women
    {"ipc_section":"354","ipc_name":"Assault on Woman (Modesty)","bns_section":"74","bns_name":"Assault/Criminal Force to Woman","category":"Women","note":""},
    {"ipc_section":"354A","ipc_name":"Sexual Harassment","bns_section":"75","bns_name":"Sexual Harassment","category":"Women","note":""},
    {"ipc_section":"354B","ipc_name":"Assault to Disrobe","bns_section":"76","bns_name":"Assault/Criminal Force to Disrobe","category":"Women","note":""},
    {"ipc_section":"354C","ipc_name":"Voyeurism","bns_section":"77","bns_name":"Voyeurism","category":"Women","note":""},
    {"ipc_section":"354D","ipc_name":"Stalking","bns_section":"78","bns_name":"Stalking","category":"Women","note":""},
    {"ipc_section":"375","ipc_name":"Rape (definition)","bns_section":"63","bns_name":"Rape","category":"Women","note":""},
    {"ipc_section":"376","ipc_name":"Punishment for Rape","bns_section":"64","bns_name":"Punishment for Rape","category":"Women","note":""},
    {"ipc_section":"376A","ipc_name":"Rape causing death","bns_section":"66","bns_name":"Death or PVS from Rape","category":"Women","note":""},
    {"ipc_section":"376B","ipc_name":"Sexual intercourse by husband (separation)","bns_section":"67","bns_name":"Sexual Intercourse by Husband During Separation","category":"Women","note":""},
    {"ipc_section":"376C","ipc_name":"Sexual intercourse by authority","bns_section":"68","bns_name":"Sexual Intercourse by Person in Authority","category":"Women","note":""},
    {"ipc_section":"376D","ipc_name":"Gang Rape","bns_section":"70","bns_name":"Gang Rape","category":"Women","note":""},
    {"ipc_section":"376E","ipc_name":"Repeat Rape Offender","bns_section":"71","bns_name":"Punishment for Repeat Offenders","category":"Women","note":""},
    {"ipc_section":"377","ipc_name":"Unnatural Offences","bns_section":"REPEALED","bns_name":"Decriminalized (consensual)","category":"Women","note":"Consensual same-sex relations decriminalized"},
    {"ipc_section":"498A","ipc_name":"Cruelty by Husband/Family","bns_section":"85","bns_name":"Cruelty by Husband/Relatives","category":"Women","note":""},
    {"ipc_section":"509","ipc_name":"Word/Gesture Insulting Modesty","bns_section":"79","bns_name":"Word/Gesture Insulting Modesty","category":"Women","note":""},
    # Property offences
    {"ipc_section":"378","ipc_name":"Theft","bns_section":"303","bns_name":"Theft","category":"Property","note":""},
    {"ipc_section":"379","ipc_name":"Punishment for Theft","bns_section":"303(2)","bns_name":"Punishment for Theft","category":"Property","note":""},
    {"ipc_section":"380","ipc_name":"Theft in Dwelling","bns_section":"305","bns_name":"Theft in Dwelling","category":"Property","note":""},
    {"ipc_section":"383","ipc_name":"Extortion","bns_section":"308","bns_name":"Extortion","category":"Property","note":""},
    {"ipc_section":"390","ipc_name":"Robbery","bns_section":"309","bns_name":"Robbery","category":"Property","note":""},
    {"ipc_section":"391","ipc_name":"Dacoity","bns_section":"310","bns_name":"Dacoity","category":"Property","note":""},
    {"ipc_section":"415","ipc_name":"Cheating","bns_section":"318","bns_name":"Cheating","category":"Property","note":""},
    {"ipc_section":"420","ipc_name":"Cheating (Dishonest Inducement)","bns_section":"318(4)","bns_name":"Cheating with Dishonest Inducement","category":"Property","note":""},
    {"ipc_section":"425","ipc_name":"Mischief","bns_section":"324","bns_name":"Mischief","category":"Property","note":""},
    {"ipc_section":"447","ipc_name":"Criminal Trespass","bns_section":"329","bns_name":"Criminal Trespass","category":"Property","note":""},
    {"ipc_section":"463","ipc_name":"Forgery","bns_section":"336","bns_name":"Forgery","category":"Property","note":""},
    {"ipc_section":"467","ipc_name":"Forgery of Valuable Security","bns_section":"338","bns_name":"Forgery of Valuable Security","category":"Property","note":""},
    # Hurt
    {"ipc_section":"319","ipc_name":"Hurt","bns_section":"114","bns_name":"Hurt","category":"Hurt","note":""},
    {"ipc_section":"320","ipc_name":"Grievous Hurt","bns_section":"116","bns_name":"Grievous Hurt","category":"Hurt","note":""},
    {"ipc_section":"323","ipc_name":"Voluntarily Causing Hurt","bns_section":"115","bns_name":"Voluntarily Causing Hurt","category":"Hurt","note":""},
    {"ipc_section":"325","ipc_name":"Voluntarily Causing Grievous Hurt","bns_section":"117","bns_name":"Voluntarily Causing Grievous Hurt","category":"Hurt","note":""},
    {"ipc_section":"326","ipc_name":"Hurt by Dangerous Weapon","bns_section":"118","bns_name":"Hurt by Dangerous Weapon","category":"Hurt","note":""},
    {"ipc_section":"326A","ipc_name":"Acid Attack","bns_section":"124","bns_name":"Acid Attack","category":"Hurt","note":""},
    # Speech & public order
    {"ipc_section":"499","ipc_name":"Defamation","bns_section":"356","bns_name":"Defamation","category":"Speech","note":""},
    {"ipc_section":"503","ipc_name":"Criminal Intimidation","bns_section":"351","bns_name":"Criminal Intimidation","category":"Speech","note":""},
    {"ipc_section":"504","ipc_name":"Intentional Insult","bns_section":"352","bns_name":"Intentional Insult","category":"Speech","note":""},
    {"ipc_section":"505","ipc_name":"Statements Causing Mischief","bns_section":"353","bns_name":"Statements Causing Mischief","category":"Speech","note":""},
    {"ipc_section":"506","ipc_name":"Punishment for Criminal Intimidation","bns_section":"351(2)","bns_name":"Punishment for Criminal Intimidation","category":"Speech","note":""},
    # New BNS-only sections
    {"ipc_section":"NEW","ipc_name":"Organised Crime (new)","bns_section":"111","bns_name":"Organised Crime","category":"New","note":"New in BNS — no direct IPC counterpart"},
    {"ipc_section":"NEW","ipc_name":"Petty Organised Crime (new)","bns_section":"112","bns_name":"Petty Organised Crime","category":"New","note":"New in BNS — covers snatching, ticket touts etc."},
    {"ipc_section":"NEW","ipc_name":"Terrorist Act (transferred from UAPA)","bns_section":"113","bns_name":"Terrorist Act","category":"New","note":"Moved from special law into main penal code"},
]


class IPCBNSComparator:
    """Handles IPC→BNS translation and scenario-based comparison."""

    def __init__(self):
        self._mapping_df: Optional[pd.DataFrame] = None
        self._bns_df: Optional[pd.DataFrame] = None

    # ── Initialization ──────────────────────────────────────────────────────────

    def load(self) -> "IPCBNSComparator":
        """Load mapping CSV (or fall back to built-in mapping)."""
        if IPC_BNS_MAPPING_PATH.exists():
            self._mapping_df = pd.read_csv(IPC_BNS_MAPPING_PATH, dtype=str)
        else:
            self._mapping_df = pd.DataFrame(_BUILTIN_MAPPING)
            IPC_BNS_MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._mapping_df.to_csv(IPC_BNS_MAPPING_PATH, index=False)
            print(f"[Comparator] Mapping CSV created: {IPC_BNS_MAPPING_PATH}")

        self._bns_df = pd.read_csv(ROOT / "bns_sections.csv", encoding="utf-8")
        self._bns_df.columns = [c.strip().replace(" ", "_") for c in self._bns_df.columns]
        print(f"[Comparator] Loaded {len(self._mapping_df)} IPC→BNS mappings")
        return self

    # ── Section Translation ─────────────────────────────────────────────────────

    def translate_ipc_to_bns(self, ipc_section: str) -> dict:
        """
        Given an IPC section number (e.g. '302', '376D'), return BNS equivalent.
        Returns a dict with keys: ipc_section, bns_section, ipc_name, bns_name, note, bns_text
        """
        ipc_section = str(ipc_section).strip().upper()

        # Look up in mapping
        row = self._mapping_df[
            self._mapping_df["ipc_section"].str.upper() == ipc_section
        ]
        if row.empty:
            return {
                "ipc_section": ipc_section,
                "bns_section": "UNKNOWN",
                "ipc_name": "Not found in mapping",
                "bns_name": "Not found",
                "note": f"IPC Section {ipc_section} not in mapping table. Use chatbot for detailed lookup.",
                "bns_text": "",
                "found": False,
            }

        r = row.iloc[0]
        result = {
            "ipc_section": r["ipc_section"],
            "bns_section": r["bns_section"],
            "ipc_name": r["ipc_name"],
            "bns_name": r["bns_name"],
            "note": r.get("note", ""),
            "category": r.get("category", ""),
            "found": True,
            "bns_text": "",
        }

        # Try to get BNS full text
        if r["bns_section"] not in ("REPEALED", "UNKNOWN", "NEW"):
            bns_num_str = re.sub(r'\([^)]*\)', '', r["bns_section"]).strip()
            try:
                bns_num = int(bns_num_str)
                bns_rows = self._bns_df[
                    pd.to_numeric(
                        self._bns_df.get("Section", self._bns_df.get("section_num", pd.Series())),
                        errors="coerce"
                    ) == bns_num
                ]
                if not bns_rows.empty:
                    result["bns_text"] = str(bns_rows.iloc[0].get("Description", ""))[:1500]
            except Exception:
                pass

        return result

    # ── Scenario Comparison ─────────────────────────────────────────────────────

    def compare_scenario(self, scenario: str, language: str = "en") -> dict:
        """
        Given a user scenario, retrieve relevant IPC + BNS sections
        and generate a side-by-side comparison.
        Returns {bns_results, ipc_results, llm_analysis}
        """
        engine = get_engine()

        # Two PageIndex queries
        bns_results = engine.query_bns(scenario, top_k=3)
        ipc_results = engine.query_ipc(scenario, top_k=3)

        # Build context for LLM
        bns_context = engine.format_context(bns_results)
        ipc_context = engine.format_context(ipc_results)

        prompt = f"""A user describes this scenario: "{scenario}"

**Relevant BNS (Bharatiya Nyaya Sanhita 2023) sections:**
{bns_context if bns_context else "No specific sections found — use general knowledge."}

**Relevant IPC (Indian Penal Code 1860) sections:**
{ipc_context if ipc_context else "No specific sections found — use general knowledge."}

Please provide:
1. **Applicable BNS Sections** — list section numbers and punishments
2. **Applicable IPC Sections** — list section numbers and punishments  
3. **Key Differences** — what changed from IPC to BNS for this scenario
4. **Advice for Citizen** — practical next steps
"""

        analysis = chat(
            [{"role": "user", "content": prompt}],
            language=language,
            max_tokens=1200,
        )

        return {
            "scenario": scenario,
            "bns_results": bns_results,
            "ipc_results": ipc_results,
            "llm_analysis": analysis,
        }

    def get_full_mapping_df(self) -> pd.DataFrame:
        return self._mapping_df.copy()


# ── Singleton ────────────────────────────────────────────────────────────────────
_comparator: Optional[IPCBNSComparator] = None

def get_comparator() -> IPCBNSComparator:
    global _comparator
    if _comparator is None:
        _comparator = IPCBNSComparator().load()
    return _comparator


if __name__ == "__main__":
    comp = get_comparator()
    result = comp.translate_ipc_to_bns("302")
    print(result)
    print("\n")
    result2 = comp.translate_ipc_to_bns("420")
    print(result2)
