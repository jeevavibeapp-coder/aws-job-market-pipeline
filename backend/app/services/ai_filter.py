from __future__ import annotations
import json
from dataclasses import dataclass

import openai
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.job_scorer import compute_competition_score

log = structlog.get_logger()


@dataclass
class ExperienceMatch:
    status: str  # "accept", "warning", "reject"
    score: float  # 0-100
    reason: str


class AIJobFilter:
    def __init__(self) -> None:
        self._client: openai.AsyncOpenAI | None = None

    @property
    def client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def check_experience_match(
        self,
        job_exp_min: float | None,
        job_exp_max: float | None,
        user_exp: float,
        tolerance: float = 1.0,
    ) -> ExperienceMatch:
        """Core experience-matching rule.

        Accept  : required <= user_exp + tolerance
        Warning : required <= user_exp + tolerance * 2
        Reject  : required >  user_exp + tolerance * 2
        """
        if job_exp_min is None:
            return ExperienceMatch(status="accept", score=80, reason="No experience requirement specified")

        if job_exp_min <= user_exp + tolerance:
            score = 100 - max(0, (job_exp_min - user_exp) * 10)
            return ExperienceMatch(
                status="accept",
                score=min(100, max(60, score)),
                reason=f"Requires {job_exp_min}+ yrs, you have {user_exp} yrs",
            )

        if job_exp_min <= user_exp + tolerance * 2:
            return ExperienceMatch(
                status="warning",
                score=45,
                reason=f"Requires {job_exp_min}+ yrs, slightly above your {user_exp} yrs",
            )

        return ExperienceMatch(
            status="reject",
            score=0,
            reason=f"Requires {job_exp_min}+ yrs, too senior for your {user_exp} yrs",
        )

    def _keyword_skill_match(self, job_skills: list[str], user_skills: list[str]) -> tuple[float, list[str]]:
        if not job_skills:
            return 70.0, []
        user_lower = {s.lower() for s in user_skills}
        matched = [s for s in job_skills if s.lower() in user_lower]
        score = round(len(matched) / len(job_skills) * 100, 1)
        return score, matched

    def _location_match(self, job_location: str | None, target_locations: list[str]) -> float:
        if not job_location or not target_locations:
            return 70.0
        job_loc_lower = job_location.lower()
        for loc in target_locations:
            if loc.lower() in job_loc_lower or job_loc_lower in loc.lower():
                return 100.0
        if "remote" in job_loc_lower:
            return 90.0
        return 30.0

    @staticmethod
    def _company_name(job) -> str:
        company = getattr(job, "company", None)
        return company.name if company is not None else "Unknown"

    async def filter_and_score(self, jobs: list, profile, search) -> list[dict]:
        user_exp = search.experience_years
        user_skills = search.skills or (profile.parsed_skills if profile else [])
        target_locations = search.locations
        tolerance = search.experience_tolerance
        min_score = search.min_score

        results: list[dict] = []
        for job in jobs:
            exp_match = self.check_experience_match(
                job.experience_min, job.experience_max, user_exp, tolerance
            )
            if exp_match.status == "reject":
                continue

            skill_score, matched_skills = self._keyword_skill_match(
                job.skills_required or [], user_skills
            )
            location_score = self._location_match(job.location, target_locations)
            # Technology match leans on the same skill overlap but is more forgiving.
            technology_score = min(100.0, skill_score + 20) if matched_skills else 60.0
            seniority_score = 80.0

            overall = (
                skill_score * 0.35
                + exp_match.score * 0.25
                + technology_score * 0.20
                + location_score * 0.10
                + seniority_score * 0.10
            )

            if overall < min_score:
                continue

            competition = job.competition_score
            if competition is None:
                competition = compute_competition_score(job.applicant_count, job.posted_at)
            if search.competition_max is not None and competition > search.competition_max:
                continue

            insight = self._build_insight(job, matched_skills, exp_match)

            results.append({
                "id": str(job.id),
                "title": job.title,
                "company": {"id": str(job.company_id), "name": self._company_name(job)},
                "location": job.location,
                "remote_type": self._enum_value(job.remote_type),
                "experience_min": job.experience_min,
                "experience_max": job.experience_max,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "currency": job.currency,
                "source": self._enum_value(job.source),
                "direct_apply_url": job.direct_apply_url,
                "company_apply_url": job.company_apply_url,
                "job_url": job.job_url,
                "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                "applicant_count": job.applicant_count,
                "competition_score": competition,
                "skills_required": job.skills_required or [],
                "seniority_level": self._enum_value(job.seniority_level),
                "description": job.description,
                "requirements": job.requirements,
                "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
                "score": {
                    "skill_match": skill_score,
                    "experience_match": exp_match.score,
                    "location_match": location_score,
                    "technology_match": technology_score,
                    "seniority_match": seniority_score,
                    "overall_score": round(overall, 1),
                    "experience_status": exp_match.status,
                    "match_reasons": [exp_match.reason]
                    + ([f"{len(matched_skills)} skill match(es): {', '.join(matched_skills[:5])}"] if matched_skills else []),
                    "insight": insight,
                },
            })

        results.sort(key=lambda x: x["score"]["overall_score"], reverse=True)
        return results

    @staticmethod
    def _enum_value(value):
        if value is None:
            return None
        return value.value if hasattr(value, "value") else value

    def _build_insight(self, job, matched_skills: list[str], exp_match: ExperienceMatch) -> str:
        parts: list[str] = []
        if matched_skills:
            parts.append(f"{', '.join(matched_skills[:4])} are direct matches")
        parts.append(exp_match.reason)
        if job.direct_apply_url or job.company_apply_url:
            parts.append("Direct company application available")
        if self._enum_value(job.source) == "company_site":
            parts.append("Listed directly on the company career page")
        return ". ".join(parts) + "."

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def parse_natural_language(self, query: str):
        from app.schemas.search import SearchRequest

        if not settings.OPENAI_API_KEY:
            return SearchRequest(target_role=query, experience_years=2)

        prompt = f"""Parse this job search query into structured parameters.
Query: "{query}"

Return JSON with these fields:
- target_role (string)
- experience_years (number, default 2)
- skills (array of strings)
- locations (array of strings)
- remote_type (array: "remote"/"hybrid"/"onsite")
- posted_within_hours (number: 24/72/168/336, default 24)
- min_score (number 70-100, default 70)"""

        response = await self.client.chat.completions.create(
            model=settings.AI_MODEL_PRIMARY,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return SearchRequest(
            target_role=data.get("target_role", query),
            experience_years=float(data.get("experience_years", 2)),
            skills=data.get("skills", []),
            locations=data.get("locations", []),
            remote_type=data.get("remote_type", []),
            posted_within_hours=int(data.get("posted_within_hours", 24)),
            min_score=int(data.get("min_score", 70)),
        )
