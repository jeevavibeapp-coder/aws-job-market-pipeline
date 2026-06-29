"""
tests/test_pipeline_local.py
Run the full pipeline locally (no AWS needed – uses mock data & local filesystem).

    python tests/test_pipeline_local.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import patch

# Patch boto3 before importing handlers


class TestIngestor(unittest.TestCase):
    def test_mock_jobs_returned_without_token(self):
        from lambdas.ingestor.handler import fetch_jobs_from_apify

        with patch.dict(os.environ, {"APIFY_API_TOKEN": ""}):
            jobs = fetch_jobs_from_apify("Data Engineer", "India")
        self.assertIsInstance(jobs, list)
        self.assertGreater(len(jobs), 0)
        self.assertIn("title", jobs[0])

    def test_record_has_required_fields(self):
        from lambdas.ingestor.handler import _mock_jobs

        jobs = _mock_jobs("Data Engineer", "Chennai")
        for j in jobs:
            self.assertIn("id", j)
            self.assertIn("title", j)
            self.assertIn("company", j)


class TestTransformer(unittest.TestCase):
    def test_normalise_basic(self):
        from lambdas.transformer.handler import _normalise

        raw = {
            "id": "job-001",
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Chennai, India",
            "description": "Python, Spark, AWS required.",
            "salary": "$80,000 – $100,000",
            "posted_at": "2025-01-15T00:00:00",
            "source": "linkedin",
            "url": "https://example.com/1",
        }
        meta = {"ingested_at": "2025-01-15T06:00:00", "query": "Data Engineer", "location": "India"}
        result = _normalise(raw, meta)
        self.assertEqual(result["job_id"], "job-001")
        self.assertEqual(result["salary_min"], 80000.0)
        self.assertEqual(result["salary_max"], 100000.0)
        self.assertEqual(result["salary_avg"], 90000.0)

    def test_parse_salary_edge_cases(self):
        from lambdas.transformer.handler import _parse_salary

        self.assertEqual(_parse_salary("")["salary_min"], None)
        self.assertEqual(_parse_salary("$50k")["salary_min"], 50000.0)
        self.assertEqual(_parse_salary("Competitive")["salary_avg"], None)

    def test_fingerprint_deduplication(self):
        from lambdas.transformer.handler import _record_fingerprint

        r1 = {"title": "Data Engineer", "company": "Acme", "location": "Chennai", "job_id": "1"}
        r2 = {"title": "DATA ENGINEER", "company": "acme", "location": "Chennai", "job_id": "1"}
        self.assertEqual(_record_fingerprint(r1), _record_fingerprint(r2))


class TestFeatureExtractor(unittest.TestCase):
    def test_skill_extraction(self):
        from lambdas.feature_extractor.handler import extract_skills

        text = "We need Python, PySpark, AWS Lambda, and Apache Airflow experience."
        skills = extract_skills(text)
        self.assertIn("python", skills)
        self.assertIn("spark", skills)
        self.assertIn("aws", skills)
        self.assertIn("airflow", skills)

    def test_experience_level(self):
        from lambdas.feature_extractor.handler import extract_experience_level

        self.assertEqual(extract_experience_level("Junior Data Engineer role"), "entry")
        self.assertEqual(extract_experience_level("Senior Data Engineer 5+ years"), "senior")
        self.assertEqual(extract_experience_level("Data Engineer – no level mentioned"), "unknown")

    def test_work_mode(self):
        from lambdas.feature_extractor.handler import extract_work_mode

        self.assertEqual(extract_work_mode("Fully remote position"), "remote")
        self.assertEqual(extract_work_mode("Hybrid – 3 days onsite"), "hybrid")
        self.assertEqual(extract_work_mode("In-office, Bangalore"), "onsite")

    def test_enrich_adds_fields(self):
        from lambdas.feature_extractor.handler import enrich

        record = {
            "job_id": "x1",
            "title": "Junior Data Engineer",
            "description": "Python, SQL, AWS Lambda, remote work.",
            "location": "Remote",
        }
        enriched = enrich(record)
        self.assertIn("skills", enriched)
        self.assertIn("experience_level", enriched)
        self.assertIn("work_mode", enriched)
        self.assertEqual(enriched["experience_level"], "entry")
        self.assertEqual(enriched["work_mode"], "remote")


if __name__ == "__main__":
    unittest.main(verbosity=2)
