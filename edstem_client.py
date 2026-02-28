import httpx
import os

_COUNTRY = os.environ.get("EDSTEM_COUNTRY", "us").lower()
BASE_URL = f"https://{_COUNTRY}.edstem.org/api"


class EdStemClient:
    @staticmethod
    def login(email: str, password: str) -> str:
        """Authenticate with EdStem and return the API token."""
        r = httpx.post(
            f"{BASE_URL}/login",
            json={"login": {"email": email, "password": password}},
        )
        r.raise_for_status()
        return r.json()["token"]

    def __init__(self, token: str):
        self.token = token
        self.headers = {"X-Token": token}

    def get_courses(self):
        r = httpx.get(f"{BASE_URL}/user", headers=self.headers)
        r.raise_for_status()
        return (r.json() or {}).get("courses", [])

    def get_threads(self, course_id: int, limit: int = 30, offset: int = 0):
        params = {"limit": limit, "offset": offset, "sort": "new"}
        r = httpx.get(
            f"{BASE_URL}/courses/{course_id}/threads",
            headers=self.headers,
            params=params,
        )
        r.raise_for_status()
        return (r.json() or {}).get("threads", [])

    def get_thread(self, thread_id: int):
        r = httpx.get(f"{BASE_URL}/threads/{thread_id}", headers=self.headers)
        r.raise_for_status()
        return (r.json() or {}).get("thread", {})

    def get_lessons(self, course_id: int):
        r = httpx.get(f"{BASE_URL}/courses/{course_id}/lessons", headers=self.headers)
        r.raise_for_status()
        return (r.json() or {}).get("lessons", [])

    def get_lesson_slides(self, lesson_id: int):
        r = httpx.get(f"{BASE_URL}/lessons/{lesson_id}", headers=self.headers)
        r.raise_for_status()
        return (r.json() or {}).get("lesson", {}).get("slides", [])

    def search_threads(self, course_id: int, query: str, limit: int = 20):
        params = {"limit": limit, "sort": "new", "filter": "all"}
        r = httpx.get(
            f"{BASE_URL}/courses/{course_id}/threads",
            headers=self.headers,
            params={**params, "search": query},
        )
        r.raise_for_status()
        return (r.json() or {}).get("threads", [])
