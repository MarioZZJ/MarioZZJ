from __future__ import annotations

import base64
import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
GITHUB_BIO_START = "<!-- github-bio:start -->"
GITHUB_BIO_END = "<!-- github-bio:end -->"
SIGNALS_START = "<!-- profile-signals:start -->"
SIGNALS_END = "<!-- profile-signals:end -->"
WAKATIME_STATS_URL = "https://api.wakatime.com/api/v1/users/current/stats/last_30_days"
HTTP_TIMEOUT_SECONDS = 15
WAKATIME_ATTEMPTS = 4
WAKATIME_RETRY_SECONDS = 10


def _fetch_json(url: str, headers: dict[str, str]) -> tuple[int, dict]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
            status = response.status
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Request failed with HTTP {error.code}: {url}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Request failed: {url}") from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected JSON response: {url}")
    return status, payload


def fetch_github_bio(owner: str, token: str) -> str:
    encoded_owner = urllib.parse.quote(owner, safe="")
    _, payload = _fetch_json(
        f"https://api.github.com/users/{encoded_owner}",
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": f"{owner}-profile-refresh",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    bio = payload.get("bio")
    if not isinstance(bio, str) or not bio.strip():
        raise RuntimeError("GitHub bio is empty")
    return " ".join(bio.split())


def fetch_wakatime_stats(api_key: str) -> dict:
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "User-Agent": "MarioZZJ-profile-refresh",
    }

    for attempt in range(WAKATIME_ATTEMPTS):
        _, payload = _fetch_json(WAKATIME_STATS_URL, headers)
        data = payload.get("data")
        if (
            isinstance(data, dict)
            and data.get("is_up_to_date") is True
            and data.get("percent_calculated") == 100
        ):
            return data
        if attempt + 1 < WAKATIME_ATTEMPTS:
            time.sleep(WAKATIME_RETRY_SECONDS)

    raise RuntimeError("WakaTime stats remained stale after retries")


def format_tokens(count: int) -> str:
    if count < 0:
        raise ValueError("Token count cannot be negative")

    for threshold, suffix in (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ):
        if count >= threshold:
            value = f"{count / threshold:.2f}".rstrip("0").rstrip(".")
            return f"{value}{suffix}"
    return str(count)


def _replace_block(text: str, start: str, end: str, content: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError(f"Expected exactly one marker pair: {start}, {end}")

    prefix, remainder = text.split(start, 1)
    _, suffix = remainder.split(end, 1)
    return f"{prefix}{start}\n{content}\n{end}{suffix}"


def _signals_html(stats: dict) -> str:
    coding_time = stats.get("human_readable_total")
    input_tokens = stats.get("ai_input_tokens")
    output_tokens = stats.get("ai_output_tokens")
    if not isinstance(coding_time, str) or not coding_time.strip():
        raise RuntimeError("WakaTime coding time is missing")
    if type(input_tokens) is not int or type(output_tokens) is not int:
        raise RuntimeError("WakaTime AI token counts are missing")

    total_tokens = format_tokens(input_tokens + output_tokens)
    safe_time = html.escape(" ".join(coding_time.split()))
    return (
        '<p align="center"><sub>Last 30 days · '
        f"{safe_time} coding · {total_tokens} WakaTime-tracked AI tokens"
        "</sub></p>"
    )


def render_profile(readme: str, bio: str, stats: dict) -> str:
    safe_bio = html.escape(bio)
    updated = _replace_block(
        readme,
        GITHUB_BIO_START,
        GITHUB_BIO_END,
        f'<p align="center"><strong>{safe_bio}</strong></p>',
    )
    return _replace_block(updated, SIGNALS_START, SIGNALS_END, _signals_html(stats))


def update_profile(
    readme_path: Path, owner: str, github_token: str, wakatime_token: str
) -> bool:
    bio = fetch_github_bio(owner, github_token)
    stats = fetch_wakatime_stats(wakatime_token)
    current = readme_path.read_text(encoding="utf-8")
    updated = render_profile(current, bio, stats)
    if updated == current:
        return False
    readme_path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def main() -> None:
    update_profile(
        README_PATH,
        _required_env("PROFILE_OWNER"),
        _required_env("GITHUB_TOKEN"),
        _required_env("WAKATIME_TOKEN"),
    )


if __name__ == "__main__":
    main()
