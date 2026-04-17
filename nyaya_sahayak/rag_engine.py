"""
PageIndex-powered RAG engine for Nyaya-Sahayak.
Builds hierarchical tree indices for BNS and IPC, then uses LLM reasoning for retrieval.
Two separate indices support side-by-side comparison queries.
"""

from __future__ import annotations
import sys, json, os
from pathlib import Path
from typing import Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from nyaya_sahayak.config import (
    BNS_CSV_PATH, BNS_INDEX_PATH, IPC_INDEX_PATH, ROOT,
    LLM_MODEL, LLM_API_KEY, LLM_BASE_URL
)

# ── PageIndex Vendor Path ───────────────────────────────────────────────────────
VENDOR_PATH = ROOT / "vendor" / "PageIndex"
if VENDOR_PATH.exists():
    sys.path.insert(0, str(VENDOR_PATH))

# ── BNS In-Memory Index (built from CSV directly) ────────────────────────────────
class BNSIndex:
    """
    Hierarchical tree index built from bns_sections.csv.
    Structure: chapters → sections (no PDF processing needed).
    """

    def __init__(self):
        self.chapters: dict[str, dict] = {}
        self.sections: dict[int, dict] = {}
        self._built = False

    def build(self) -> "BNSIndex":
        """Parse CSV and build tree."""
        pdf = pd.read_csv(BNS_CSV_PATH, encoding="utf-8")
        pdf.columns = [c.strip().replace(" ", "_") for c in pdf.columns]

        for _, row in pdf.iterrows():
            ch = str(row.get("Chapter", ""))
            ch_name = str(row.get("Chapter_name", ""))
            sec = int(pd.to_numeric(row.get("Section", 0), errors="coerce") or 0)
            sec_name = ""
            for k in row.index:
                if "section" in k.lower() and "name" in k.lower() and k != "Chapter_name":
                    sec_name = str(row[k]); break
            desc = str(row.get("Description", ""))

            if ch not in self.chapters:
                self.chapters[ch] = {"name": ch_name, "sections": []}
            self.chapters[ch]["sections"].append(sec)

            self.sections[sec] = {
                "chapter": ch,
                "chapter_name": ch_name,
                "section_num": sec,
                "section_name": sec_name,
                "description": desc,
                "ref": f"BNS Section {sec}",
            }

        self._built = True
        print(f"[RAG] BNS index built: {len(self.sections)} sections, {len(self.chapters)} chapters")
        return self

    def get_section(self, num: int) -> Optional[dict]:
        return self.sections.get(num)

    def search_keyword(self, keyword: str, top_k: int = 5) -> list[dict]:
        kw = keyword.lower()
        results = []
        for sec, data in self.sections.items():
            score = 0
            text = (data["section_name"] + " " + data["description"]).lower()
            score += text.count(kw) * 2
            if kw in data["section_name"].lower():
                score += 10
            if score > 0:
                results.append({**data, "_score": score})
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:top_k]

    def get_chapter_summary(self, chapter_num: str) -> dict:
        ch = self.chapters.get(str(chapter_num), {})
        sections = [self.sections[s] for s in ch.get("sections", []) if s in self.sections]
        return {"chapter": chapter_num, "name": ch.get("name", ""), "sections": sections}

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"chapters": self.chapters, "sections": {str(k): v for k, v in self.sections.items()}}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[RAG] BNS index saved: {path}")

    def load(self, path: Path) -> "BNSIndex":
        data = json.loads(path.read_text(encoding="utf-8"))
        self.chapters = data["chapters"]
        self.sections = {int(k): v for k, v in data["sections"].items()}
        self._built = True
        print(f"[RAG] BNS index loaded: {len(self.sections)} sections")
        return self


# ── PageIndex Tree RAG ──────────────────────────────────────────────────────────
class PageIndexRAG:
    """
    Wraps the PageIndex library (cloned to vendor/) for PDF-based retrieval.
    Falls back to keyword search if PageIndex is unavailable.
    """

    def __init__(self, label: str, md_path: Path, index_path: Path):
        self.label = label
        self.md_path = md_path
        self.index_path = index_path
        self._tree = None
        self._pi = None

    def _load_pageindex(self):
        """Try to import and configure PageIndex."""
        try:
            import litellm
            # Configure litellm to use HF endpoint
            os.environ.setdefault("OPENAI_API_KEY", LLM_API_KEY)
            os.environ.setdefault("OPENAI_API_BASE", LLM_BASE_URL)

            # Dynamic import from vendor path
            sys.path.insert(0, str(VENDOR_PATH))
            from pageindex.page_index import PageIndex
            self._pi = PageIndex(model=f"openai/{LLM_MODEL}")
            print(f"[RAG/{self.label}] PageIndex loaded successfully")
            return True
        except Exception as e:
            print(f"[RAG/{self.label}] PageIndex not available ({e}), using built-in retrieval")
            return False

    def build_or_load(self) -> "PageIndexRAG":
        """Build a new index or load from cache."""
        if self.index_path.exists():
            print(f"[RAG/{self.label}] Loading cached index: {self.index_path}")
            self._tree = json.loads(self.index_path.read_text(encoding="utf-8"))
            return self

        if not self.md_path.exists():
            print(f"[RAG/{self.label}] ⚠️ MD file not found: {self.md_path}")
            return self

        if self._load_pageindex() and self._pi:
            try:
                print(f"[RAG/{self.label}] Building PageIndex tree from {self.md_path}...")
                self._tree = self._pi.build_from_md(str(self.md_path))
                self.index_path.parent.mkdir(parents=True, exist_ok=True)
                self.index_path.write_text(
                    json.dumps(self._tree, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                print(f"[RAG/{self.label}] Tree saved to {self.index_path}")
            except Exception as e:
                print(f"[RAG/{self.label}] Tree build failed: {e}")
        return self

    def query(self, question: str, top_k: int = 3) -> list[dict]:
        """Query the index. Returns list of relevant section dicts."""
        if self._pi and self._tree:
            try:
                result = self._pi.query(self._tree, question, top_k=top_k)
                return self._format_pageindex_results(result)
            except Exception as e:
                print(f"[RAG/{self.label}] Query error: {e}")

        # Fallback: simple keyword search over the MD file
        return self._keyword_search(question, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        """Keyword search supporting both Markdown (BNS) and plain-text (IPC) files."""
        if not self.md_path.exists():
            return []
        text = self.md_path.read_text(encoding="utf-8")
        kws = [k for k in query.lower().split() if len(k) > 2]
        parts = []

        if "\n### " in text:
            # Markdown format (BNS) — split by section headers
            for sec in text.split("\n### ")[1:]:
                lines = sec.strip().split("\n")
                parts.append((lines[0], "\n".join(lines[1:])))
        else:
            # Plain-text format (IPC PDF) — split by section number pattern
            import re
            chunks = re.split(r'\n(?=\d{1,3}[A-Z]?\.\s)', text)
            for chunk in chunks:
                lines = chunk.strip().split("\n")
                header = lines[0][:120] if lines else ""
                body = "\n".join(lines[1:])
                parts.append((header, body))

        results = []
        for header, body in parts:
            combined = (header + " " + body).lower()
            score = sum(combined.count(kw) + header.lower().count(kw) * 2 for kw in kws)
            if score > 0:
                results.append({
                    "title": header.strip(),
                    "text": body[:800].strip(),
                    "score": score,
                    "source": self.label,
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _format_pageindex_results(self, pi_result) -> list[dict]:
        """Convert PageIndex output to our standard format."""
        if isinstance(pi_result, list):
            return [{"title": r.get("title",""), "text": r.get("content",""), "source": self.label} for r in pi_result]
        if isinstance(pi_result, dict):
            return [{"title": pi_result.get("title",""), "text": pi_result.get("content",""), "source": self.label}]
        return [{"title": "Result", "text": str(pi_result), "source": self.label}]


# ── Unified RAG Engine ───────────────────────────────────────────────────────────
class NyayaRAGEngine:
    """
    Main RAG engine exposing BNS + IPC retrieval.
    Uses PageIndex trees for reasoning-based retrieval with LLM synthesis.
    """

    def __init__(self):
        self.bns_index = BNSIndex()
        self.bns_rag = PageIndexRAG(
            label="BNS",
            md_path=ROOT / "data" / "bns_full.md",
            index_path=BNS_INDEX_PATH,
        )
        self.ipc_rag = PageIndexRAG(
            label="IPC",
            md_path=ROOT / "data" / "ipc_full.md",
            index_path=IPC_INDEX_PATH,
        )

    def initialize(self) -> "NyayaRAGEngine":
        """Build/load all indices."""
        self.bns_index.build()
        self.bns_rag.build_or_load()
        self.ipc_rag.build_or_load()
        print("[RAG] NyayaRAGEngine ready ✅")
        return self

    # ── Public Query Methods ────────────────────────────────────────────────────

    def query_bns(self, question: str, top_k: int = 3) -> list[dict]:
        """Retrieve relevant BNS sections for a question."""
        # First try structured CSV index
        kw_results = self.bns_index.search_keyword(question, top_k=top_k)
        if kw_results:
            return [{"title": f"BNS Section {r['section_num']} — {r['section_name']}",
                     "text": r["description"][:800],
                     "section_num": r["section_num"],
                     "source": "BNS"} for r in kw_results]
        # Fall back to PageIndex
        return self.bns_rag.query(question, top_k=top_k)

    def query_ipc(self, question: str, top_k: int = 3) -> list[dict]:
        """Retrieve relevant IPC sections for a question."""
        return self.ipc_rag.query(question, top_k=top_k)

    def query_bns_section(self, section_num: int) -> Optional[dict]:
        """Get a specific BNS section by number."""
        return self.bns_index.get_section(section_num)

    def format_context(self, results: list[dict]) -> str:
        """Format RAG results into a context string for the LLM."""
        parts = []
        for r in results:
            parts.append(f"**{r.get('title','Section')}**\n{r.get('text','')}")
        return "\n\n---\n\n".join(parts)


# ── Singleton ────────────────────────────────────────────────────────────────────
_engine: Optional[NyayaRAGEngine] = None

def get_engine() -> NyayaRAGEngine:
    """Return (or lazily initialize) the global RAG engine."""
    global _engine
    if _engine is None:
        _engine = NyayaRAGEngine().initialize()
    return _engine


if __name__ == "__main__":
    engine = get_engine()
    results = engine.query_bns("murder punishment")
    for r in results:
        print(r["title"])
        print(r["text"][:200])
        print("---")
