import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from src.mcp_client import MCPClient


@pytest.fixture
def client():
    return MCPClient()


def test_search_jobs_returns_list(client):
    jobs = client.search_jobs("Python Developer")
    assert isinstance(jobs, list)
    assert len(jobs) > 0


def test_search_jobs_respects_limit(client):
    jobs = client.search_jobs("Engineer", limit=2)
    assert len(jobs) <= 2


def test_search_jobs_fields_present(client):
    required = {"source", "job_id_on_source", "title", "company", "job_url", "description"}
    for job in client.search_jobs("Developer"):
        assert required.issubset(job.keys()), f"Missing fields in: {job}"


def test_search_jobs_with_location(client):
    jobs = client.search_jobs("Data Scientist", location="Bangalore")
    assert all("Bangalore" in j.get("location", "") or j.get("location") for j in jobs)


def test_get_job_details_found(client):
    jobs    = client.search_jobs("Python")
    first   = jobs[0]
    details = client.get_job_details(first["job_id_on_source"], first["source"])
    assert details is not None
    assert details["title"] == first["title"]


def test_get_job_details_not_found(client):
    result = client.get_job_details("nonexistent_id_xyz", "Unknown")
    assert result is None
