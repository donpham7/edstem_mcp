# EdStem MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes EdStem course discussion boards as tools for AI assistants. Supports Georgia Tech SSO + Duo MFA authentication with fully automated browser login.

## Features

- List all enrolled courses
- Fetch recent posts from a course board
- Retrieve full thread content with answers and comments
- Search posts by keyword
- Automatic SSO login via Selenium (GT SSO + Duo MFA)
- Token caching in `.env` — re-authenticates automatically on expiry

---

## Requirements

- Python 3.10+
- Google Chrome installed
- ChromeDriver (matching your Chrome version) on your `PATH`

Install dependencies:

```bash
pip install mcp selenium python-dotenv httpx
```

---

## Configuration

Create a `.env` file in the project root. All fields:

```env
# EdStem API token — auto-populated after first login, leave blank initially
EDSTEM_TOKEN=

# Your EdStem account email
EDSTEM_EMAIL=you@gatech.edu

# EdStem region: us | au | uk
EDSTEM_COUNTRY=us

# Georgia Tech SSO credentials (used for automated browser login)
GT_USERNAME=gburdell3
GT_PASSWORD=yourpassword
```

> **Never commit `.env` to version control.** It is listed in `.gitignore` by default.

---

## Getting a Token

Run the login script once to authenticate and save the token:

```bash
python get_token.py
```

This will:
1. Open Chrome to the EdStem login page
2. Auto-fill your email and select the region
3. Redirect to `sso.gatech.edu` and auto-fill your GT username/password
4. Wait for you to approve **Duo MFA on your phone**
5. Auto-click the "Trust this browser" prompt
6. Capture the `X-Token` from the EdStem API and save it to `.env`

After this, the token is cached and the server starts instantly on future runs. The server will re-run this flow automatically if the token expires mid-session.

---

## Usage

### With Claude Code

**Register the server (one time):**

```bash
claude mcp add edstem -- /path/to/python /path/to/edstem_scraper/server.py
```

Example with Miniconda:

```bash
claude mcp add edstem -- /home/youruser/miniconda3/bin/python /home/youruser/edstem_scraper/server.py
```

**Start Claude Code:**

```bash
claude
```

The EdStem tools are now available. Verify with `/mcp` inside the session.

**Example prompts:**
- `"List my EdStem courses"`
- `"Show me the 20 most recent posts in course 91212"`
- `"Search for posts about 'group project' in course 91212"`
- `"Get the full content of thread 7716453"`

**To re-register after changes:**

```bash
claude mcp remove edstem && claude mcp add edstem -- /path/to/python /path/to/server.py
```

---

### With Any Other MCP Client

The server uses stdio transport (the MCP default). Point your client at:

```
command: python
args: ["/absolute/path/to/server.py"]
```

For example in a `claude_desktop_config.json` (Claude Desktop):

```json
{
  "mcpServers": {
    "edstem": {
      "command": "/path/to/python",
      "args": ["/path/to/edstem_scraper/server.py"]
    }
  }
}
```

---

## Available Tools

| Tool | Description | Parameters |
|---|---|---|
| `list_courses` | List all enrolled courses | — |
| `get_lessons` | List all lessons in a course sorted by index | `course_id` |
| `get_recent_posts` | Fetch recent threads from a course board | `course_id`, `limit` (default 20) |
| `get_thread_detail` | Get full thread with answers and comments | `thread_id` |
| `search_posts` | Search threads by keyword | `course_id`, `query`, `limit` (default 15) |

To find a `course_id`, call `list_courses` first.

---

## SSO Compatibility

The automated login flow in `get_token.py` is built and tested for **Georgia Tech SSO** (`sso.gatech.edu`) using the GT CAS login form (username/password fields + Duo MFA).

**Other institutions:** The automated browser login will not work out of the box for non-GT SSO providers, as login form selectors and MFA flows vary by institution. If you want to adapt this for another institution, fork the repo and update the following in `get_token.py`:

- `SSO_HOST` — your institution's SSO hostname
- `try_fill_gt_sso()` — update form field selectors to match your SSO login page
- `try_click_trust_browser()` — verify the trust-browser button ID matches
- Remove or replace the Duo-specific handling if your institution uses a different MFA provider

Everything else (EdStem API client, MCP tools, token caching) is institution-agnostic and requires no changes.

---

## File Overview

| File | Purpose |
|---|---|
| `server.py` | MCP server — defines tools and handles auth retry |
| `edstem_client.py` | HTTP client for the EdStem API |
| `get_token.py` | Selenium browser automation for SSO login |
| `.env` | Credentials and config (not committed) |
| `.gitignore` | Excludes `.env` and `__pycache__` |
