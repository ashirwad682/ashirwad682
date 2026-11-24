#!/usr/bin/env python3
"""Update the README's latest-project section from GitHub's public REST API."""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "ashirwad682")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README_PATH = "README.md"
START = "<!--START_SECTION:latest_projects-->"
END = "<!--END_SECTION:latest_projects-->"


def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ashirwad-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def clean(value):
    value = (value or "").replace("\r", " ").replace("\n", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value.replace("|", r"\|") or "No description provided."


def display_date(value):
    if not value:
        return "Push date unavailable"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def build_section(repositories):
    owned = [
        repo for repo in repositories
        if not repo.get("fork")
        and not repo.get("archived")
        and repo.get("owner", {}).get("login", "").lower() == USERNAME.lower()
    ]
    owned.sort(key=lambda repo: repo.get("pushed_at") or "", reverse=True)
    latest = owned[:2]

    if not latest:
        return "_No public pushed repositories were returned by the GitHub API._"

    cards = []
    for index, repo in enumerate(latest, start=1):
        name = repo["name"]
        url = repo["html_url"]
        description = clean(repo.get("description"))
        language = repo.get("language") or "Not specified"
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        pushed = display_date(repo.get("pushed_at"))
        homepage = (repo.get("homepage") or "").strip()

        block = [
            f"### {index}. [{name}]({url})",
            "",
            description,
            "",
            f"`{language}` &nbsp; · &nbsp; ⭐ {stars} stars &nbsp; · &nbsp; 🍴 {forks} forks",
            "",
            f"**Latest push:** {pushed}",
        ]
        if homepage.startswith(("https://", "http://")):
            block.append(f"**Live demo:** [Open project]({homepage})")
        block.append("")
        cards.append("\n".join(block))

    return "\n---\n\n".join(cards).strip()


def main():
    url = (
        f"https://api.github.com/users/{urllib.parse.quote(USERNAME)}/repos"
        "?type=owner&sort=pushed&direction=desc&per_page=100"
    )
    try:
        repositories = github_get(url)
    except urllib.error.HTTPError as exc:
        print(f"GitHub API returned HTTP {exc.code}.", file=sys.stderr)
        raise
    except Exception as exc:
        print(f"Could not retrieve repositories: {exc}", file=sys.stderr)
        raise

    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()

    replacement = f"{START}\n{build_section(repositories)}\n{END}"
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        flags=re.DOTALL,
    )
    updated, count = pattern.subn(lambda _: replacement, readme, count=1)
    if count != 1:
        raise RuntimeError("README markers are missing or duplicated.")

    with open(README_PATH, "w", encoding="utf-8") as file:
        file.write(updated)

    print("Latest-project section refreshed successfully.")


if __name__ == "__main__":
    main()
