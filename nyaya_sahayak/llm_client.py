"""
Sarvam-M LLM client via HuggingFace Inference API (OpenAI-compatible endpoint).
Supports Hindi/English responses and streaming.
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path
from typing import Iterator, List, Dict, Optional

from openai import OpenAI

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from nyaya_sahayak.config import (
    LLM_BASE_URL, LLM_API_KEY, LLM_MODEL,
    MAX_TOKENS_ANSWER, TEMPERATURE_LEGAL
)

# ── System Prompts ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT_EN = """You are Nyaya-Sahayak (न्याय-सहायक), an expert Indian legal assistant specializing in:
1. Bharatiya Nyaya Sanhita 2023 (BNS) — India's new penal code
2. Indian Penal Code 1860 (IPC) — the old penal code now replaced by BNS
3. Government schemes and citizen rights

When answering:
- Always cite specific BNS section numbers (e.g., "BNS Section 101")
- When comparing with IPC, cite both (e.g., "IPC 302 → BNS 101")
- Keep language clear and accessible for common citizens
- Flag important legal disclaimers where needed
- Structure your answer with clear headings if long

You are NOT a lawyer and users should consult a qualified advocate for their specific case."""

SYSTEM_PROMPT_HI = """आप न्याय-सहायक हैं, एक विशेषज्ञ भारतीय कानूनी सहायक जो इन विषयों में विशेषज्ञता रखते हैं:
1. भारतीय न्याय संहिता 2023 (BNS) — भारत का नया दंड संहिता
2. भारतीय दंड संहिता 1860 (IPC) — पुरानी दंड संहिता जिसे BNS ने बदला
3. सरकारी योजनाएं और नागरिक अधिकार

उत्तर देते समय:
- हमेशा BNS धारा संख्या बताएं (जैसे "BNS धारा 101")
- IPC से तुलना करते समय दोनों बताएं (जैसे "IPC 302 → BNS 101")
- भाषा सरल और आम नागरिकों के लिए समझने योग्य रखें
- जहां जरूरी हो कानूनी अस्वीकरण लगाएं

आप वकील नहीं हैं — अपने विशिष्ट मामले के लिए योग्य अधिवक्ता से परामर्श लें।"""

# ── Client Factory ──────────────────────────────────────────────────────────────

def _get_client() -> OpenAI:
    """Return an OpenAI-compatible client pointed at Sarvam-M / HF endpoint."""
    return OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=120.0,
    )


# ── Core Chat Function ──────────────────────────────────────────────────────────

def chat(
    messages: List[Dict[str, str]],
    language: str = "en",
    max_tokens: int = MAX_TOKENS_ANSWER,
    temperature: float = TEMPERATURE_LEGAL,
    stream: bool = False,
) -> str | Iterator[str]:
    """
    Send a chat request to Sarvam-M.

    Args:
        messages:    List of {"role": ..., "content": ...} dicts (WITHOUT system msg)
        language:    "en" or "hi"
        max_tokens:  Maximum tokens in response
        temperature: Sampling temperature
        stream:      If True, returns a generator yielding text chunks

    Returns:
        Full response string, or a generator if stream=True
    """
    client = _get_client()
    system_prompt = SYSTEM_PROMPT_HI if language == "hi" else SYSTEM_PROMPT_EN

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    if stream:
        return _stream_response(client, full_messages, max_tokens, temperature)
    else:
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            raw = response.choices[0].message.content or ""
            return _strip_think_tags(raw)
        except Exception as e:
            return f"⚠️ LLM Error: {e}\n\nPlease check your API token and network connection."


def _stream_response(
    client: OpenAI,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> Iterator[str]:
    """Yield text chunks from a streaming response."""
    try:
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        buffer = ""
        in_think = False
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            buffer += delta
            # Strip <think>...</think> tags on-the-fly
            while True:
                if not in_think:
                    think_start = buffer.find("<think>")
                    if think_start != -1:
                        yield buffer[:think_start]
                        buffer = buffer[think_start + 7:]
                        in_think = True
                    else:
                        yield buffer
                        buffer = ""
                        break
                else:
                    think_end = buffer.find("</think>")
                    if think_end != -1:
                        buffer = buffer[think_end + 8:]
                        in_think = False
                    else:
                        buffer = ""  # discard think content
                        break
    except Exception as e:
        yield f"⚠️ Streaming error: {e}"


def _strip_think_tags(text: str) -> str:
    """Remove Sarvam-M's <think>...</think> reasoning blocks from output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ── Convenience Wrappers ────────────────────────────────────────────────────────

def ask_legal_question(question: str, language: str = "en", context: str = "") -> str:
    """Ask a straightforward legal question."""
    user_content = question
    if context:
        user_content = f"Context:\n{context}\n\nQuestion: {question}"
    return chat([{"role": "user", "content": user_content}], language=language)


def explain_section(
    section_text: str, section_ref: str, language: str = "en"
) -> str:
    """Explain a BNS section in plain language."""
    prompt = (
        f"Please explain {section_ref} in simple language that a common citizen can understand.\n\n"
        f"Section text:\n{section_text}"
    )
    if language == "hi":
        prompt = (
            f"कृपया {section_ref} को सरल भाषा में समझाएं जिसे एक आम नागरिक समझ सके।\n\n"
            f"धारा का पाठ:\n{section_text}"
        )
    return chat([{"role": "user", "content": prompt}], language=language)


def compare_sections(
    ipc_text: str,
    bns_text: str,
    ipc_ref: str,
    bns_ref: str,
    language: str = "en",
) -> str:
    """Generate a natural-language comparison between an IPC and BNS section."""
    prompt = f"""Compare {ipc_ref} (old IPC) with {bns_ref} (new BNS):

**{ipc_ref} — Indian Penal Code:**
{ipc_text}

**{bns_ref} — Bharatiya Nyaya Sanhita 2023:**
{bns_text}

Provide:
1. Key similarities
2. Key differences / changes
3. Practical impact for citizens
4. Any new provisions added or old provisions removed"""

    return chat([{"role": "user", "content": prompt}], language=language)


def classify_query(query: str) -> str:
    """
    Classify a user query into one of:
    'chatbot' | 'comparison' | 'translate_section' | 'scheme'
    """
    prompt = f"""Classify this legal query into exactly one category:
- chatbot: General legal question about BNS/IPC
- comparison: Wants to compare IPC vs BNS sections or scenarios
- translate_section: Wants to find BNS equivalent of an IPC section number
- scheme: About government schemes or eligibility

Query: "{query}"

Reply with ONLY the category name, nothing else."""

    result = chat(
        [{"role": "user", "content": prompt}],
        language="en",
        max_tokens=10,
        temperature=0.0,
    )
    result = result.strip().lower()
    valid = {"chatbot", "comparison", "translate_section", "scheme"}
    return result if result in valid else "chatbot"


if __name__ == "__main__":
    # Quick smoke test
    print("Testing Sarvam-M connection...")
    response = ask_legal_question("What is the punishment for murder under BNS?")
    print(response[:500])
