import logging
from datetime import datetime
from typing import List, Dict, Optional


class MCPClient:
    """
    Model Context Protocol client for querying job portals.
    In production, replace the dummy data with real MCP server API calls.
    """

    def __init__(self, mcp_server_url: str = "https://api.example.com/mcp"):
        self.mcp_server_url = mcp_server_url
        self._last_results: List[Dict] = []   # cache populated by search_jobs
        logging.info(f"MCPClient initialized with server: {self.mcp_server_url}")

    def search_jobs(self, keywords: str, location: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Searches for job postings using the MCP server.
        Returns simulated job data; replace with real API calls in production.
        """
        logging.info(f"Searching for jobs with keywords='{keywords}', location='{location}'")
        loc = location if location else "Remote"

        dummy_jobs = [
            {
                "source": "Indeed",
                "job_id_on_source": "indeed_12345",
                "title": f"Software Engineer – {keywords}",
                "company": "Tech Solutions Inc.",
                "location": loc,
                "description": (
                    "We are looking for a skilled Software Engineer to join our dynamic team. "
                    "Responsibilities include developing and maintaining software applications, "
                    "collaborating with cross-functional teams, and contributing to all phases "
                    "of the development lifecycle. Strong proficiency in Python and experience "
                    "with web frameworks are required."
                ),
                "job_url": "https://www.indeed.com/job/indeed_12345",
                "posted_date": datetime(2026, 5, 20).isoformat(),
            },
            {
                "source": "Glassdoor",
                "job_id_on_source": "glassdoor_67890",
                "title": f"Senior {keywords} Developer",
                "company": "Innovate Corp.",
                "location": location if location else "New York, NY",
                "description": (
                    f"Innovate Corp. is seeking a Senior Developer with expertise in {keywords} "
                    "and cloud technologies. You will lead the design and implementation of complex "
                    "software solutions, mentor junior developers, and drive technical innovation. "
                    "A minimum of 5 years experience is required."
                ),
                "job_url": "https://www.glassdoor.com/job/glassdoor_67890",
                "posted_date": datetime(2026, 5, 18).isoformat(),
            },
            {
                "source": "Naukri",
                "job_id_on_source": "naukri_11223",
                "title": f"{keywords} Specialist",
                "company": "Global Systems Ltd.",
                "location": location if location else "Bangalore, India",
                "description": (
                    f"Join Global Systems Ltd. as a {keywords} Specialist. You will be responsible "
                    "for analyzing requirements, designing solutions, and implementing features. "
                    "Strong analytical skills and a passion for problem-solving are essential. "
                    "Experience with data analysis tools is a plus."
                ),
                "job_url": "https://www.naukri.com/job/naukri_11223",
                "posted_date": datetime(2026, 5, 22).isoformat(),
            },
            {
                "source": "LinkedIn",
                "job_id_on_source": "linkedin_44556",
                "title": f"{keywords} Engineer – Product Team",
                "company": "NextGen AI",
                "location": location if location else "San Francisco, CA",
                "description": (
                    f"NextGen AI is hiring a {keywords} Engineer to work on cutting-edge AI products. "
                    "You will collaborate with product managers and designers to build scalable systems. "
                    "Experience with machine learning frameworks and REST APIs is preferred."
                ),
                "job_url": "https://www.linkedin.com/jobs/view/44556",
                "posted_date": datetime(2026, 5, 21).isoformat(),
            },
            {
                "source": "Monster",
                "job_id_on_source": "monster_99001",
                "title": f"Junior {keywords} Developer",
                "company": "StartUp Hub",
                "location": location if location else "Austin, TX",
                "description": (
                    f"StartUp Hub is looking for a motivated Junior {keywords} Developer to join our "
                    "fast-growing team. Ideal for recent graduates with strong fundamentals in software "
                    "development. Mentorship and growth opportunities provided."
                ),
                "job_url": "https://www.monster.com/job/monster_99001",
                "posted_date": datetime(2026, 5, 23).isoformat(),
            },
        ]

        self._last_results = dummy_jobs[:limit]
        return self._last_results

    def get_job_details(self, job_id_on_source: str, source: str) -> Optional[Dict]:
        """
        Retrieves detailed information for a specific job posting.
        Looks up from the cache populated by the most recent search_jobs call.
        """
        logging.info(f"Getting details for job_id={job_id_on_source}, source={source}")
        for job in self._last_results:
            if job["job_id_on_source"] == job_id_on_source and job["source"] == source:
                return job
        return None


if __name__ == '__main__':
    client = MCPClient()
    jobs = client.search_jobs(keywords="Python Developer", location="Remote")
    for job in jobs:
        print(f"- {job['title']} at {job['company']} ({job['source']})")
