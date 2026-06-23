import io
import json
import re
from typing import Any

import structlog

log = structlog.get_logger()


class ResumeParser:
    async def parse(self, content: bytes, filename: str) -> dict[str, Any]:
        raw_text = self._extract_text(content, filename)
        return await self._parse_with_ai(raw_text)

    def _extract_text(self, content: bytes, filename: str) -> str:
        if filename.lower().endswith(".pdf"):
            return self._extract_pdf(content)
        if filename.lower().endswith(".docx"):
            return self._extract_docx(content)
        return content.decode("utf-8", errors="ignore")

    def _extract_pdf(self, content: bytes) -> str:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            log.warning("PDF extraction failed", error=str(e))
            return ""

    def _extract_docx(self, content: bytes) -> str:
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            log.warning("DOCX extraction failed", error=str(e))
            return ""

    async def _parse_with_ai(self, text: str) -> dict[str, Any]:
        from app.core.config import settings

        if not settings.OPENAI_API_KEY or not text.strip():
            return self._fallback_parse(text)

        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = f"""Extract structured information from this resume.

Return JSON with:
- skills: array of technical skills (programming languages, tools, frameworks, cloud services)
- experience_years: total years of professional experience (number)
- education: array of objects with {{degree, institution, year}}
- certifications: array of certification names
- projects: array of objects with {{name, description, technologies}}

Resume text:
{text[:4000]}"""

            response = await client.chat.completions.create(
                model=settings.AI_MODEL_PRIMARY,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            return {
                "raw_text": text,
                "skills": data.get("skills", []),
                "experience_years": float(data.get("experience_years", 0)),
                "education": data.get("education", []),
                "certifications": data.get("certifications", []),
                "projects": data.get("projects", []),
            }
        except Exception as e:
            log.error("AI resume parsing failed", error=str(e))
            return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> dict[str, Any]:
        tech_keywords = [
            "python", "java", "javascript", "typescript", "sql", "aws", "gcp", "azure",
            "docker", "kubernetes", "react", "node", "fastapi", "django", "flask",
            "snowflake", "airflow", "spark", "kafka", "redis", "postgresql", "mongodb",
            "terraform", "ansible", "git", "linux", "dbt", "bigquery",
        ]
        text_lower = text.lower()
        found_skills = [kw for kw in tech_keywords if kw in text_lower]

        years_match = re.findall(r"(\d+)\+?\s*years?", text_lower)
        exp_years = max((int(y) for y in years_match), default=0)

        return {
            "raw_text": text,
            "skills": found_skills,
            "experience_years": float(min(exp_years, 40)),
            "education": [],
            "certifications": [],
            "projects": [],
        }
