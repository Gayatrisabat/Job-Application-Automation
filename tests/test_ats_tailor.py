import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from src.ats_tailor import ATSTailor


@pytest.fixture
def tailor():
    return ATSTailor()   # will use fallback mode if no API key


def test_extract_keywords_fallback(tailor):
    text     = "Python Django Flask PostgreSQL REST API cloud AWS"
    keywords = tailor._extract_keywords(text)
    assert isinstance(keywords, list)
    assert len(keywords) > 0


def test_analyze_job_description(tailor):
    jd  = "We need a Python developer with Django, REST APIs, and PostgreSQL experience."
    out = tailor.analyze_job_description(jd)
    assert "keywords" in out
    assert "raw_description" in out
    assert isinstance(out["keywords"], list)


def test_tailor_resume_returns_tuple(tailor):
    jd       = "Python Flask PostgreSQL AWS REST"
    analysis = tailor.analyze_job_description(jd)
    resume   = "John Doe\nSoftware Developer\nSkills: Python, SQL, Git"
    result   = tailor.tailor_resume(resume, analysis)
    assert isinstance(result, tuple)
    assert len(result) == 2
    content, score = result
    assert isinstance(content, str)
    assert 0 <= score <= 100


def test_tailor_resume_no_api_key(tailor):
    """Without API key, tailor returns original content and score=0."""
    if tailor.client is not None:
        pytest.skip("API key is set; fallback not applicable")
    jd       = "Python Developer"
    analysis = tailor.analyze_job_description(jd)
    resume   = "My resume content"
    content, score = tailor.tailor_resume(resume, analysis)
    assert content == resume
    assert score == 0
