import re
from typing import Optional, Dict, Any

import requests

# Matches a GitHub repo root or deeper paths (we normalize later)
GITHUB_REGEX = re.compile(
    r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*",
    re.IGNORECASE
)

def extract_github_url(model_info: Dict[str, Any]) -> Optional[str]:
    """
    Extract a GitHub repository URL from HuggingFace /api/models/{model} metadata.
    Tries multiple strategies including cardData fields, URL fields,
    recursive scanning, and README.md content.

    Returns:
        Clean normalized GitHub repo URL, or None if no repo detected.
    """

    # ---------------------------------------------
    # 1. cardData.repository
    # ---------------------------------------------
    card = model_info.get("cardData", {}) or {}
    repo_field = card.get("repository")
    if isinstance(repo_field, str) and "github.com" in repo_field:
        return _normalize_github_repo_url(repo_field)

    # ---------------------------------------------
    # 2. cardData.github
    # ---------------------------------------------
    gh_field = card.get("github")
    if isinstance(gh_field, str) and "github.com" in gh_field:
        return _normalize_github_repo_url(gh_field)

    # ---------------------------------------------
    # 3. Search all cardData fields for GitHub URLs
    # ---------------------------------------------
    for val in card.values():
        # string
        if isinstance(val, str):
            match = GITHUB_REGEX.search(val)
            if match:
                return _normalize_github_repo_url(match.group())

        # list of strings
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    match = GITHUB_REGEX.search(item)
                    if match:
                        return _normalize_github_repo_url(match.group())

    # ---------------------------------------------
    # 4. Check model_info["url"]
    # ---------------------------------------------
    url = model_info.get("url", "")
    if isinstance(url, str):
        match = GITHUB_REGEX.search(url)
        if match:
            return _normalize_github_repo_url(match.group())

    # ---------------------------------------------
    # 5. Search siblings (occasionally contain GitHub links)
    # ---------------------------------------------
    siblings = model_info.get("siblings", [])
    for sib in siblings:
        if isinstance(sib, dict):
            for v in sib.values():
                if isinstance(v, str):
                    match = GITHUB_REGEX.search(v)
                    if match:
                        return _normalize_github_repo_url(match.group())

    # ---------------------------------------------
    # 6. Deep recursive search over JSON object
    # ---------------------------------------------
    def deep_scan(obj):
        if isinstance(obj, str):
            m = GITHUB_REGEX.search(obj)
            return m.group() if m else None

        if isinstance(obj, list):
            for item in obj:
                res = deep_scan(item)
                if res:
                    return res

        if isinstance(obj, dict):
            for v in obj.values():
                res = deep_scan(v)
                if res:
                    return res

        return None

    found = deep_scan(model_info)
    if found:
        return _normalize_github_repo_url(found)

    # ---------------------------------------------
    # 7. Scan README.md for GitHub links
    # ---------------------------------------------
    model_id = model_info.get("modelId") or model_info.get("id")
    if model_id:
        readme_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
        try:
            resp = requests.get(readme_url, timeout=5)
            if resp.status_code == 200:
                match = GITHUB_REGEX.search(resp.text)
                if match:
                    return _normalize_github_repo_url(match.group())
        except Exception:
            pass

    # If all methods fail:
    return None


# ---------------------------------------------------------
# Helper: Normalize GitHub links to the repo root
# ---------------------------------------------------------
def _normalize_github_repo_url(url: str) -> str:
    """
    Normalize GitHub URLs to the base repository form:
    https://github.com/owner/repo

    Also strips:
      - query params
      - fragments (#)
      - /tree/main, /blob/main, /issues, etc.
    """

    # remove query params & anchors
    url = url.split("?")[0].split("#")[0].rstrip("/")

    # Break into components
    parts = url.split("/")

    # GitHub repo root should be:
    # https: / github.com / owner / repo
    # indices: 0     1        2      3     4
    if len(parts) >= 5: 
        base = "/".join(parts[:5])
        return base.rstrip("/")

    return url
