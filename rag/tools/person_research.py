import os
import re
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tavily import TavilyClient
from apify_client import ApifyClient

class PersonResearchInput(BaseModel):
    person_name: str = Field(description="The full name of the person to research")
    designation: str = Field(default="", description="The professional title/designation of the person")
    company: str = Field(default="", description="The company the person is associated with")


class PersonResearchTool(BaseTool):
    name: str = "research_person"
    description: str = (
        "Research a person's professional background using their name and designation. "
        "Returns role, experience, interests, publications, and personalized talking points. "
        "Use this to personalize pitches for specific decision-makers."
    )
    args_schema: type[BaseModel] = PersonResearchInput

    def _run(self, person_name: str, designation: str = "", company: str = "") -> str:
        # Load keys
        apify_key = os.getenv("APIFY_API_KEY", "")
        tavily_key = os.getenv("TAVILY_API_KEY", "")

        profile = {}

        # 1. Try Apify LinkedIn scraper
        if apify_key:
            try:
                profile = _apify_linkedin_lookup(person_name, company, apify_key, tavily_key)
            except Exception as e:
                print(f"[PersonResearchTool] Apify LinkedIn lookup failed: {e}")

        # 2. Tavily web search for broader context
        web_context = ""
        if tavily_key:
            try:
                web_context = _tavily_person_search(person_name, designation, company, tavily_key)
            except Exception as e:
                web_context = f"Web search failed: {e}"
        else:
            web_context = "Tavily API key not configured."

        # 3. Structure into actionable intelligence
        return _format_person_brief(profile, web_context)


def _extract_linkedin_url(search_results: dict) -> str | None:
    for r in search_results.get("results", []):
        url = r.get("url", "")
        if "linkedin.com/in/" in url:
            match = re.search(r'(https?://[a-z]+\.linkedin\.com/in/[a-zA-Z0-9_\-%]+)', url)
            if match:
                return match.group(1)
    return None


def _apify_linkedin_lookup(name: str, company: str, apify_key: str, tavily_key: str) -> dict:
    """Use Apify LinkedIn scraper actor to get profile data."""
    if not tavily_key:
        return {}

    # Find LinkedIn URL via Tavily search
    search_query = f"{name} {company} site:linkedin.com/in"
    search_results = TavilyClient(api_key=tavily_key).search(
        search_query, max_results=3
    )
    linkedin_url = _extract_linkedin_url(search_results)
    if not linkedin_url:
        return {}

    client = ApifyClient(apify_key)
    run = client.actor("curious_coder/linkedin-profile-scraper").call(
        run_input={"urls": [linkedin_url]}
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return items[0] if items else {}


def _tavily_person_search(name: str, designation: str, company: str, tavily_key: str) -> str:
    tavily = TavilyClient(api_key=tavily_key)
    queries = [
        f"{name} {designation} {company} professional background experience",
        f"{name} {company} blog publications speaking presentations",
        f"{name} {designation} interests data analytics technology",
    ]
    results = []
    for q in queries:
        try:
            r = tavily.search(q, max_results=3)
            results.extend(r.get("results", []))
        except Exception:
            continue

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in results:
        url = r.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    return "\n".join(f"[{r.get('title', 'Unknown')}]({r.get('url', '')})\n{r.get('content', '')[:300]}" for r in unique_results[:5])


def _format_person_brief(linkedin_profile: dict, web_context: str) -> str:
    """Format into a structured person intelligence brief."""
    lines = ["=== PERSON INTELLIGENCE BRIEF ==="]
    if linkedin_profile:
        lines.append(f"Name: {linkedin_profile.get('fullName', 'N/A')}")
        lines.append(f"Title: {linkedin_profile.get('headline', 'N/A')}")
        lines.append(f"Location: {linkedin_profile.get('location', 'N/A')}")
        lines.append(f"Summary: {linkedin_profile.get('summary', 'N/A')[:500]}")
        # Experience
        exp_list = linkedin_profile.get("experience", []) or []
        if exp_list:
            lines.append("Professional Experience:")
            for exp in exp_list[:3]:
                title = exp.get('title', '')
                comp = exp.get('company', '')
                dur = exp.get('duration', '')
                lines.append(f"  • {title} at {comp} ({dur})")
        # Skills/Interests
        skills = linkedin_profile.get("skills", []) or []
        if skills:
            lines.append(f"Key Skills: {', '.join(skills[:10])}")

    lines.append("\n--- Additional Web Context ---")
    lines.append(web_context[:2000])
    return "\n".join(lines)
