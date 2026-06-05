import os
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tavily import TavilyClient

class CompanyResearchInput(BaseModel):
    company_name: str = Field(description="The name of the company to research")


class CompanyResearchTool(BaseTool):
    name: str = "research_company"
    description: str = (
        "Research a target company for sales intelligence. Returns industry overview, "
        "tech stack signals, recent news, hiring patterns, and potential pain points."
    )
    args_schema: type[BaseModel] = CompanyResearchInput

    def _run(self, company_name: str) -> str:
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        if not tavily_key:
            return "Company research unavailable — TAVILY_API_KEY not configured."

        tavily = TavilyClient(api_key=tavily_key)

        research_queries = [
            (f"{company_name} data analytics technology stack 2024 2025", "Tech Stack"),
            (f"{company_name} digital transformation news recent", "Recent News"),
            (f"{company_name} hiring data engineer data scientist jobs", "Hiring Signals"),
            (f"{company_name} company overview revenue industry", "Company Overview"),
        ]

        brief_sections = ["=== COMPANY INTELLIGENCE BRIEF ===", f"Company: {company_name}"]
        pain_points = []

        for query, section_name in research_queries:
            try:
                results = tavily.search(query, max_results=3, search_depth="advanced")
                brief_sections.append(f"\n--- {section_name} ---")
                for r in results.get("results", []):
                    title = r.get("title", "Unknown")
                    url = r.get("url", "")
                    content = r.get("content", "")
                    brief_sections.append(f"[{title}]({url})")
                    brief_sections.append(content[:400].strip())

                    # Deduce pain points from signals
                    pain_points.extend(_detect_pain_points(content, section_name))
            except Exception as e:
                brief_sections.append(f"\n--- {section_name} ---\nNo data found: {e}")

        if pain_points:
            brief_sections.append("\n--- DEDUCED PAIN POINTS ---")
            for pp in sorted(set(pain_points)):
                brief_sections.append(f"  • {pp}")

        return "\n".join(brief_sections)


# Signal → Pain Point mapping
_PAIN_POINT_SIGNALS = {
    "hiring data engineer": "Scaling data infrastructure — likely outgrowing current setup",
    "cloud migration": "Legacy system modernization — seeking modern cloud-native architecture",
    "data governance": "Data quality/compliance gaps — need governance framework",
    "digital transformation": "Broad transformation initiative — opportunity for analytics foundation",
    "real-time": "Need for real-time analytics — current batch processing is insufficient",
    "cost optimization": "Cloud cost pressures — need efficient architecture",
    "data silo": "Data fragmentation — need unified data platform",
    "hiring data scientist": "Building ML/AI capability — may need MLOps infrastructure",
    "regulatory": "Compliance pressure — need audit trails and data lineage",
    "customer experience": "CX improvement initiative — need customer analytics platform",
}

def _detect_pain_points(content: str, section_name: str) -> list[str]:
    content_lower = content.lower()
    return [pain for signal, pain in _PAIN_POINT_SIGNALS.items() if signal in content_lower]
