import base64

import httpx
from fastapi import HTTPException, status


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _jira_auth_header(email: str, api_token: str) -> str:
    raw = f"{email}:{api_token}".encode()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"Basic {encoded}"


async def test_connection(base_url: str, email: str, api_token: str) -> None:
    normalized_base = _normalize_base_url(base_url)
    headers = {
        "Authorization": _jira_auth_header(email, api_token),
        "Accept": "application/json",
    }
    url = f"{normalized_base}/rest/api/3/myself"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify Jira integration.",
        ) from exc


async def create_issue(
    *,
    base_url: str,
    email: str,
    api_token: str,
    project_key: str,
    summary: str,
    description: str,
) -> dict[str, str]:
    normalized_base = _normalize_base_url(base_url)
    headers = {
        "Authorization": _jira_auth_header(email, api_token),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    url = f"{normalized_base}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": "Task"},
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Jira issue.",
        ) from exc

    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("key"), str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid Jira issue response.",
        )

    issue_key = body["key"]
    issue_url = f"{normalized_base}/browse/{issue_key}"
    return {"issueKey": issue_key, "url": issue_url}
