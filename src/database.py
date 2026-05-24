import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Define the base for our declarative models
Base = declarative_base()

# Define the database file path
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'applications.db')

# Ensure the database directory exists
os.makedirs(DATABASE_DIR, exist_ok=True)


class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String)
    linkedin_profile = Column(String)
    github_profile = Column(String)

    resumes = relationship('Resume', back_populates='user_profile')

    def __repr__(self):
        return f"<UserProfile(name='{self.name}', email='{self.email}')>"


class Resume(Base):
    __tablename__ = 'resumes'

    id = Column(Integer, primary_key=True)
    user_profile_id = Column(Integer, ForeignKey('user_profiles.id'))
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.now)

    user_profile = relationship('UserProfile', back_populates='resumes')
    tailored_resumes = relationship('TailoredResume', back_populates='base_resume')

    def __repr__(self):
        return f"<Resume(title='{self.title}', file_path='{self.file_path}')>"


class TailoredResume(Base):
    __tablename__ = 'tailored_resumes'

    id = Column(Integer, primary_key=True)
    base_resume_id = Column(Integer, ForeignKey('resumes.id'))
    job_posting_id = Column(Integer, ForeignKey('job_postings.id'))
    tailored_file_path = Column(String, nullable=False)
    match_score = Column(Integer)
    generated_at = Column(DateTime, default=datetime.now)

    base_resume = relationship('Resume', back_populates='tailored_resumes')
    job_posting = relationship('JobPosting', back_populates='tailored_resumes')
    application = relationship('Application', back_populates='tailored_resume', uselist=False)

    def __repr__(self):
        return f"<TailoredResume(id={self.id}, match_score={self.match_score})>"


class JobPosting(Base):
    __tablename__ = 'job_postings'

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    job_id_on_source = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    description = Column(Text)
    job_url = Column(String, nullable=False)
    posted_date = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.now)

    tailored_resumes = relationship('TailoredResume', back_populates='job_posting')
    applications = relationship('Application', back_populates='job_posting')

    def __repr__(self):
        return f"<JobPosting(title='{self.title}', company='{self.company}')>"


class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    user_profile_id = Column(Integer, ForeignKey('user_profiles.id'))
    job_posting_id = Column(Integer, ForeignKey('job_postings.id'))
    tailored_resume_id = Column(Integer, ForeignKey('tailored_resumes.id'))
    applied_at = Column(DateTime, default=datetime.now)
    status = Column(String, default='Applied')
    notes = Column(Text)

    user_profile = relationship('UserProfile')
    job_posting = relationship('JobPosting', back_populates='applications')
    tailored_resume = relationship('TailoredResume', back_populates='application')

    def __repr__(self):
        return f"<Application(job='{self.job_posting.title}', status='{self.status}')>"


# Database engine and session setup
engine = create_engine(f'sqlite:///{DATABASE_PATH}')
Session = sessionmaker(bind=engine)


def init_db():
    """Initializes the database by creating all defined tables."""
    Base.metadata.create_all(engine)
    logging.info(f"Database initialized at {DATABASE_PATH}")
    print(f"Database initialized at {DATABASE_PATH}")


if __name__ == '__main__':
    init_db()
