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

try:
    # CrewAI 1.14+ marks every message with cache_breakpoint for Anthropic prompt caching.
    # Groq rejects requests that contain this field. Patch it out before any agent runs.
    import crewai.llms.cache as _crewai_cache
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg
except ImportError:
    pass

import threading

_local_registry = threading.local()

class ProgressCallbackScope:
    def __init__(self, callback):
        self.callback = callback

    def __enter__(self):
        _local_registry.callback = self.callback
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(_local_registry, 'callback'):
            del _local_registry.callback

def send_progress_update(stage: str, message: str):
    callback = getattr(_local_registry, 'callback', None)
    if callback:
        try:
            callback(stage, message)
        except Exception:
            pass

def make_task_callback(next_stage: str, next_msg: str):
    def callback(output):
        send_progress_update(next_stage, next_msg)
    return callback

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import BaseTool

from rag.groq_keys import get_groq_api_keys, is_groq_limit_error
from rag.retriever import retrieve
from rag.tools.person_research import PersonResearchTool
from rag.tools.company_research import CompanyResearchTool

_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _make_llm(api_key: str, temperature: float = 0.4) -> LLM:
    # Use Groq's OpenAI-compatible endpoint without a provider prefix.
    # The groq/ prefix routes through litellm's Groq provider which generates
    # hermes-style XML tool calls that Groq's API rejects. The openai path
    # uses standard JSON function calling which Groq accepts.
    return LLM(
        model=_GROQ_MODEL,
        base_url=_GROQ_BASE_URL,
        api_key=api_key,
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
        send_progress_update("kb_research", f"Searching knowledge base for '{query}'...")
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
        send_progress_update("web_research", f"Searching web for '{query}'...")
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


def _build_writer(llm: LLM, tone: str = "balanced", output_format: str = "proposal") -> Agent:
    from rag.prompts import TONE_INSTRUCTIONS
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["balanced"])
    if output_format == "email":
        goal = (
            "Using only the research brief, write a compelling, personalized cold outreach email. "
            "Output a valid JSON object with subject, body, and sources."
        )
    elif output_format == "meeting_brief":
        goal = (
            "Using only the research brief, prepare a structured meeting preparation brief. "
            "Output a valid JSON object with the exact schema specified."
        )
    elif output_format == "one_pager":
        goal = (
            "Using only the research brief, write a concise one-page pitch. "
            "Output a valid JSON object with the exact schema specified."
        )
    else:
        goal = (
            "Using only the research brief, write a compelling, specific response. "
            "Output a valid JSON object with the exact schema specified."
        )

    return Agent(
        role="Senior Proposal Writer",
        goal=goal,
        backstory=(
            "You are a senior proposal writer at a data & analytics consulting firm. "
            "You write as 'we'. You cite specific project names, technologies, and outcomes. "
            "You never use filler phrases. You write comprehensive, structured responses. "
            "You never invent clients, metrics, or technologies not found in the research brief.\n\n"
            f"{tone_instruction}"
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


def _build_person_researcher(llm: LLM) -> Agent:
    return Agent(
        role="Person Research Specialist",
        goal="Research key client stakeholders using LinkedIn and web search to extract background, experiences, and personalized icebreakers.",
        backstory=(
            "You are an expert executive recruiter and pre-sales personalization specialist. "
            "You look up people, analyze their history, and deduce what they care about "
            "so our proposal is tailored directly to their persona."
        ),
        tools=[PersonResearchTool()],
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


def _build_company_researcher(llm: LLM) -> Agent:
    return Agent(
        role="Company Intelligence Analyst",
        goal="Analyze target companies for sales intelligence, tech stacks, hiring trends, and pain points using web search.",
        backstory=(
            "You are a corporate intelligence analyst. You study companies, read between the lines "
            "of recent news, identify hiring patterns, and map their technology stack. "
            "You deduce their pain points so we can pitch highly targeted solutions."
        ),
        tools=[CompanyResearchTool()],
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────

def _plan_task(query: str, planner: Agent, conversation_context: str = "") -> Task:
    context_str = f"Conversation Context (previous messages):\n{conversation_context}\n\n" if conversation_context else ""
    return Task(
        description=(
            f"{context_str}"
            f'User request: "{query}"\n\n'
            "Generate 3–4 targeted search queries to find the most relevant content.\n"
            "If the request refers to previous topics, use the conversation context to resolve pronouns or context.\n"
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


def _person_research_task(researcher: Agent, person_name: str, company_name: str = "") -> Task:
    desc = (
        f"Research the professional profile of '{person_name}' associated with company '{company_name or 'Unknown'}'. "
        "Use research_person tool to extract their title, location, experience summary, key skills, "
        "and any external context like blog posts or articles. "
        "Format this as a Person Intelligence Brief."
    )
    return Task(
        description=desc,
        expected_output="A structured Person Intelligence Brief outlining stakeholder background, experiences, and interests.",
        agent=researcher,
    )


def _company_research_task(researcher: Agent, company_name: str) -> Task:
    desc = (
        f"Research the target company '{company_name}'. "
        "Use research_company tool to study their industry overview, technology stack, "
        "recent news, and hiring patterns. Deduce their business pain points from these signals. "
        "Format this as a Company Intelligence Brief."
    )
    return Task(
        description=desc,
        expected_output="A structured Company Intelligence Brief detailing technology stack, news, hiring, and deduced pain points.",
        agent=researcher,
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


def _write_task(query: str, writer: Agent, context: list[Task], use_web_search: bool = False, tone: str = "balanced", person_name: str = None, company_name: str = None, output_format: str = "proposal") -> Task:
    from rag.prompts import TONE_INSTRUCTIONS
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["balanced"])
    base_rules = (
        "  1. Never invent clients, projects, metrics, or technologies not in the brief.\n"
        "  2. No filler: avoid 'leveraging', 'strategic', 'well-positioned'.\n"
        "  3. Be specific — cite project names, platforms, outcomes, metrics.\n"
        "  4. Comprehensive answers beat brief ones. Do not truncate proposals.\n"
        "  6. CROSS-DOMAIN ANALOGIES: When citing projects from a different industry than the target client's, explicitly frame them as transferable. Explain why the same solution pattern or technical approach applies directly (e.g. 'While this was delivered for Client A in industry X, the same dynamic pricing pipeline structure applies directly to your retail challenge because...').\n"
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

    personalization = ""
    if person_name or company_name:
        personalization = (
            "\nPERSONALIZATION & SALES INTELLIGENCE INSTRUCTIONS:\n"
            f"You are preparing a personalized pitch for a specific prospect: {person_name or 'Unknown'} at {company_name or 'the target company'}.\n"
            "Use the Person Intelligence Brief and/or Company Intelligence Brief in your context to:\n"
            "  - Align the Solution Approach and Technical Architecture with their tech stack and deduced pain points.\n"
            "  - Personalize the Executive Summary and Next Steps to address the stakeholder's role, background, and likely concerns.\n"
            "  - Make the proposal feel customized specifically for them while relying strictly on our actual past experience for proof points (never invent past experience).\n\n"
        )

    # Format specific response structure
    if output_format == "email":
        format_structure = (
            "Generate a cold outreach email.\n"
            "Guidelines: Keep under 200 words. Lead with their pain point, not our capability. "
            "End with a specific ask (e.g., a 15-minute call, not 'let me know').\n\n"
            "Output ONLY this JSON (no markdown code fences, no text outside the JSON):\n"
            '{\n'
            '  "subject": "Compelling subject line",\n'
            '  "body": "Full email with personalized opening, value proposition, and clear CTA",\n'
            '  "sources": ["Source Name 1", "Source Name 2"]\n'
            '}'
        )
        expected_output = (
            'JSON: {"subject": "string", "body": "string", "sources": ["string"]}'
        )
    elif output_format == "meeting_brief":
        format_structure = (
            "Generate a meeting preparation brief.\n"
            "Guidelines: Use exactly these section headers:\n"
            "  1. Meeting Objective\n"
            "  2. Attendee Background\n"
            "  3. Talking Points\n"
            "  4. Relevant Case Studies\n"
            "  5. Discovery Questions\n"
            "  6. Next Steps\n\n"
            "Output ONLY this JSON (no markdown code fences, no text outside the JSON):\n"
            '{\n'
            '  "sections": [\n'
            '    {"heading": "Meeting Objective", "content": "..."},\n'
            '    {"heading": "Attendee Background", "content": "..."},\n'
            '    {"heading": "Talking Points", "content": "..."},\n'
            '    {"heading": "Relevant Case Studies", "content": "..."},\n'
            '    {"heading": "Discovery Questions", "content": "..."},\n'
            '    {"heading": "Next Steps", "content": "..."}\n'
            '  ],\n'
            '  "sources": ["Source Name 1", "Source Name 2"]\n'
            '}'
        )
        expected_output = (
            'JSON: {"sections": [{"heading": "string", "content": "string"}], "sources": ["string"]}'
        )
    elif output_format == "one_pager":
        format_structure = (
            "Generate a concise one-page pitch.\n"
            "Guidelines: Use exactly these section headers:\n"
            "  1. The Opportunity (2-3 sentences on the client's challenge)\n"
            "  2. Our Approach (3-4 sentences on how we'd solve it)\n"
            "  3. Proof Points (2-3 bullet points citing specific past projects with metrics)\n"
            "  4. Why Us (2-3 key differentiators)\n"
            "  5. Next Step (One clear action item)\n\n"
            "Output ONLY this JSON (no markdown code fences, no text outside the JSON):\n"
            '{\n'
            '  "sections": [\n'
            '    {"heading": "The Opportunity", "content": "..."},\n'
            '    {"heading": "Our Approach", "content": "..."},\n'
            '    {"heading": "Proof Points", "content": "..."},\n'
            '    {"heading": "Why Us", "content": "..."},\n'
            '    {"heading": "Next Step", "content": "..."}\n'
            '  ],\n'
            '  "sources": ["Source Name 1", "Source Name 2"]\n'
            '}'
        )
        expected_output = (
            'JSON: {"sections": [{"heading": "string", "content": "string"}], "sources": ["string"]}'
        )
    else: # proposal
        format_structure = (
            "Generate a proposal.\n"
            "Guidelines: Use these section headers WHERE APPLICABLE (skip irrelevant ones):\n"
            "  1. Executive Summary\n"
            "  2. Business Challenge\n"
            "  3. Relevant Experience\n"
            "  4. Solution Approach\n"
            "  5. Technical Architecture\n"
            "  6. Delivery Plan\n"
            "  7. Risks & Mitigation\n"
            "  8. Benefits\n"
            "  9. Next Steps\n\n"
            "Output ONLY this JSON (no markdown code fences, no text outside the JSON):\n"
            '{\n'
            '  "sections": [\n'
            '    {"heading": "Executive Summary", "content": "..."},\n'
            '    {"heading": "Relevant Experience", "content": "..."}\n'
            '  ],\n'
            '  "sources": ["Source Name 1", "Source Name 2"]\n'
            '}'
        )
        expected_output = (
            'JSON: {"sections": [{"heading": "string", "content": "string"}], "sources": ["string"]}'
        )

    description = (
        f'Original user request: "{query}"\n\n'
        "Using ONLY the research brief and intelligence briefs above, write the response.\n\n"
        + personalization
        + f"Tone Instructions: {tone_instruction}\n\n"
        + "Response Structure & Format:\n"
        + format_structure + "\n\n"
        + "Rules:\n"
        + base_rules
        + sources_instruction
        + source_rules
    )

    return Task(
        description=description,
        expected_output=expected_output,
        agent=writer,
        context=context,
    )


# ── Pipeline entry point ──────────────────────────────────────────────────────

def run_crew(query: str, use_web_search: bool = False, tone: str = "balanced", person_name: str = None, company_name: str = None, output_format: str = "proposal", conversation_context: str = "") -> dict:
    """
    Run the multi-agent pipeline and return {sections, sources, web_sources}.

    Raises:
        RuntimeError — if ChromaDB is empty (surfaces to the caller as 503)
    All other agent/LLM errors are caught by the caller and trigger fallback.
    """
    keys = get_groq_api_keys()
    if not keys:
        raise ValueError("GROQ_API_KEY not found in .env file")

    last_limit_error: Exception | None = None
    for api_key in keys:
        try:
            return _run_crew_with_key(
                query,
                api_key,
                use_web_search=use_web_search,
                tone=tone,
                person_name=person_name,
                company_name=company_name,
                output_format=output_format,
                conversation_context=conversation_context,
            )
        except Exception as exc:
            if not is_groq_limit_error(exc):
                raise
            last_limit_error = exc

    raise RuntimeError("All configured Groq API keys are exhausted or rate-limited.") from last_limit_error


def _run_crew_with_key(query: str, api_key: str, use_web_search: bool = False, tone: str = "balanced", person_name: str = None, company_name: str = None, output_format: str = "proposal", conversation_context: str = "") -> dict:
    llm_fast = _make_llm(api_key, temperature=0.3)
    llm_writer = _make_llm(api_key, temperature=0.45)
    kb_tool = SearchKBTool()
    web_tool = SearchWebTool() if use_web_search else None

    # Check if we are in Pitch Prep mode (either person_name or company_name is provided)
    is_pitch_prep = bool(person_name or company_name)

    if is_pitch_prep:
        # Pitch Prep mode (up to 5 agents)
        planner = _build_planner(llm_fast)
        writer = _build_writer(llm_writer, tone=tone, output_format=output_format)
        kb_researcher = _build_researcher(llm_fast, [kb_tool])

        agents = [planner]
        t_plan = _plan_task(query, planner, conversation_context=conversation_context)
        t_plan.callback = make_task_callback("researching", "Search plan generated. Beginning KB and web research...")
        tasks = [t_plan]
        context_for_writer = []

        if person_name:
            person_researcher = _build_person_researcher(llm_fast)
            t_person = _person_research_task(person_researcher, person_name, company_name)
            t_person.callback = make_task_callback("researching", "Stakeholder intelligence gathered. Continuing research...")
            agents.append(person_researcher)
            tasks.append(t_person)
            context_for_writer.append(t_person)

        if company_name:
            company_researcher = _build_company_researcher(llm_fast)
            t_company = _company_research_task(company_researcher, company_name)
            t_company.callback = make_task_callback("researching", "Company intelligence gathered. Continuing research...")
            agents.append(company_researcher)
            tasks.append(t_company)
            context_for_writer.append(t_company)

        # Standard KB research task
        t_kb = _research_task(kb_researcher, context=[t_plan], use_web_search=False)
        t_kb.callback = make_task_callback("writing", "Research phase complete. Synthesizing findings and writing final response...")
        agents.append(kb_researcher)
        tasks.append(t_kb)
        context_for_writer.append(t_kb)

        # Proposal writer task
        t_write = _write_task(
            query,
            writer,
            context=context_for_writer,
            use_web_search=use_web_search,
            tone=tone,
            person_name=person_name,
            company_name=company_name,
            output_format=output_format,
        )
        agents.append(writer)
        tasks.append(t_write)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
            memory=False,
        )
        result = crew.kickoff()
        return _parse_result(result, kb_tool.found_sources, web_tool, output_format=output_format)

    else:
        # Standard proposal mode (3 agents)
        tools = [kb_tool] + ([web_tool] if web_tool else [])

        planner = _build_planner(llm_fast)
        researcher = _build_researcher(llm_fast, tools)
        writer = _build_writer(llm_writer, tone=tone, output_format=output_format)

        t_plan = _plan_task(query, planner, conversation_context=conversation_context)
        t_plan.callback = make_task_callback("researching", "Search plan generated. Beginning KB and web research...")

        t_research = _research_task(researcher, context=[t_plan], use_web_search=use_web_search)
        t_research.callback = make_task_callback("writing", "Research phase complete. Synthesizing findings and writing final response...")

        t_write = _write_task(
            query,
            writer,
            context=[t_research],
            use_web_search=use_web_search,
            tone=tone,
            output_format=output_format,
        )

        crew = Crew(
            agents=[planner, researcher, writer],
            tasks=[t_plan, t_research, t_write],
            process=Process.sequential,
            verbose=False,
            memory=False,
        )

        result = crew.kickoff()
        return _parse_result(result, kb_tool.found_sources, web_tool, output_format=output_format)


# ── Output parsing ────────────────────────────────────────────────────────────

def _parse_result(result, found_sources: list[str], web_tool=None, output_format: str = "proposal") -> dict:
    """
    Extract {sections, sources, web_sources} (or {subject, body, sources, web_sources} for emails) from the crew result.
    Uses multiple fallback strategies so a malformed LLM response never crashes.
    """
    raw = result.raw if hasattr(result, "raw") and result.raw else str(result)
    web_sources = web_tool.found_web_sources if web_tool else []

    parsed = _extract_json(raw)
    if output_format == "email":
        if parsed and ("subject" in parsed or "body" in parsed):
            subject = parsed.get("subject", "Proposal Outreach")
            body = parsed.get("body", "")
            writer_sources = parsed.get("sources") or []
            sources = writer_sources if writer_sources else found_sources
            return {"subject": subject, "body": body, "sources": sources, "web_sources": web_sources}
        return {
            "subject": "Proposal Outreach",
            "body": raw[:3000].strip(),
            "sources": [],
            "web_sources": web_sources,
        }

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
