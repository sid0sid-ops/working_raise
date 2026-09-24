"""
RAISE Academic GraphRAG Studio - System Synthesis Prompt Module
Formatted for optimal LLM adherence (Qwen 2.5, GPT-4, Claude, LLaMA)
with clear semantic boundaries, citation formatting, and anti-hallucination guardrails.
"""

import re
from typing import Any, Dict, List, Optional


def sanitize_rag_text(text: str) -> str:
    """
    Sanitizes RAG text, stripping control characters, normalizing newlines,
    and ensuring bullet points, lists, and paragraphs are formatted cleanly for
    both terminal and web frontends. Automatically attributes entity roles and
    structures bullet points with blank line spacing to prevent paragraph collapsing.
    """
    if not text:
        return ""
    # Strip non-printable control characters (ASCII 0-8, 11, 12, 14-31, 127)
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    cleaned = re.sub(r'\r\n|\r', '\n', cleaned)
    # Strip raw Docling scaffolding like [Section Context: ...]
    cleaned = re.sub(r'\[Section Context:[^\]]*\]', '', cleaned, flags=re.IGNORECASE)
    # Strip accidental inlined (Filename.pdf, Page X) or (Doc: ..., Page X) prose artifacts
    cleaned = re.sub(r'\s*\([^)]*?\.pdf,\s*(?:PDF\s*)?Page\s*\d+[^)]*?\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\[Doc:\s*[^\]]+?\.pdf,\s*(?:PDF\s*)?Page\s*\d+[^\]]*?\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\((?:p\.|page)\s*\d+\)', '', cleaned, flags=re.IGNORECASE)
    # Strip negative enumeration or omission explanations (e.g. "Excerpts [4] and [5] were omitted...")
    cleaned = re.sub(
        r'(?:(?:Excerpts?|Passages?|Sources?|References?)\s*(?:\[\d+\][,\s&and–-]*)+[^.\n]*(?:omitted|excluded|not\s+(?:used|relevant)|do\s+not\s+pertain|pertain\s+to|refer\s+to|irrelevant)[^.\n]*[.\n]?)',
        '',
        cleaned,
        flags=re.IGNORECASE,
    )

    # Normalize colon followed immediately by text or newline
    cleaned = re.sub(r':\s*\n+', ':\n\n', cleaned)

    # Convert existing bullets to unicode bullet '• ' which triggers frontend rich card renderer
    cleaned = re.sub(r'(^|\n)\s*[\-\*\+]\s+', r'\1• ', cleaned)

    lines = [l.strip() for l in cleaned.split('\n')]
    processed = []
    i = 0
    in_entity_list = False
    entity_bullets = []

    while i < len(lines):
        line = lines[i]
        if not line:
            processed.append('')
            i += 1
            continue

        # Check if line already has a bullet or number
        is_bullet = bool(re.match(r'^(?:•|\d+\.)\s+', line))

        # Check if previous line ended with a colon indicating an introductory list header
        prev_was_intro = bool(processed and any(processed[-j].endswith(':') for j in range(1, min(4, len(processed)+1)) if processed[-j]))

        # Detect standalone entity/name lines
        is_entity_line = (
            not is_bullet and 
            (prev_was_intro or in_entity_list) and 
            len(line) < 80 and 
            (not line.endswith('.') or any(line.startswith(h) for h in ["Dr.", "Prof.", "Mr.", "Ms.", "Mrs.", "Shri", "Thiru."]))
        )

        if is_entity_line:
            raw_entity = line.strip('* ')
            line = f"• **{raw_entity}**"
            is_bullet = True
            in_entity_list = True
            entity_bullets.append(raw_entity)
        elif is_bullet:
            in_entity_list = True
        else:
            in_entity_list = False

        processed.append(line)
        i += 1

    # Check if trailing paragraphs contain descriptive roles for the detected entity bullets
    if entity_bullets:
        final_lines = []
        for p_idx, pl in enumerate(processed):
            if any(pl == f"• **{ent}**" for ent in entity_bullets):
                ent_name = pl.replace("• **", "").replace("**", "").strip()
                core_name = re.sub(r"^(?:Dr\.|Prof\.|Thiru\.|Mr\.|Ms\.|Mrs\.|Shri)\s*", "", ent_name).split(",")[0].strip()
                matched_role = None
                for search_idx in range(len(processed)):
                    cand = processed[search_idx]
                    if cand and not cand.startswith("•") and core_name.lower() in cand.lower():
                        sents = re.split(r'(?<=[.!?])\s+', cand)
                        ent_sents = [s for s in sents if core_name.lower() in s.lower()]
                        if ent_sents:
                            matched_role = " ".join(ent_sents)
                            break
                if matched_role:
                    desc = re.sub(rf"^(?:.*?\b)?{re.escape(core_name)}\b(?:\s*,\s*IAS)?\s*(?:is\s+also|is\s+the|is)?\s*", "", matched_role, flags=re.IGNORECASE).strip()
                    desc = desc[0].upper() + desc[1:] if desc else matched_role
                    cits_in_role = re.findall(r"\[\d+\]", matched_role)
                    cit_str = f" {cits_in_role[0]}" if (cits_in_role and not re.search(r"\[\d+\]", desc)) else ""
                    final_lines.append(f"• **{ent_name}**: {desc}{cit_str}")
                else:
                    final_lines.append(pl)
            elif not pl.startswith("•") and any(re.sub(r"^(?:Dr\.|Prof\.|Thiru\.|Mr\.|Ms\.|Mrs\.|Shri)\s*", "", ent).split(",")[0].strip().lower() in pl.lower() for ent in entity_bullets):
                sents = re.split(r'(?<=[.!?])\s+', pl)
                remaining_sents = []
                for s in sents:
                    s_clean = re.sub(r"^(?:Dr\.|Prof\.|Thiru\.|Mr\.|Ms\.|Mrs\.|Shri|\s+|\[\d+\])+$", "", s).strip()
                    if s_clean and not any(re.sub(r"^(?:Dr\.|Prof\.|Thiru\.|Mr\.|Ms\.|Mrs\.|Shri)\s*", "", ent).split(",")[0].strip().lower() in s.lower() for ent in entity_bullets):
                        remaining_sents.append(s)
                if remaining_sents:
                    final_lines.append(" ".join(remaining_sents))
            else:
                final_lines.append(pl)
        processed = final_lines

    result = '\n'.join(processed)
    # Ensure double newlines around bullets
    result = re.sub(r'\n(•\s+)', r'\n\n\1', result)
    result = re.sub(r'(:\s*\n+)(•\s+)', r':\n\n\2', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


SYSTEM_SYNTHESIS_PROMPT = """You are an expert academic and institutional research intelligence assistant.
Answer the user's inquiry accurately, professionally, and concisely using ONLY the provided verified context chunks.

STRICT FORMATTING AND CITATION RULES:
1. CITATIONS:
   - CRITICAL CITATION RULE: You MUST ground every factual claim, metric, or entity with an inline citation bracket referencing the source chunk index, e.g., "The institute established 4 new Centres of Excellence [1]."
   - Cite sources using simple numeric ASCII bracket markers ONLY: [1], [2], or multi-citation [1, 2].
   - Do NOT use bold unicode numbers (e.g. do NOT use [𝟏]). Use only standard ASCII brackets: [1], [2].
   - Place citation markers directly after the specific claim, fact, or bullet point they support.
   - NEVER write out the PDF filename, page number, or document title inside the answer text (e.g. NEVER write "(Report.pdf, Page 8) [1]" or "(Annual Report, p. 12)"). All document metadata will be rendered automatically by the UI via citation badges.

2. STRUCTURE & READABILITY:
   - Provide a natural, synthesized response. Do NOT simply dump raw context chunks.
   - Group related findings into clear thematic headings (### Heading) or formatted bullet points (`• `).
   - When listing persons, organizations, roles, recommendations, or key facts, ALWAYS format each entry as a bullet point starting with `• **Name/Title**: Description [citation]` on its own line.
   - ALWAYS leave a blank line before starting any list and after every bullet item.
   - Never output lists as unbulleted lines or inline comma-separated blocks.
   - If quoting an excerpt, present it as a clean blockquote (> "quote") or an indented excerpt.

3. DIRECT FACTUAL ANSWER:
   - State the direct, factual answer immediately in your first sentence.
   - If the user asks for a specific numeric metric, date, name, or total, provide that exact data upfront.

4. UNGROUNDED CLAIMS & STRICT BOUNDARIES:
   - Absolute negative constraint: NEVER extrapolate, speculate, or introduce external facts not present in the provided excerpts.
   - If the uploaded documents do not contain sufficient evidence to answer the query, state clearly what is missing rather than speculating.

5. NEGATIVE STATEMENTS & ABSENCE OF INFORMATION:
   - When stating that an event, entity, award, or fact is NOT mentioned, NOT won, or NOT present in the document (e.g. "did not win any Nobel Prizes", "no information is provided regarding..."), DO NOT attach any bracket citations [N].
   - Numeric bracket citations [1], [2] must ONLY be attached to sentences asserting positive facts directly quoted or extracted from the evidence.

6. RELEVANT PASSAGES & ANTI-ENUMERATION:
   - Only synthesize facts directly supported by the relevant context.
   - Do NOT enumerate, list, or explain why irrelevant passages or excerpts were omitted.
   - Use citations ([1], [2]) ONLY for the relevant excerpts that directly support your substantive claims.
"""


def get_synthesis_system_prompt() -> str:
    """Returns the canonical system synthesis prompt string."""
    return SYSTEM_SYNTHESIS_PROMPT.strip()


def format_synthesis_user_prompt(query: str, evidence: str) -> str:
    """
    Constructs the formatted user prompt pairing the research query with retrieved evidence.
    """
    return f"""<user_query>
{query.strip()}
</user_query>

<retrieved_evidence>
{evidence.strip()}
</retrieved_evidence>

Please generate the grounded, cited answer following all system instructions:"""


def build_synthesis_chat_messages(
    query: str,
    evidence: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Builds an OpenAI/vLLM compliant message list for multi-turn chat synthesis.
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": get_synthesis_system_prompt()}
    ]

    # Append past conversation history if present
    if chat_history:
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    # Append current turn with query and evidence
    user_content = format_synthesis_user_prompt(query, evidence)
    messages.append({"role": "user", "content": user_content})

    return messages