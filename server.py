import os
import sys
import functools
import httpx
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from edstem_client import EdStemClient
from dotenv import load_dotenv

# Ensure imports resolve regardless of CWD when launched by Claude Code
sys.path.insert(0, str(Path(__file__).parent))

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

mcp = FastMCP("EdStem")


def _run_sso():
    from get_token import main as browser_login
    browser_login()
    load_dotenv(ENV_PATH, override=True)


def _make_client() -> EdStemClient:
    token = os.environ.get("EDSTEM_TOKEN")
    if not token:
        print("EDSTEM_TOKEN not set — launching SSO login.")
        _run_sso()
        token = os.environ.get("EDSTEM_TOKEN")
    return EdStemClient(token=token)


client = _make_client()


def with_auth_retry(fn):
    """Re-authenticate via SSO and retry once if a 401 is returned."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        global client
        try:
            return fn(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("Token expired — re-authenticating via SSO.")
                _run_sso()
                client = _make_client()
                return fn(*args, **kwargs)
            raise
    return wrapper


@mcp.tool()
@with_auth_retry
def list_courses() -> list[dict]:
    """List all Ed Stem courses you're enrolled in."""
    courses = client.get_courses()
    return [
        {
            "id": c["course"]["id"],
            "name": c["course"]["name"],
            "code": c["course"].get("code", ""),
        }
        for c in courses
    ]


@mcp.tool()
@with_auth_retry
def get_recent_posts(course_id: int, limit: int = 20) -> list[dict]:
    """Get recent posts/threads from a course message board."""
    threads = client.get_threads(course_id, limit=limit)
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "author": (t.get("user") or {}).get("name", "Anonymous"),
            "created_at": t["created_at"],
            "vote_count": t.get("vote_count", 0),
            "answer_count": t.get("answer_count", 0),
            "is_answered": t.get("is_answered", False),
            "type": t.get("type", "post"),
        }
        for t in threads
    ]


@mcp.tool()
@with_auth_retry
def get_thread_detail(thread_id: int) -> dict:
    """Get the full content of a specific thread including all replies."""
    thread = client.get_thread(thread_id)
    return {
        "id": thread["id"],
        "title": thread["title"],
        "content": thread.get("document", ""),
        "author": (thread.get("user") or {}).get("name", "Anonymous"),
        "answers": [
            {
                "author": (a.get("user") or {}).get("name", "Anonymous"),
                "content": a.get("document", ""),
                "is_correct": a.get("is_correct", False),
            }
            for a in thread.get("answers", [])
        ],
        "comments": [
            {
                "author": (c.get("user") or {}).get("name", "Anonymous"),
                "content": c.get("document", ""),
            }
            for c in thread.get("comments", [])
        ],
    }


@mcp.tool()
@with_auth_retry
def get_lessons(course_id: int) -> list[dict]:
    """Get all lessons for a course, sorted by index."""
    lessons = client.get_lessons(course_id)
    return sorted(
        [
            {
                "id": l["id"],
                "title": l["title"],
                "index": l["index"],
                "kind": l.get("kind", ""),
                "status": l.get("status", ""),
                "state": l.get("state", ""),
                "slide_count": l.get("slide_count", 0),
                "due_at": l.get("due_at"),
                "available_at": l.get("available_at"),
                "is_hidden": l.get("is_hidden", False),
            }
            for l in lessons
        ],
        key=lambda l: l["index"],
    )


@mcp.tool()
@with_auth_retry
def search_posts(course_id: int, query: str, limit: int = 15) -> list[dict]:
    """Search for posts in a course by keyword."""
    threads = client.search_threads(course_id, query, limit=limit)
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "author": (t.get("user") or {}).get("name", "Anonymous"),
            "is_answered": t.get("is_answered", False),
        }
        for t in threads
    ]


if __name__ == "__main__":
    mcp.run()
