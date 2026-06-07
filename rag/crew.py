"""
CrewAI multi-agent pipeline for proposal generation.

Three agents run in sequence:
  1. QueryPlannerAgent    — decomposes the user query into 3–4 targeted search queries
  2. ResearchAnalystAgent — executes each search, synthesises a grounded research brief
  3. ProposalWriterAgent  — writes the final structured JSON using only the research brief

Why this beats single-shot RAG:
- Planner generates semantically diverse queries → surfaces more relevant chunks than
  template-expanded queries, because the LLM understands the request intent.
- Researcher synthesises before the writer sees the context → cleaner signal, less noise,
  no irrelevant chunks diluting the prompt.
- Writer focuses purely on writing with no retrieval distractions → better structure,
  correct tone, thorough depth.
- SearchKBTool tracks actual sources hit → source list is accurate, not inferred.
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import litellm
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).parent.parent / ".env")

litellm.cache = None

# CrewAI 1.14+ marks every message with cache_breakpoint for Anthropic prompt caching.
# Groq rejects requests that contain this field. Patch it out before any agent runs.
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import BaseTool

from rag.retriever import retrieve

_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
_TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

from rag.groq_keys import GroqQuotaExhaustedError, is_rotatable_error, key_manager


def _make_llm(temperature: float = 0.4) -> LLM:
    # Use Groq's OpenAI-compatible endpoint without a provider prefix.
    # The groq/ prefix routes through litellm's Groq provider which generates
    # hermes-style XML tool calls that Groq's API rejects. The openai path
    # uses standard JSON function calling which Groq accepts.
    return LLM(
        model=_GROQ_MODEL,
        base_url=_GROQ_BASE_URL,
        api_key=key_manager.current,
        temperature=temperature,
    )


# ── Tools ─────────────────────────────────────────────────────────────────────

class _SearchInput(BaseModel):
    query: str = Field(description="The search query to run against the knowledge base")


class SearchKBTool(BaseTool):
    name: str = "search_knowledge_base"
    description: str = (
        "Search the internal knowledge base of past client case studies and project work. "
        "Returns ranked text chunks with source names and relevance scores. "
        "Call this multiple times with different queries to explore different angles."
    )
    args_schema: type[BaseModel] = _SearchInput
    found_sources: list[dict] = Field(default_factory=list)  # [{name, file}]
    n_results: int = Field(default=8)
    max_per_file: int = Field(default=3)
    text_limit: int = Field(default=1000)

    def _run(self, query: str) -> str:
        try:
            chunks = retrieve(query, n_results=self.n_results, max_per_file=self.max_per_file)
        except RuntimeError as exc:
            raise  # propagate empty-DB error

        if not chunks:
            return "No relevant results found for this query."

        lines = []
        for chunk in chunks:
            display = chunk.get("display_name") or chunk["file"]
            score = chunk.get("score", 0.0)
            if not any(s["name"] == display for s in self.found_sources):
                self.found_sources.append({"name": display, "file": chunk["file"]})
            lines.append(f"[Source: {display} | relevance: {score:.3f}]")
            lines.append(chunk["text"][:self.text_limit].strip())
            lines.append("")
        return "\n".join(lines)


class _WebSearchInput(BaseModel):
    query: str = Field(description="The search query to run against the web")


class SearchWebTool(BaseTool):
    name: str = "search_web"
    description: str = (
        "Search the web for market data, industry benchmarks, client background, "
        "and external context such as industry trends, market size, or technology reports. "
        "Use this for questions about the external world — NOT for our internal project experience. "
        "For our own past work, always use search_knowledge_base instead."
    )
    args_schema: type[BaseModel] = _WebSearchInput
    found_web_sources: list[dict] = Field(default_factory=list)

    def _run(self, query: str) -> str:
        if not _TAVILY_API_KEY:
            return "Web search unavailable — TAVILY_API_KEY not configured."

        print(f"[SearchWebTool] Searching web: {query!r}")
        try:
            from tavily import TavilyClient
            results = TavilyClient(api_key=_TAVILY_API_KEY).search(
                query, max_results=5, search_depth="basic"
            )
        except Exception as exc:
            return f"Web search failed: {exc}"

        lines = []
        for r in results.get("results", []):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            source = {"name": title, "url": url}
            if source not in self.found_web_sources:
                self.found_web_sources.append(source)
            lines.append(f"[{title}]({url})")
            lines.append(content[:500].strip())
            lines.append("")

        return "\n".join(lines) or "No web results found."


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_history(history: list[dict]) -> str:
    """Format conversation history as a short context block for the LLM.

    Capped at the last 3 turns (6 messages) and 300 chars per message so it
    stays well within Groq's 12k token budget.
    """
    if not history:
        return ""
    lines = ["Conversation so far (most recent last):"]
    for msg in history[-6:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        text = (msg.get("text") or "").strip()[:300]
        if text:
            lines.append(f"  {role}: {text}")
    return "\n".join(lines) + "\n\n" if len(lines) > 1 else ""


def _is_pitch_request(query: str) -> bool:
    """Detect complex pitch/proposal requests that need full structured multi-section output."""
    q = query.lower()
    return any(kw in q for kw in [
        "pitch", "proposal", "solution approach", "implementation roadmap",
        "high-level architecture", "business outcome", "create a client",
        "generate a pitch", "write a pitch", "prepare a", "develop a pitch",
    ])


# ── Agents ────────────────────────────────────────────────────────────────────

def _build_planner(llm: LLM) -> Agent:
    return Agent(
        role="Sales Intelligence Strategist",
        goal=(
            "Analyse the user's question and produce 3–4 targeted search queries "
            "that will surface the most relevant past projects, capabilities, and experience "
            "from the knowledge base."
        ),
        backstory=(
            "You are a sales intelligence strategist who knows exactly how to find relevant past work. "
            "You break questions into focused search angles: industry experience, technical capability, "
            "client outcomes, and specific cloud/platform matches. "
            "You output a JSON search plan and nothing else."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


def _build_researcher(llm: LLM, tools: list) -> Agent:
    has_web = any(isinstance(t, SearchWebTool) for t in tools)
    goal = (
        "Execute every search query from the plan using search_knowledge_base AND search_web. "
        "Synthesise findings into two strictly separated briefs: one for internal KB facts, "
        "one for web/market context. Never mix content between the two sections."
        if has_web else
        "Execute every search query from the plan using search_knowledge_base. "
        "Synthesise all findings into an exhaustive, fact-rich research brief."
    )
    return Agent(
        role="Research Analyst",
        goal=goal,
        backstory=(
            "You are a meticulous research analyst. You run every query from the plan "
            "before writing anything. You extract specific facts: client names, cloud platforms, "
            "technologies, delivery timelines, and measurable outcomes. "
            "You never invent facts — you only report what the sources say."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


def _build_writer(llm: LLM) -> Agent:
    return Agent(
        role="Sales Intelligence Assistant",
        goal=(
            "Using only the research brief, answer the user's question directly and accurately. "
            "Output a valid JSON object with the exact schema specified."
        ),
        backstory=(
            "You are a knowledgeable sales intelligence assistant at a data & analytics consulting firm. "
            "You have deep familiarity with every past client project and delivery. "
            "You answer like a senior solutions consultant — directly, specifically, grounded in real work. "
            "You write as 'we' when referring to internal experience. "
            "You cite specific client names, technologies, and outcomes. "
            "You never use filler phrases. You never invent facts not in the research brief."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────

def _plan_task(query: str, planner: Agent, history: list[dict] = None) -> Task:
    pitch = _is_pitch_request(query)
    if pitch:
        strategy = (
            "This is a complex pitch or proposal request. Generate 5–6 targeted search queries:\n"
            "  • One query for EACH major topic or section explicitly named in the request "
            "(e.g. solution approach, architecture, governance, implementation roadmap, "
            "business outcomes, relevant experience).\n"
            "  • One query specifically for pharma/healthcare industry case studies and delivery experience.\n"
            "  • One query targeting the specific source systems and cloud platform mentioned "
            "(e.g. SAP, LIMS, MES, Salesforce, Azure, regulatory data).\n"
            "  • One query for company capabilities, credentials, and delivery differentiators.\n"
        )
        count_hint = "5–6"
    else:
        strategy = "Generate 3–4 targeted search queries to find the most relevant content.\n"
        count_hint = "3–4"

    return Task(
        description=(
            _format_history(history or [])
            + f'User request: "{query}"\n\n'
            + strategy
            + "\nFor every query, consider:\n"
            "  1. Industry or domain (e.g. pharma, FMCG, banking, automotive, healthcare)\n"
            "  2. Technical capabilities (e.g. data warehouse, ML, BI, data engineering)\n"
            "  3. Source systems named (e.g. SAP, Salesforce, LIMS, MES, Veeva, regulatory data)\n"
            "  4. Cloud platform and specific services (e.g. Azure, AWS, GCP, Microsoft Fabric)\n"
            "  5. Compliance, governance, or regulatory requirements\n"
            "  6. Measurable outcomes (e.g. supply chain visibility, compliance reporting, KPI unification)\n\n"
            "Output ONLY this JSON — no other text:\n"
            '{"queries": ["query 1", "query 2", ...]}'
        ),
        expected_output=f'A JSON object with {count_hint} queries: {{"queries": ["...", ...]}}',
        agent=planner,
    )


def _research_task(
    researcher: Agent,
    context: list[Task],
    use_web_search: bool = False,
    is_pitch: bool = False,
) -> Task:
    pitch_kb_extra = (
        "\n\nThis is a pitch/proposal request — extract with maximum depth. "
        "For EACH case study found:\n"
        "  • Client name, industry, country/geography, and scale\n"
        "  • Exact technologies and cloud services used (name every one)\n"
        "  • Specific measurable outcomes — copy percentages, volumes, and timelines verbatim from the source\n"
        "  • Which of the user's requested pitch sections (solution approach, architecture, governance, "
        "roadmap, outcomes, relevant experience) this case study most directly supports\n"
        "Do not paraphrase or summarise — extract actual facts. "
        "Explicitly flag any requested section for which the KB had no relevant content."
    ) if is_pitch else ""

    if use_web_search:
        description = (
            "Run each search query from the plan using BOTH search_knowledge_base AND search_web. "
            "Run ALL queries against both tools before synthesising — do not skip any.\n\n"
            "Output your brief in exactly these two labelled sections — no exceptions:\n\n"
            "=== INTERNAL KB BRIEF ===\n"
            "Facts from search_knowledge_base ONLY. Cover:\n"
            "  • Each relevant project — client name, industry, what was built, outcomes, metrics\n"
            "  • Technologies, cloud platforms, timelines, scale\n"
            "  • Source document names\n"
            "If no KB results found, write: No relevant internal projects found.\n"
            + pitch_kb_extra + "\n\n"
            "=== WEB RESEARCH BRIEF ===\n"
            "Context from search_web ONLY. Cover:\n"
            "  • Market size, industry trends, benchmarks\n"
            "  • Client company background if relevant\n"
            "  • Technology adoption data or analyst reports\n"
            "Always note the source title and URL for each fact.\n"
            "If no web results found, write: No relevant web context found.\n\n"
            "CRITICAL: Never move a fact from one section to the other. "
            "Never blend internal and web content."
        )
        expected_output = (
            "Two labelled sections: '=== INTERNAL KB BRIEF ===' with internal project facts, "
            "and '=== WEB RESEARCH BRIEF ===' with external market context."
        )
    else:
        description = (
            "Run each search query from the plan using search_knowledge_base. "
            "Run ALL queries before synthesising — do not skip any.\n\n"
            "Your research brief must cover:\n"
            "  • Each relevant project found — client name, industry, what was built, "
            "specific outcomes and metrics\n"
            "  • Technologies and cloud platforms mentioned across all sources\n"
            "  • Any specific timelines, scale, or volume details\n"
            "  • Which source documents contained the most relevant information\n\n"
            "Be exhaustive. Every specific fact in the sources should appear in your brief."
            + pitch_kb_extra
        )
        expected_output = (
            "A structured research brief covering all relevant projects, technologies, "
            "outcomes, and source document names."
        )

    return Task(
        description=description,
        expected_output=expected_output,
        agent=researcher,
        context=context,
    )


# ── Mode framing — sets the writer's persona and context ──────────────────────
# Each mode gets a completely different framing, not just vocabulary tweaks.
# This is what forces the LLM to produce genuinely different output per mode.

_MODE_FRAMING = {
    "ask": (
        "RESPONSE MODE: Direct Answer\n"
        "You are a senior consultant answering a colleague's question from memory. "
        "Be direct, specific, and complete — like someone who actually worked on these projects.\n"
        "A sales person reading this should immediately know: which clients, which technologies, which outcomes.\n\n"
    ),
    "pitch": (
        "RESPONSE MODE: Sales Meeting Prep\n"
        "You are preparing a sales consultant for a client meeting happening soon. "
        "Make every line count. Lead each section with the strongest claim, back it immediately with named evidence. "
        "The sales person should be able to speak confidently from each section for 2–3 minutes.\n\n"
    ),
    "pitch_executive": (
        "RESPONSE MODE: Executive Briefing\n"
        "Your audience is CEO/CFO/CDO level. They decide in the first 2 minutes whether to keep listening. "
        "Lead with business impact, not solution. Every technical element must become business language: "
        "revenue, cost, risk, time. No acronyms. No architecture. No 'data pipelines' — "
        "say 'decisions in real time' or 'reports that took 3 days now take minutes'. "
        "Write like a trusted advisor, not a vendor.\n\n"
    ),
    "pitch_technical": (
        "RESPONSE MODE: Technical Deep-Dive\n"
        "Your audience is CTOs, data engineers, and architects who will probe technical depth. "
        "Lead with HOW — pipeline design, integration patterns, specific services, architecture trade-offs. "
        "Name every technology. Include data flows and rationale for key decisions. "
        "Business outcomes anchor each section, but technical depth is the priority. "
        "Vague architecture statements ('a scalable cloud platform') are not acceptable.\n\n"
    ),
    "proposal": (
        "RESPONSE MODE: Formal Written Proposal\n"
        "This document will be sent to the client. They will read it without you present — "
        "it must stand completely alone. Every claim justified, every recommendation explained. "
        "Professional document language. Each section must be fully developed. "
        "A one-paragraph section in a formal proposal is inadequate. "
        "The reader should feel confident in our capability after reading each section.\n\n"
    ),
}

# ── Section templates per mode ────────────────────────────────────────────────

_ASK_SECTION_RULES = (
    "Structure:\n"
    "  • Single direct question → 1 section, heading=null, answer it completely.\n"
    "  • Multi-part or complex question → 2–5 sections with short, descriptive headings.\n"
    "  Calibrate to the question — only add a section when the content genuinely warrants it. "
    "Never create structure just to appear thorough. A clear focused answer beats unnecessary sections.\n\n"
)

_PITCH_GENERAL_SECTION_RULES = (
    "Structure with EXACTLY these 6 sections in this order:\n"
    "  1. Problem Understanding — their world, their pain, their constraints. "
    "Show deep understanding of their industry. Make them feel understood before you sell anything.\n"
    "  2. Recommended Approach — what we would build and why, specific to this client. "
    "Not a generic methodology — a concrete approach for their exact situation.\n"
    "  3. Relevant Experience — 2–3 named client case studies. For each: the challenge, "
    "what we built, and the specific measurable outcome. Connect each explicitly to the prospect's challenge.\n"
    "  4. Expected Business Outcomes — what changes for the client when this is live. "
    "Business terms: time saved, cost reduced, decisions improved, compliance met. "
    "Separate proven outcomes (from KB) from projections (hedged language).\n"
    "  5. Why Ganit — our specific differentiators for this engagement, backed by KB evidence. "
    "No generic 'trusted partner' language. Concrete claims only.\n"
    "  6. Key Discussion Points — 5 specific things to raise in the meeting that advance the deal. "
    "Not generic conversation topics — specific to this prospect and their situation.\n\n"
    "Each section must be substantive. Develop each point fully.\n\n"
)

_PITCH_EXECUTIVE_SECTION_RULES = (
    "Structure with EXACTLY these 7 sections in this order:\n"
    "  1. Business Context — their industry pressures, competitive landscape, and why this matters now. "
    "No technical content. Show you understand their world.\n"
    "  2. The Cost of Inaction — what staying as-is costs them. "
    "Quantify: operational risk, missed decisions, compliance exposure, manual effort, speed disadvantage.\n"
    "  3. Expected Business Outcomes — measurable results in business language only. "
    "Revenue, cost, risk, time. Zero technical terminology.\n"
    "  4. Relevant Experience — 2–3 named proof points. For each: one sentence on what the business problem was, "
    "one sentence on the measurable business result. No technical detail.\n"
    "  5. Why Ganit — our differentiators stated as business value. "
    "What we deliver that others don't, with KB evidence. Write like a trusted advisor.\n"
    "  6. Key Discussion Points — 4–5 strategic conversation starters that demonstrate "
    "you understand their business priorities and open meaningful dialogue.\n"
    "  7. Discovery Questions — 4–5 open-ended questions to uncover deeper priorities, "
    "constraints, and what a successful outcome looks like for them.\n\n"
    "Each section must be fully developed. No technical terminology anywhere.\n\n"
)

_PITCH_TECHNICAL_SECTION_RULES = (
    "Structure with EXACTLY these 6 sections in this order:\n"
    "  1. Technical Context — their current landscape: source systems, data volumes, "
    "existing tools, integration points, known technical debt. Be specific.\n"
    "  2. Architecture Overview — high-level design with components, data flow, and integration points. "
    "Include specific cloud services and patterns.\n"
    "  3. Technical Approach — exactly how we'd build it: specific services chosen and why, "
    "integration methods, data patterns (medallion, CDC, streaming vs batch), trade-offs considered.\n"
    "  4. Relevant Technical Experience — what we built for comparable clients, every technology used, "
    "performance and scale outcomes. Name every service from the KB brief.\n"
    "  5. Implementation Approach — delivery phases, key dependencies, technical risks, "
    "what we need from their team, and how we'd de-risk the critical path.\n"
    "  6. Technical Discussion Points — specific architecture decisions that need alignment in the meeting. "
    "Concrete questions about their environment and constraints.\n\n"
    "Every section must have technical depth — name specific services, patterns, and trade-offs.\n\n"
)

_PROPOSAL_SECTION_RULES = (
    "Structure with EXACTLY these 9 sections in this order:\n"
    "  1. Executive Summary — a self-contained overview: their challenge, our solution, "
    "expected outcomes, and why Ganit. A decision-maker should read only this and understand the full proposal.\n"
    "  2. Business Challenge — the client's problem in full context: operational, competitive, "
    "regulatory, and strategic dimensions. Show thorough understanding.\n"
    "  3. Relevant Experience — 2–3 named engagements with: challenge, what we built, measured outcome. "
    "Make the parallel to this engagement explicit for each.\n"
    "  4. Solution Approach — what we propose to build and why. Justify every major decision "
    "with reference to the client's specific challenge.\n"
    "  5. Technical Architecture — the design: components, data flows, integrations, "
    "technology choices with rationale. Enough detail to build confidence.\n"
    "  6. Delivery Plan — phases, milestones, timelines, team structure, client dependencies. "
    "As specific as KB evidence allows; hedge where it doesn't.\n"
    "  7. Risks & Mitigation — what could go wrong and how we'd address it. "
    "Be honest — this shows maturity and builds trust.\n"
    "  8. Benefits & Expected Outcomes — quantified results grounded in KB evidence. "
    "Clearly separate proven outcomes (from past engagements) from forward projections (hedged).\n"
    "  9. Next Steps — specific actions to move toward contract: what we need from them, "
    "what we'll produce, and a suggested timeline to decision.\n\n"
    "Every section must be fully developed. This is a sendable document — each section "
    "must stand on its own without verbal context.\n\n"
)


def _write_task(query: str, writer: Agent, context: list[Task], use_web_search: bool = False, tone: str = "pitch", history: list[dict] = None) -> Task:
    is_pitch = _is_pitch_request(query)
    mode_framing = _MODE_FRAMING.get(tone, _MODE_FRAMING["pitch"])

    base_rules = (
        "  1. NUMBER CITATION RULE (non-negotiable): Before writing any number, percentage, timeframe, or metric, "
        "verify: does this exact figure appear in the research brief? "
        "YES → use it and attribute it. NO → hedged language only: "
        "'potential benefits may include...', 'clients in similar engagements have seen...', "
        "'expected to reduce...'. Never state an inferred or estimated figure as a confirmed outcome.\n"
        "  2. Never invent clients, projects, or technologies not in the brief.\n"
        "  3. STRUCTURE for readability: **bold** for client names, technology names, and key metrics. "
        "Bullet lists (- item) for multiple items. Numbered lists for steps or sequences. "
        "Tables for comparisons. > blockquote for a standout fact or key highlight. "
        "Blank line between paragraphs. Only use structure where it genuinely helps — never for decoration.\n"
        "  4. DEPTH: Cover every relevant point in the research brief. Never truncate or skip relevant detail. "
        "Calibrate length to the complexity of the question — the LLM decides how long each section needs to be, "
        "not a word count. A short question gets a focused answer. A complex pitch gets full coverage.\n"
        "  5. SALES VALUE: Every section must give the sales person something specific to say — "
        "a named client, a concrete number, a differentiator backed by evidence. "
        "Generic statements without named proof are not acceptable.\n"
        "  6. RELEVANCE: Answer what was asked. If the question is specific, be specific. "
        "Don't pad with adjacent topics the user didn't ask about.\n"
        "  7. No filler words: 'leveraging', 'strategic', 'robust', 'seamlessly', 'end-to-end', "
        "'cutting-edge', 'best-in-class'. Specific language only.\n"
        "  8. Do NOT use backtick code formatting for product or technology names — "
        "only for actual code (SQL, CLI commands, config values).\n"
    )

    # Section structure — completely different per mode, not vocabulary tweaks
    if tone == "proposal":
        section_rules = _PROPOSAL_SECTION_RULES
    elif tone == "pitch_executive" and is_pitch:
        section_rules = _PITCH_EXECUTIVE_SECTION_RULES
    elif tone == "pitch_technical" and is_pitch:
        section_rules = _PITCH_TECHNICAL_SECTION_RULES
    elif is_pitch:  # "pitch" (general) or pitch-toned query
        section_rules = _PITCH_GENERAL_SECTION_RULES
    else:
        section_rules = _ASK_SECTION_RULES

    if use_web_search:
        source_rules = (
            "\nSOURCE ATTRIBUTION (non-negotiable):\n"
            "  KB brief → first-person only: 'We delivered X', 'In our work with Client Y, we...'\n"
            "  Web brief → always attributed inline: 'According to [Source Name]', 'Research from [Source] shows'\n"
            "  Never use 'we' for web-sourced facts. Never blend KB and web claims in the same sentence.\n"
            "  If KB and web data conflict, use KB and ignore web.\n"
        )
        sources_instruction = (
            "  9. 'sources': list ONLY the KB source names you directly cited in your response. "
            "Copy each name VERBATIM from the [Source: <name> | ...] tag in the research brief — "
            "do not paraphrase, shorten, or rename. Omit any source you did not reference.\n"
        )
    else:
        source_rules = ""
        sources_instruction = (
            "  9. 'sources': list ONLY the source names you directly cited in your response. "
            "Copy each name VERBATIM from the [Source: <name> | ...] tag in the research brief — "
            "do not paraphrase, shorten, or rename. Omit any source you did not reference.\n"
        )

    if is_pitch or tone == "proposal":
        win_strategy_rules = (
            "  10. win_strategy (internal sales guide — never shown to the client):\n"
            "     • pitch_strategy: 2–3 tactical sentences — which case study to open with and why, "
            "the key angle to lead on, and one thing to explicitly avoid saying in this meeting.\n"
            "     • value_propositions: exactly 3 concise strings, each anchored to a named KB "
            "proof point or metric, tailored to this prospect's specific challenge.\n"
            "     • objections: exactly 3 likely pushbacks "
            "(incumbent vendor, budget, compliance, team size). "
            "Every response must cite KB evidence — no generic consulting language.\n"
        )
        win_strategy_schema = (
            ', "win_strategy": {'
            '"pitch_strategy": "string", '
            '"value_propositions": ["string", "string", "string"], '
            '"objections": [{"objection": "string", "response": "string"}, '
            '{"objection": "string", "response": "string"}, '
            '{"objection": "string", "response": "string"}]}'
        )
    else:
        win_strategy_rules = ""
        win_strategy_schema = ""

    description = (
        _format_history(history or [])
        + mode_framing
        + f'User question: "{query}"\n\n'
        + "Using ONLY the research brief above, answer the user's question.\n\n"
        + section_rules
        + "Rules:\n"
        + base_rules
        + sources_instruction
        + source_rules
        + win_strategy_rules
        + "\nYOUR ENTIRE RESPONSE MUST BE A SINGLE JSON OBJECT. "
        "No preamble, no explanation, no text before or after. Start with { and end with }.\n"
        '{"sections": [{"heading": "Title or null", "content": "markdown content"}], '
        '"sources": ["Source Name 1"]'
        + win_strategy_schema
        + "}"
    )

    return Task(
        description=description,
        expected_output=(
            'A single JSON object and nothing else: '
            '{"sections": [{"heading": "string or null", "content": "string"}], '
            '"sources": ["string"]}'
        ),
        agent=writer,
        context=context,
    )


def _parse_queries(plan_result) -> list[str]:
    """Extract the query list from the planner's crew output."""
    raw = getattr(plan_result, "raw", None) or str(plan_result)
    raw = raw.strip()

    def _try(text: str) -> list[str] | None:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "queries" in parsed:
                qs = [q for q in parsed["queries"] if isinstance(q, str) and q.strip()]
                return qs or None
        except (json.JSONDecodeError, ValueError):
            return None

    result = _try(raw)
    if result:
        return result

    # Try extracting JSON object from inside surrounding text
    start, end = raw.rfind("{"), raw.rfind("}") + 1
    if start != -1 and end > start:
        result = _try(raw[start:end])
        if result:
            return result

    # Fallback: treat the whole output as one query
    return [raw[:500]] if raw else []


# ── S3: Parallel KB fetch ─────────────────────────────────────────────────────

def _parallel_kb_fetch(
    queries: list[str],
    n_results: int,
    max_per_file: int,
    text_limit: int,
) -> tuple[str, list[dict]]:
    """Run all KB searches simultaneously and return (kb_brief_text, found_sources).

    Replaces the sequential tool-call loop inside the researcher agent.
    All queries are independent so they can all start at the same time.

    Returns found_sources filtered to top 3 by average similarity score.
    """
    source_scores: dict[str, list[float]] = {}  # {display_name: [scores]}
    seen_names: set[str] = set()
    results_by_query: dict[str, list[dict]] = {}

    def _fetch_one(q: str) -> tuple[str, list[dict]]:
        try:
            return q, retrieve(q, n_results=n_results, max_per_file=max_per_file)
        except RuntimeError:
            raise  # ChromaDB empty — must propagate
        except Exception:
            return q, []

    max_workers = min(len(queries), 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, q): q for q in queries}
        for future in as_completed(futures):
            q, chunks = future.result()  # RuntimeError propagates here if DB empty
            results_by_query[q] = chunks
            for chunk in chunks:
                display = chunk.get("display_name") or chunk["file"]
                score = chunk.get("score", 0.0)
                if display not in source_scores:
                    source_scores[display] = []
                source_scores[display].append(score)
                seen_names.add(display)

    # Calculate average similarity score per source and sort by relevance
    def _normalize_score(raw_score: float) -> float:
        """Normalize cross-encoder score (-10 to 10) to 0-100 scale."""
        return max(0, min(100, ((raw_score + 10) / 20) * 100))

    source_with_scores = [
        {
            "name": display,
            "file": None,  # Will be filled from chunks
            "similarity_score": _normalize_score(sum(scores) / len(scores))
        }
        for display, scores in source_scores.items()
    ]

    # Sort by similarity score (descending) and keep top 3
    source_with_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_sources = source_with_scores[:3]

    # Fill in file paths for top sources by looking back at chunks
    top_source_names = {s["name"] for s in top_sources}
    for chunk_list in results_by_query.values():
        for chunk in chunk_list:
            display = chunk.get("display_name") or chunk["file"]
            if display in top_source_names:
                for src in top_sources:
                    if src["name"] == display and src["file"] is None:
                        src["file"] = chunk["file"]

    found_sources = top_sources

    # Format into a structured text block for the researcher
    lines = ["=== PRE-FETCHED KNOWLEDGE BASE RESULTS ===\n"]
    for q in queries:  # preserve planner's original query order
        chunks = results_by_query.get(q, [])
        lines.append(f"--- Query: {q} ---")
        if not chunks:
            lines.append("No relevant results found.\n")
            continue
        for chunk in chunks:
            display = chunk.get("display_name") or chunk["file"]
            score = chunk.get("score", 0.0)
            lines.append(f"[Source: {display} | relevance: {score:.3f}]")
            lines.append(chunk["text"][:text_limit].strip())
            lines.append("")

    return "\n".join(lines), found_sources


# ── Web pre-fetch (parallel with KB) ─────────────────────────────────────────

def _fetch_web_results(queries: list[str]) -> tuple[str, list[dict]]:
    """Run Tavily searches directly — no LLM tool call involved.

    Runs in the same ThreadPoolExecutor as _parallel_kb_fetch so neither
    adds latency to the other. Pre-fetching eliminates the live SearchWebTool
    call in the researcher, which caused the LLM to emit tool invocations as
    literal text instead of actual function calls (tool_use_failed error).
    """
    if not _TAVILY_API_KEY:
        return "Web search unavailable — TAVILY_API_KEY not configured.", []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=_TAVILY_API_KEY)
    except Exception as exc:
        return f"Web search unavailable — Tavily init failed: {exc}", []

    found_web_sources: list[dict] = []
    lines = ["=== PRE-FETCHED WEB RESULTS ===\n"]
    seen_urls: set[str] = set()

    for q in queries[:2]:  # first 2 queries are most relevant; cap to avoid token bloat
        try:
            results = client.search(q, max_results=5, search_depth="basic")
            lines.append(f"--- Web search: {q} ---")
            for r in results.get("results", []):
                title = r.get("title", "")
                url = r.get("url", "")
                content = r.get("content", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    found_web_sources.append({"name": title, "url": url})
                lines.append(f"[{title}]({url})")
                lines.append(content[:500].strip())
                lines.append("")
        except Exception as exc:
            lines.append(f"Web search failed for '{q}': {exc}\n")

    return "\n".join(lines), found_web_sources


# ── Researcher variant: pre-fetched KB + web ──────────────────────────────────

def _build_researcher_with_context(llm: LLM, use_web_search: bool = False) -> Agent:
    """Researcher agent when all context (KB + web) is pre-fetched and injected as text.
    No live tools — eliminates tool_use_failed errors caused by LLMs emitting
    tool invocations as literal text when given large pre-injected context blocks.
    """
    goal = (
        "Analyse the provided knowledge base results and pre-fetched web research. "
        "Synthesise into two strictly separated briefs: one for internal KB facts, "
        "one for web/market context. Never mix content between sections."
        if use_web_search else
        "Analyse the provided knowledge base results and synthesise them into "
        "an exhaustive, fact-rich research brief."
    )
    return Agent(
        role="Research Analyst",
        goal=goal,
        backstory=(
            "You are a meticulous research analyst. You are given pre-retrieved knowledge base results "
            "and extract specific facts: client names, cloud platforms, technologies, delivery timelines, "
            "and measurable outcomes. You never invent facts — you only report what the sources say."
        ),
        tools=[],  # all context injected as text — no live tool calls needed
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


def _research_task_with_kb_context(
    researcher: Agent,
    query: str,
    kb_context: str,
    use_web_search: bool = False,
    is_pitch: bool = False,
    web_context: str = "",
) -> Task:
    """Research task with all context (KB + web) pre-injected — zero live tool calls.

    Web results are injected alongside KB results so the researcher never needs
    to call search_web as a live tool. This eliminates the tool_use_failed error
    caused by the LLM emitting <function=search_web(...)> as literal text.
    """
    pitch_kb_extra = (
        "\n\nThis is a pitch/proposal request — extract with maximum depth. "
        "For EACH case study found:\n"
        "  • Client name, industry, country/geography, and scale\n"
        "  • Exact technologies and cloud services used (name every one)\n"
        "  • Specific measurable outcomes — copy percentages, volumes, and timelines verbatim\n"
        "  • Which of the user's requested pitch sections this case study most directly supports\n"
        "Do not paraphrase — extract actual facts. "
        "Flag any requested section for which the KB had no relevant content."
    ) if is_pitch else ""

    if use_web_search:
        description = (
            f'User query: "{query}"\n\n'
            "The knowledge base has already been searched. Results are below:\n\n"
            + kb_context
            + "\n\nWeb search results have also been pre-fetched. Results are below:\n\n"
            + (web_context or "No web results were retrieved.")
            + "\n\nSynthesise both into exactly these two labelled sections — do not call any tools:\n\n"
            "=== INTERNAL KB BRIEF ===\n"
            "Synthesise the PRE-FETCHED KNOWLEDGE BASE RESULTS above. Cover:\n"
            "  • Each relevant project — client name, industry, what was built, outcomes, metrics\n"
            "  • Technologies, cloud platforms, timelines, scale\n"
            "  • Source document names\n"
            "If no KB results found, write: No relevant internal projects found.\n"
            + pitch_kb_extra + "\n\n"
            "=== WEB RESEARCH BRIEF ===\n"
            "Synthesise the PRE-FETCHED WEB RESULTS above. Cover:\n"
            "  • Market size, industry trends, benchmarks\n"
            "  • Client company background if relevant\n"
            "  • Technology adoption data or analyst reports\n"
            "Always note the source title and URL for each fact.\n"
            "If no web results found, write: No relevant web context found.\n\n"
            "CRITICAL: Never move a fact from one section to the other. "
            "Never blend internal and web content."
        )
        expected_output = (
            "Two labelled sections: '=== INTERNAL KB BRIEF ===' with internal project facts, "
            "and '=== WEB RESEARCH BRIEF ===' with external market context."
        )
    else:
        description = (
            f'User query: "{query}"\n\n'
            "The knowledge base has already been searched. Results are below:\n\n"
            + kb_context
            + "\n\nSynthesise these results into a research brief covering:\n"
            "  • Each relevant project — client name, industry, what was built, "
            "specific outcomes and metrics\n"
            "  • Technologies and cloud platforms mentioned across all sources\n"
            "  • Any specific timelines, scale, or volume details\n"
            "  • Which source documents contained the most relevant information\n\n"
            "Be exhaustive. Every specific fact in the sources should appear in your brief."
            + pitch_kb_extra
        )
        expected_output = (
            "A structured research brief covering all relevant projects, technologies, "
            "outcomes, and source document names."
        )

    return Task(
        description=description,
        expected_output=expected_output,
        agent=researcher,
        context=[],  # KB injected directly into description — no parent task needed
    )


# ── Pipeline entry point ──────────────────────────────────────────────────────

def _run_crew_once(query: str, use_web_search: bool, tone: str, history: list[dict]) -> dict:
    """Build and execute the pipeline with whichever key is currently active.

    S3: KB searches run in parallel after planning, before the researcher runs (~4s saved).
    """
    # Mode-aware is_pitch:
    #   proposal → always full pitch retrieval (5-6 queries, n=6, verbatim extraction)
    #   ask      → never pitch retrieval (3-4 queries, n=10, direct answer framing)
    #   pitch*   → detect from query content as before
    is_pitch = (
        True if tone == "proposal"
        else False if tone == "ask"
        else _is_pitch_request(query)
    )
    llm_fast = _make_llm(temperature=0.3)
    llm_writer = _make_llm(temperature=0.45)

    # ── Query planning (always runs) ───────────────────────────────────────
    planner = _build_planner(llm_fast)
    t_plan = _plan_task(query, planner, history=history)
    plan_result = Crew(
        agents=[planner], tasks=[t_plan],
        process=Process.sequential, verbose=False, memory=False,
    ).kickoff()
    queries = _parse_queries(plan_result)

    # ── S3: Parallel KB + web fetch ───────────────────────────────────────
    # KB searches and (when enabled) web search run simultaneously.
    # Pre-fetching web results eliminates the live SearchWebTool call that was
    # causing the LLM to emit <function=search_web(...)> as literal text.
    n_results = 6 if is_pitch else 10
    if use_web_search:
        with ThreadPoolExecutor(max_workers=2) as executor:
            kb_future = executor.submit(
                _parallel_kb_fetch, queries, n_results, 3, 1000
            )
            web_future = executor.submit(_fetch_web_results, queries)
            kb_context, found_sources = kb_future.result()
            web_context, pre_fetched_web_sources = web_future.result()
    else:
        kb_context, found_sources = _parallel_kb_fetch(
            queries, n_results=n_results, max_per_file=3, text_limit=1000,
        )
        web_context, pre_fetched_web_sources = "", []

    # ── Research + Write ───────────────────────────────────────────────────
    # All context pre-injected — researcher has no live tools to call.
    researcher = _build_researcher_with_context(llm_fast, use_web_search=use_web_search)
    writer = _build_writer(llm_writer)

    t_research = _research_task_with_kb_context(
        researcher, query, kb_context,
        use_web_search=use_web_search, is_pitch=is_pitch,
        web_context=web_context,
    )
    t_write = _write_task(query, writer, context=[t_research], use_web_search=use_web_search, tone=tone, history=history)

    result = Crew(
        agents=[researcher, writer],
        tasks=[t_research, t_write],
        process=Process.sequential,
        verbose=False,
        memory=False,
    ).kickoff()

    return _parse_result(result, found_sources, pre_fetched_web_sources=pre_fetched_web_sources)


def run_crew(query: str, use_web_search: bool = False, tone: str = "balanced", history: list[dict] = None) -> dict:
    """
    Run the 3-agent pipeline and return {sections, sources, web_sources}.
    Rotates through available Groq API keys on rate-limit or quota errors.

    Raises:
        RuntimeError — if ChromaDB is empty (surfaces to the caller as 503)
    All other errors after key exhaustion are re-raised to trigger fallback.
    """
    key_manager.reset()
    while True:
        try:
            return _run_crew_once(query, use_web_search, tone, history or [])
        except RuntimeError:
            raise  # ChromaDB empty — do not rotate, surface as 503
        except Exception as exc:
            if is_rotatable_error(exc):
                if key_manager.rotate():
                    continue  # retry with next key
                raise GroqQuotaExhaustedError(
                    f"All {key_manager.pool_size} Groq API key(s) have hit their rate or quota limit. "
                    "Please try again in a few minutes."
                ) from exc
            raise  # non-rotatable error


# ── Output parsing ────────────────────────────────────────────────────────────

def _resolve_source(name: str, found_sources: list[dict]) -> dict | None:
    """Match a writer-output source name to a found_source entry.

    Tries three strategies in order:
      1. Exact string match
      2. Case-insensitive match
      3. Substring match (writer used a shorter or longer name variant)

    Returns the matched source dict (with file + similarity_score) or None if
    no match found (hallucinated source — caller should drop it).
    """
    name_l = name.lower().strip()
    # 1. Exact
    for src in found_sources:
        if src["name"] == name:
            return src
    # 2. Case-insensitive exact
    for src in found_sources:
        if src["name"].lower() == name_l:
            return src
    # 3. Substring — writer shortened or slightly renamed the source
    for src in found_sources:
        src_l = src["name"].lower()
        if name_l in src_l or src_l in name_l:
            return src
    return None


def _parse_result(
    result,
    found_sources: list[dict],
    pre_fetched_web_sources: list | None = None,
    web_tool=None,
) -> dict:
    """
    Extract {sections, sources, web_sources} from the crew result.
    Uses multiple fallback strategies so a malformed LLM response never crashes.
    Preserves similarity_score from found_sources in the output.
    """
    raw = result.raw if hasattr(result, "raw") and result.raw else str(result)
    # pre_fetched_web_sources takes priority; web_tool kept for backwards compat
    web_sources = (
        pre_fetched_web_sources if pre_fetched_web_sources is not None
        else (web_tool.found_web_sources if web_tool else [])
    )

    parsed = _extract_json(raw)
    if parsed and "sections" in parsed:
        sections = parsed["sections"]

        # Map writer-cited source names → {name, file, similarity_score}.
        # Uses fuzzy matching so name variations (shortened, casing) still resolve.
        # Sources that can't be matched (hallucinated names) are dropped — they
        # have no file path and would show as broken pills with no link.
        writer_source_names = parsed.get("sources") or []
        if writer_source_names:
            resolved = (_resolve_source(n, found_sources) for n in writer_source_names)
            sources = [s for s in resolved if s is not None]
        else:
            sources = [s for s in found_sources if s.get("file")]

        win_strategy = parsed.get("win_strategy") or None
        return {"sections": sections, "sources": sources, "web_sources": web_sources, "win_strategy": win_strategy}

    # Last resort — wrap the raw text as a plain conversational response
    return {
        "sections": [{"heading": None, "content": raw[:3000].strip()}],
        "sources": [],
        "web_sources": web_sources,
    }


def _fix_json_newlines(text: str) -> str:
    """Escape unescaped control characters inside JSON string values.

    LLMs often write literal newlines/tabs in JSON string values (which is
    invalid JSON). This walks the text character-by-character, tracking
    whether we're inside a string, and escapes any raw control chars it finds.
    """
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and in_string:
            # Already-escaped sequence — copy both chars verbatim
            result.append(c)
            i += 1
            if i < len(text):
                result.append(text[i])
        elif c == '"':
            in_string = not in_string
            result.append(c)
        elif in_string and c == "\n":
            result.append("\\n")
        elif in_string and c == "\r":
            result.append("\\r")
        elif in_string and c == "\t":
            result.append("\\t")
        else:
            result.append(c)
        i += 1
    return "".join(result)


def _try_parse(candidate: str) -> dict | None:
    """Try json.loads on the raw candidate, then on the newline-fixed version."""
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_fix_json_newlines(candidate))
    except json.JSONDecodeError:
        return None


def _extract_json(text: str) -> dict | None:
    """Find and parse a JSON object containing a 'sections' key from LLM output.

    Tries four strategies in order, each also attempting a newline-repair pass.
    The most common failure mode: LLM writes literal newlines inside JSON string
    values (markdown bullet points / paragraphs), making the JSON technically
    invalid. _fix_json_newlines handles this without any extra dependency.
    """
    text = text.strip()

    # 1. Whole output is valid JSON (or fixable JSON)
    result = _try_parse(text)
    if result is not None:
        return result

    # 2. JSON in markdown code fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        result = _try_parse(fence.group(1).strip())
        if result is not None:
            return result

    # 3. Brace-match from "sections" key — immune to { } chars in preceding prose
    idx = text.find('"sections"')
    if idx != -1:
        brace_start = text.rfind("{", 0, idx)
        if brace_start != -1:
            depth = 0
            for i, ch in enumerate(text[brace_start:]):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        result = _try_parse(text[brace_start : brace_start + i + 1])
                        if result is not None:
                            return result
                        break  # matched brace found but still invalid — stop trying

    # 4. Last resort: first { to last }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        result = _try_parse(text[start:end])
        if result is not None:
            return result

    return None
