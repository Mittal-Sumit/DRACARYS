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
_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _make_llm(temperature: float = 0.4) -> LLM:
    # Use Groq's OpenAI-compatible endpoint without a provider prefix.
    # The groq/ prefix routes through litellm's Groq provider which generates
    # hermes-style XML tool calls that Groq's API rejects. The openai path
    # uses standard JSON function calling which Groq accepts.
    return LLM(
        model=_GROQ_MODEL,
        base_url=_GROQ_BASE_URL,
        api_key=_GROQ_API_KEY,
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
    found_sources: list[str] = Field(default_factory=list)

    def _run(self, query: str) -> str:
        try:
            chunks = retrieve(query, n_results=8, max_per_file=3)
        except RuntimeError as exc:
            raise  # propagate empty-DB error

        if not chunks:
            return "No relevant results found for this query."

        lines = []
        for chunk in chunks:
            display = chunk.get("display_name") or chunk["file"]
            score = chunk.get("score", 0.0)
            if display not in self.found_sources:
                self.found_sources.append(display)
            lines.append(f"[Source: {display} | relevance: {score:.3f}]")
            lines.append(chunk["text"][:600].strip())
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


# ── Agents ────────────────────────────────────────────────────────────────────

def _build_planner(llm: LLM) -> Agent:
    return Agent(
        role="Pre-Sales Research Strategist",
        goal=(
            "Analyse the user's request and produce 3–4 targeted search queries "
            "that will surface the most relevant past projects and capabilities "
            "from the knowledge base."
        ),
        backstory=(
            "You are a pre-sales strategist who knows exactly how to find relevant past work. "
            "You break requests into focused search angles: industry experience, technical capability, "
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
        role="Senior Proposal Writer",
        goal=(
            "Using only the research brief, write a compelling, specific response. "
            "Output a valid JSON object with the exact schema specified."
        ),
        backstory=(
            "You are a senior proposal writer at a data & analytics consulting firm. "
            "You write as 'we'. You cite specific project names, technologies, and outcomes. "
            "You never use filler phrases. You write comprehensive, structured responses. "
            "You never invent clients, metrics, or technologies not found in the research brief."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────

def _plan_task(query: str, planner: Agent) -> Task:
    return Task(
        description=(
            f'User request: "{query}"\n\n'
            "Generate 3–4 targeted search queries to find the most relevant content.\n"
            "Think about:\n"
            "  1. The industry or domain (e.g. pharma, FMCG, banking, automotive, healthcare)\n"
            "  2. Technical capabilities needed (e.g. data warehouse, ML, BI, data engineering)\n"
            "  3. Similar past outcomes (e.g. demand forecasting, predictive maintenance)\n"
            "  4. Cloud or platform mentioned (e.g. Azure, AWS, GCP, Microsoft Fabric)\n\n"
            "Output ONLY this JSON — no other text:\n"
            '{"queries": ["query 1", "query 2", "query 3"]}'
        ),
        expected_output='A JSON object: {"queries": ["...", "...", "..."]}',
        agent=planner,
    )


def _research_task(researcher: Agent, context: list[Task], use_web_search: bool = False) -> Task:
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
            "If no KB results found, write: No relevant internal projects found.\n\n"
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


def _write_task(query: str, writer: Agent, context: list[Task], use_web_search: bool = False) -> Task:
    base_rules = (
        "  1. Never invent clients, projects, metrics, or technologies not in the brief.\n"
        "  2. No filler: avoid 'leveraging', 'strategic', 'well-positioned'.\n"
        "  3. Be specific — cite project names, platforms, outcomes, metrics.\n"
        "  4. Comprehensive answers beat brief ones. Do not truncate proposals.\n"
    )

    if use_web_search:
        source_rules = (
            "\nSOURCE ATTRIBUTION RULES (non-negotiable):\n"
            "  KB BRIEF → first-person claims only: 'We delivered X', 'We built Y for Client Z'.\n"
            "  WEB BRIEF → always attributed: 'According to [Source Name]', 'Industry data shows', "
            "'Research from [Source] indicates'. Never write 'we' using web data.\n"
            "  Never use web data to support, inflate, or contradict KB claims.\n"
            "  Web context belongs only in sections about market landscape, industry context, "
            "or client background — never in sections about our capabilities or past work.\n"
            "  If web and KB data conflict on any point, use KB and ignore the web data.\n"
        )
        sources_instruction = (
            "  5. 'sources': list only internal KB document names cited (not web URLs).\n"
        )
    else:
        source_rules = ""
        sources_instruction = "  5. Sources: list only source document names actually cited.\n"

    description = (
        f'Original user request: "{query}"\n\n'
        "Using ONLY the research brief above, write the response.\n\n"
        "Choose response type based on the request:\n"
        "  PROPOSAL (e.g. 'generate a proposal', 'draft a pitch', 'write a proposal for X'):\n"
        "    → 3–5 sections. Choose headings that fit THIS specific request.\n"
        "    → Examples: 'Our Approach', 'Relevant Experience', 'Technical Architecture',\n"
        "       'Why We're the Right Partner', 'What We've Delivered'\n"
        "  QUESTION (e.g. 'what experience do we have with X', 'have we done Y work'):\n"
        "    → 1–2 sections answering directly with specific evidence\n"
        "  CONVERSATIONAL (e.g. 'what can you do', 'tell me about the firm'):\n"
        "    → 1–2 short paragraphs. Set heading to null.\n\n"
        "Rules:\n"
        + base_rules
        + sources_instruction
        + source_rules
        + "\nOutput ONLY this JSON (no markdown code fences, no text outside the JSON):\n"
        '{"sections": [{"heading": "Title or null", "content": "..."}], '
        '"sources": ["Source Name 1", "Source Name 2"]}'
    )

    return Task(
        description=description,
        expected_output=(
            'JSON: {"sections": [{"heading": "string or null", "content": "string"}], '
            '"sources": ["string"]}'
        ),
        agent=writer,
        context=context,
    )


# ── Pipeline entry point ──────────────────────────────────────────────────────

def run_crew(query: str, use_web_search: bool = False) -> dict:
    """
    Run the 3-agent pipeline and return {sections, sources, web_sources}.

    Raises:
        RuntimeError — if ChromaDB is empty (surfaces to the caller as 503)
    All other agent/LLM errors are caught by the caller and trigger fallback.
    """
    llm_fast = _make_llm(temperature=0.3)
    llm_writer = _make_llm(temperature=0.45)
    kb_tool = SearchKBTool()
    web_tool = SearchWebTool() if use_web_search else None

    tools = [kb_tool] + ([web_tool] if web_tool else [])

    planner = _build_planner(llm_fast)
    researcher = _build_researcher(llm_fast, tools)
    writer = _build_writer(llm_writer)

    t_plan = _plan_task(query, planner)
    t_research = _research_task(researcher, context=[t_plan], use_web_search=use_web_search)
    t_write = _write_task(query, writer, context=[t_research], use_web_search=use_web_search)

    crew = Crew(
        agents=[planner, researcher, writer],
        tasks=[t_plan, t_research, t_write],
        process=Process.sequential,
        verbose=False,
        memory=False,
    )

    result = crew.kickoff()
    return _parse_result(result, kb_tool.found_sources, web_tool)


# ── Output parsing ────────────────────────────────────────────────────────────

def _parse_result(result, found_sources: list[str], web_tool=None) -> dict:
    """
    Extract {sections, sources, web_sources} from the crew result.
    Uses multiple fallback strategies so a malformed LLM response never crashes.
    """
    raw = result.raw if hasattr(result, "raw") and result.raw else str(result)
    web_sources = web_tool.found_web_sources if web_tool else []

    parsed = _extract_json(raw)
    if parsed and "sections" in parsed:
        sections = parsed["sections"]
        has_headings = any(s.get("heading") for s in sections)

        # Prefer sources reported by the writer; fall back to KB tool tracking
        writer_sources = parsed.get("sources") or []
        sources = writer_sources if writer_sources else (found_sources if has_headings else [])

        return {"sections": sections, "sources": sources, "web_sources": web_sources}

    # Last resort — wrap the raw text as a plain conversational response
    return {
        "sections": [{"heading": None, "content": raw[:3000].strip()}],
        "sources": [],
        "web_sources": web_sources,
    }


def _extract_json(text: str) -> dict | None:
    """Try three strategies to find valid JSON in LLM output."""
    text = text.strip()

    # 1. The whole output is valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. JSON wrapped in markdown code fences (```json ... ```)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the outermost {...} block — first { to matching }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return None
