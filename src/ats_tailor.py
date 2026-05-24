import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from typing import Dict, List, Tuple

load_dotenv()


class ATSTailor:
    """
    AI-powered ATS resume tailoring engine.
    Uses OpenAI GPT to extract keywords and tailor resumes
    to match specific job descriptions for maximum ATS compatibility.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            logging.warning("OPENAI_API_KEY not set. AI tailoring will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _extract_keywords(self, text: str) -> List[str]:
        """Uses LLM to extract key skills and keywords from a given text."""
        if not self.client:
            # Fallback: simple keyword extraction without LLM
            common_words = {"and", "or", "the", "a", "an", "in", "of", "to", "for", "with", "is", "are", "will", "be"}
            words = [w.strip(".,;:()") for w in text.split() if len(w) > 4]
            return list({w for w in words if w.lower() not in common_words})[:15]

        prompt = (
            "Extract the most important skills, technologies, and requirements from the "
            "following text. Return them as a comma-separated list only, no explanation.\n\n"
            f"Text: {text}\nKeywords:"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You extract keywords from job descriptions and resumes."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
            )
            keywords_str = response.choices[0].message.content.strip()
            return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
        except Exception as e:
            logging.error(f"Error extracting keywords: {e}")
            return []

    def analyze_job_description(self, job_description: str) -> Dict:
        """Analyzes a job description to identify key requirements and skills."""
        keywords = self._extract_keywords(job_description)
        logging.info(f"Extracted {len(keywords)} keywords from job description.")
        return {"keywords": keywords, "raw_description": job_description}

    def tailor_resume(self, base_resume_content: str, job_description_analysis: Dict) -> Tuple[str, int]:
        """
        Generates an ATS-friendly tailored resume.
        Returns (tailored_resume_content, match_score).
        Falls back to original resume if AI is unavailable.
        """
        job_keywords = ", ".join(job_description_analysis["keywords"])

        if not self.client:
            logging.warning("OpenAI client not available. Returning original resume with score 0.")
            return base_resume_content, 0

        prompt = (
            "You are an expert resume writer. Tailor the given resume to the job description "
            "keywords to maximize ATS compatibility. Incorporate relevant keywords naturally, "
            "rephrase existing content to align with requirements, but do NOT fabricate experience. "
            "Preserve the original structure and achievements.\n\n"
            f"Job Description Keywords: {job_keywords}\n\n"
            f"Original Resume:\n\n```\n{base_resume_content}\n```\n\n"
            "Tailored Resume:"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert resume writer optimizing for ATS."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
            )
            tailored_content = response.choices[0].message.content.strip()

            # Calculate match score
            job_kw_set = set(kw.lower() for kw in job_description_analysis["keywords"])
            tailored_kw_set = set(kw.lower() for kw in self._extract_keywords(tailored_content))
            matched = job_kw_set.intersection(tailored_kw_set)
            score = int((len(matched) / len(job_kw_set)) * 100) if job_kw_set else 0

            logging.info(f"Resume tailored. Match score: {score}%")
            return tailored_content, score

        except Exception as e:
            logging.error(f"Error tailoring resume: {e}")
            return base_resume_content, 0


if __name__ == '__main__':
    tailor = ATSTailor()
    sample_jd = """
    We are seeking a Python Developer with experience in Django, Flask, PostgreSQL,
    RESTful APIs, AWS, and agile methodologies. Strong problem-solving skills required.
    """
    sample_resume = """
    John Doe | Software Developer
    Skills: Python, Java, SQL, Git
    Experience: 3 years building internal tools with Python.
    Education: B.S. Computer Science
    """
    analysis = tailor.analyze_job_description(sample_jd)
    print("Keywords:", analysis["keywords"])
    tailored, score = tailor.tailor_resume(sample_resume, analysis)
    print(f"Score: {score}%\nTailored (first 200 chars):\n{tailored[:200]}")
