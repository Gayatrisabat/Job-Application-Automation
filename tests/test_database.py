import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, UserProfile, Resume, JobPosting, TailoredResume, Application


@pytest.fixture
def session():
    """In-memory SQLite session for isolated tests."""
    engine  = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_create_user_profile(session):
    p = UserProfile(name="Alice", email="alice@example.com", phone="9999999999")
    session.add(p)
    session.commit()
    result = session.query(UserProfile).filter_by(email="alice@example.com").first()
    assert result is not None
    assert result.name == "Alice"


def test_unique_email_constraint(session):
    p1 = UserProfile(name="Bob",  email="bob@example.com")
    p2 = UserProfile(name="Bob2", email="bob@example.com")
    session.add(p1)
    session.commit()
    session.add(p2)
    with pytest.raises(Exception):
        session.commit()


def test_create_resume(session):
    p = UserProfile(name="Carol", email="carol@example.com")
    session.add(p); session.commit()
    r = Resume(user_profile_id=p.id, title="SWE Resume", file_path="/tmp/resume.pdf")
    session.add(r); session.commit()
    assert session.query(Resume).count() == 1
    assert r.user_profile.name == "Carol"


def test_create_job_posting(session):
    jp = JobPosting(
        source="Indeed", job_id_on_source="abc123",
        title="Python Dev", company="ACME", job_url="https://indeed.com/abc123"
    )
    session.add(jp); session.commit()
    assert session.query(JobPosting).filter_by(job_id_on_source="abc123").first() is not None


def test_application_status_default(session):
    p  = UserProfile(name="Dave", email="dave@example.com")
    jp = JobPosting(source="GD", job_id_on_source="gd001", title="Dev",
                    company="Corp", job_url="https://glassdoor.com/gd001")
    session.add_all([p, jp]); session.commit()
    app = Application(user_profile_id=p.id, job_posting_id=jp.id)
    session.add(app); session.commit()
    assert app.status == "Applied"


def test_cascade_profile_resumes(session):
    p = UserProfile(name="Eve", email="eve@example.com")
    session.add(p); session.commit()
    for i in range(3):
        session.add(Resume(user_profile_id=p.id, title=f"R{i}", file_path=f"/tmp/r{i}.pdf"))
    session.commit()
    assert len(p.resumes) == 3
