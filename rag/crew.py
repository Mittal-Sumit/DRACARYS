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
    found_sources: list[dict] = Field(default_factory=list)  # [{name, file}]

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
            if not any(s["name"] == display for s in self.found_sources):
                self.found_sources.append({"name": display, "file": chunk["file"]})
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
        "  2. No filler: avoid 'leveraging', 'strategic', 'well-positioned', 'robust'.\n"
        "  3. Be specific — cite client names, platforms, outcomes, metrics.\n"
        "  4. Answer what was actually asked. Don't expand into a full pitch unless explicitly requested.\n"
        "  5. Depth matters — give a complete, substantive answer. Don't truncate.\n"
        "  6. Use markdown in `content` to aid readability: **bold** for client names, technology names, and key metrics; "
        "bullet lists (- item) for enumerable items; numbered lists (1. item) for steps or sequences; "
        "blank line between paragraphs; > blockquote for a key highlight or standout fact. "
        "Do NOT use backtick code formatting (`...`) for product names, technology names, or project names — "
        "only use backticks for actual code: SQL snippets, CLI commands, or config values. "
        "Format purposefully — only where it genuinely helps the reader.\n"
    )

    section_rules = (
        "Structure your response:\n"
        "  • Direct question: 1 section, heading=null, answer it fully\n"
        "  • Multi-part answer: 2–3 sections with concise descriptive headings\n"
        "  • Explicit pitch/proposal request: 3–4 sections (e.g. 'Our Experience', 'Technical Approach', 'Why Us')\n"
        "  Default to fewer sections — only add one when the content genuinely warrants it.\n\n"
    )

    if use_web_search:
        source_rules = (
            "\nSOURCE ATTRIBUTION (non-negotiable):\n"
            "  KB brief → first-person only: 'We delivered X', 'In our work with Client Y, we...'\n"
            "  Web brief → always attributed inline: 'According to [Source Name]', 'Research from [Source] shows'\n"
            "  Never use 'we' for web-sourced facts. Never blend KB and web claims in the same sentence.\n"
            "  If KB and web data conflict, use KB and ignore web.\n"
        )
        sources_instruction = "  6. 'sources': list only internal KB document names cited.\n"
    else:
        source_rules = ""
        sources_instruction = "  6. 'sources': list only source document names actually cited.\n"

    description = (
        f'User question: "{query}"\n\n'
        "Using ONLY the research brief above, answer the user's question.\n\n"
        + section_rules
        + "Rules:\n"
        + base_rules
        + sources_instruction
        + source_rules
        + "\nYOUR ENTIRE RESPONSE MUST BE A SINGLE JSON OBJECT. "
        "No preamble, no explanation, no text before or after. Start with { and end with }.\n"
        '{"sections": [{"heading": "Title or null", "content": "markdown content"}], '
        '"sources": ["Source Name 1"]}'
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

        # Prefer sources reported by the writer; fall back to KB tool tracking.
        # Always show sources — even heading=null answers come from the KB.
        # Map writer source names → {name, file} using KB tool tracking so URLs work
        # for any document, regardless of whether it's registered in doc_metadata.py.
        writer_source_names = parsed.get("sources") or []
        if writer_source_names:
            found_map = {s["name"]: s for s in found_sources}
            sources = [found_map.get(n, {"name": n, "file": None}) for n in writer_source_names]
        else:
            sources = found_sources

        return {"sections": sections, "sources": sources, "web_sources": web_sources}

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
