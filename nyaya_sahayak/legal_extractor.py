"""
LangExtract integration for Nyaya-Sahayak.
Extracts structured legal information from PDF text and user input.
Uses a custom OpenAI-compatible provider pointing to Sarvam-M via HF.
"""

from __future__ import annotations
import sys, os, json, textwrap
from pathlib import Path
from typing import Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from nyaya_sahayak.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, ROOT

# ── Schema Definitions ──────────────────────────────────────────────────────────
LEGAL_EXTRACTION_PROMPT = textwrap.dedent("""\
    Extract legal entities from Indian legal text.
    For each entity, identify:
    - The section number (IPC or BNS)
    - The offence/provision name
    - The punishment/consequence
    - Key conditions or exceptions
    Use EXACT text from the document. Do not paraphrase.
""")

MAPPING_EXTRACTION_PROMPT = textwrap.dedent("""\
    Extract IPC to BNS section correspondence from legal text.
    Identify pairs where an old IPC section maps to a new BNS section.
    Include the section numbers and section names for both.
""")

# ── LangExtract with Custom Provider ───────────────────────────────────────────
def _build_langextract_examples():
    """Build few-shot examples for LangExtract."""
    try:
        import langextract as lx
        examples = [
            lx.data.ExampleData(
                text="Section 103 of BNS: Whoever commits murder shall be punished with death or imprisonment for life and shall also be liable to fine. (Old IPC Section 302)",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="bns_section",
                        extraction_text="Section 103 of BNS",
                        attributes={"section_num": "103", "law": "BNS", "offence": "Murder"}
                    ),
                    lx.data.Extraction(
                        extraction_class="punishment",
                        extraction_text="death or imprisonment for life and shall also be liable to fine",
                        attributes={"type": "death/life", "fine": "yes"}
                    ),
                    lx.data.Extraction(
                        extraction_class="ipc_equivalent",
                        extraction_text="Old IPC Section 302",
                        attributes={"section_num": "302", "law": "IPC"}
                    ),
                ]
            ),
            lx.data.ExampleData(
                text="BNS Section 318 corresponds to IPC 415 and 420. Cheating: Whoever, by deceiving any person, fraudulently induces them, shall be punished with imprisonment up to 3 years.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="bns_section",
                        extraction_text="BNS Section 318",
                        attributes={"section_num": "318", "law": "BNS", "offence": "Cheating"}
                    ),
                    lx.data.Extraction(
                        extraction_class="ipc_equivalent",
                        extraction_text="IPC 415",
                        attributes={"section_num": "415", "law": "IPC"}
                    ),
                    lx.data.Extraction(
                        extraction_class="ipc_equivalent",
                        extraction_text="IPC 420",
                        attributes={"section_num": "420", "law": "IPC"}
                    ),
                    lx.data.Extraction(
                        extraction_class="punishment",
                        extraction_text="imprisonment up to 3 years",
                        attributes={"duration": "3 years", "type": "imprisonment"}
                    ),
                ]
            ),
        ]
        return examples
    except ImportError:
        return None


def extract_from_text(text: str, use_mapping_mode: bool = False) -> dict:
    """
    Extract structured legal entities from text using LangExtract.
    Falls back to LLM-based extraction if LangExtract is unavailable.
    
    Returns dict with keys: sections, punishments, ipc_mappings
    """
    prompt = MAPPING_EXTRACTION_PROMPT if use_mapping_mode else LEGAL_EXTRACTION_PROMPT

    try:
        import langextract as lx
        examples = _build_langextract_examples()
        if examples is None:
            raise ImportError("LangExtract examples failed")

        # Use OpenAI provider with HF endpoint
        result = lx.extract(
            text_or_documents=text[:8000],  # Limit for API
            prompt_description=prompt,
            examples=examples,
            model_id="gpt-4o",           # Will be remapped to HF endpoint
            api_key=LLM_API_KEY,
            fence_output=True,
            use_schema_constraints=False,
        )

        # Parse results
        sections, punishments, mappings = [], [], []
        for ext in result.extractions:
            if ext.char_interval is None:
                continue  # Skip hallucinated extractions
            cls = ext.extraction_class
            attrs = ext.attributes or {}
            entry = {"text": ext.extraction_text, **attrs}
            if cls == "bns_section":
                sections.append(entry)
            elif cls == "punishment":
                punishments.append(entry)
            elif cls == "ipc_equivalent":
                mappings.append(entry)

        return {"sections": sections, "punishments": punishments, "ipc_mappings": mappings, "source": "langextract"}

    except Exception as e:
        print(f"[LangExtract] Falling back to LLM extraction: {e}")
        return _llm_extract(text, use_mapping_mode)


def _llm_extract(text: str, use_mapping_mode: bool) -> dict:
    """
    LLM-based structured extraction fallback using Sarvam-M.
    Returns structured JSON via prompt engineering.
    """
    from nyaya_sahayak.llm_client import chat

    if use_mapping_mode:
        prompt = f"""Extract IPC to BNS section mappings from this legal text.
Return ONLY valid JSON in this exact format:
{{
  "mappings": [
    {{"ipc_section": "302", "ipc_name": "Murder", "bns_section": "103", "bns_name": "Murder"}}
  ]
}}

Text:
{text[:3000]}"""
        response = chat([{"role": "user", "content": prompt}], max_tokens=800, temperature=0.0)
        try:
            json_match = __import__('re').search(r'\{.*\}', response, __import__('re').DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {"sections": [], "punishments": [], "ipc_mappings": data.get("mappings", []), "source": "llm_fallback"}
        except Exception:
            pass
    else:
        prompt = f"""Extract legal entities from this text. Return ONLY valid JSON:
{{
  "sections": [{{"section_num": "103", "law": "BNS", "offence": "Murder", "text": "..."}}],
  "punishments": [{{"section_ref": "103", "punishment": "death or life imprisonment"}}]
}}

Text:
{text[:3000]}"""
        response = chat([{"role": "user", "content": prompt}], max_tokens=800, temperature=0.0)
        try:
            json_match = __import__('re').search(r'\{.*\}', response, __import__('re').DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {"sections": data.get("sections",[]), "punishments": data.get("punishments",[]),
                        "ipc_mappings": [], "source": "llm_fallback"}
        except Exception:
            pass

    return {"sections": [], "punishments": [], "ipc_mappings": [], "source": "failed"}


def extract_from_pdf(pdf_path: Path, use_mapping_mode: bool = False) -> dict:
    """Extract structured entities from a PDF file."""
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:50]:  # First 50 pages
                texts.append(page.extract_text() or "")
        text = "\n".join(texts)
        return extract_from_text(text, use_mapping_mode=use_mapping_mode)
    except Exception as e:
        return {"error": str(e), "sections": [], "punishments": [], "ipc_mappings": []}


def build_mapping_from_pdfs() -> pd.DataFrame:
    """
    Extract IPC→BNS mappings from both PDFs and merge with built-in mapping.
    Returns a DataFrame.
    """
    from nyaya_sahayak.comparator import _BUILTIN_MAPPING, IPC_BNS_MAPPING_PATH

    # Start with built-in mapping
    df = pd.DataFrame(_BUILTIN_MAPPING)

    # Try to extract more from PDFs
    for pdf_path in [ROOT / "repealedfileopen.pdf", ROOT / "250883_english_01042024.pdf"]:
        if pdf_path.exists():
            print(f"[LangExtract] Extracting mappings from {pdf_path.name}...")
            result = extract_from_pdf(pdf_path, use_mapping_mode=True)
            new_maps = result.get("ipc_mappings", [])
            if new_maps:
                new_df = pd.DataFrame(new_maps)
                # Align columns
                for col in ["ipc_section","ipc_name","bns_section","bns_name","category","note"]:
                    if col not in new_df.columns:
                        new_df[col] = ""
                df = pd.concat([df, new_df[df.columns.tolist()]], ignore_index=True)
                print(f"[LangExtract] Added {len(new_maps)} mappings from {pdf_path.name}")

    # Deduplicate
    df = df.drop_duplicates(subset=["ipc_section","bns_section"])
    df.to_csv(IPC_BNS_MAPPING_PATH, index=False)
    print(f"[LangExtract] Final mapping: {len(df)} entries → {IPC_BNS_MAPPING_PATH}")
    return df


if __name__ == "__main__":
    # Test extraction
    test_text = """BNS Section 103 deals with punishment for murder.
    Whoever commits murder shall be punished with death or imprisonment for life.
    This corresponds to IPC Section 302."""
    result = extract_from_text(test_text)
    print(json.dumps(result, indent=2))
