"""Report upstream daggerverse commits that are likely relevant to this Pixi port."""

import argparse
import fnmatch
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"


class GitHubError(RuntimeError):
    """Raised when a GitHub API request fails."""


@dataclass(frozen=True)
class PathRule:
    pattern: str
    reason: str


@dataclass(frozen=True)
class UpstreamConfig:
    repository: str
    branch: str
    base_commit: str
    base_note: str
    issue_title: str
    issue_labels: list[str]
    issue_label_color: str
    path_rules: list[PathRule]
    message_keywords: list[str]
    max_pages: int


@dataclass(frozen=True)
class RelevantCommit:
    sha: str
    message: str
    date: str
    url: str
    files: list[str]
    reasons: list[str]

    @property
    def short_sha(self) -> str:
        return self.sha[:7]


def _github_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    params: dict[str, str | int] | None = None,
) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{GITHUB_API}{path}{query}"
    body = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            contents = response.read().decode("utf-8")
            if not contents:
                return None
            return json.loads(contents)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise GitHubError(f"{method} {url} failed with HTTP {error.code}: {details}") from error


def _load_config(path: Path, base_commit_override: str | None) -> UpstreamConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    upstream = data["upstream"]
    issue = data["tracking_issue"]
    relevance = data["relevance"]
    base_commit = base_commit_override or upstream["base_commit"]
    path_rules = [PathRule(pattern=rule["pattern"], reason=rule["reason"]) for rule in relevance["path_rules"]]

    return UpstreamConfig(
        repository=upstream["repository"],
        branch=upstream["branch"],
        base_commit=base_commit,
        base_note=upstream.get("base_note", ""),
        issue_title=issue["title"],
        issue_labels=list(issue.get("labels", [])),
        issue_label_color=issue.get("label_color", "5319e7"),
        path_rules=path_rules,
        message_keywords=list(relevance.get("message_keywords", [])),
        max_pages=int(data.get("max_pages", 3)),
    )


def _list_commits_since_base(config: UpstreamConfig, token: str | None) -> tuple[list[dict[str, Any]], bool]:
    commits: list[dict[str, Any]] = []
    for page in range(1, config.max_pages + 1):
        page_commits = _github_request(
            "GET",
            f"/repos/{config.repository}/commits",
            token=token,
            params={"sha": config.branch, "per_page": 100, "page": page},
        )
        if not page_commits:
            return commits, False

        for commit in page_commits:
            if commit["sha"] == config.base_commit:
                return commits, True
            commits.append(commit)

    return commits, False


def _relevance_reasons(config: UpstreamConfig, message: str, files: list[str]) -> list[str]:
    reasons: list[str] = []
    lowered_message = message.lower()
    for keyword in config.message_keywords:
        if keyword.lower() in lowered_message:
            reasons.append(f"message mentions `{keyword}`")

    for filename in files:
        for rule in config.path_rules:
            if fnmatch.fnmatchcase(filename, rule.pattern):
                reasons.append(f"`{filename}`: {rule.reason}")

    return sorted(set(reasons))


def _get_relevant_commits(config: UpstreamConfig, token: str | None) -> tuple[list[RelevantCommit], bool]:
    commits, found_base = _list_commits_since_base(config, token)
    relevant: list[RelevantCommit] = []

    for commit in commits:
        detail = _github_request("GET", f"/repos/{config.repository}/commits/{commit['sha']}", token=token)
        message = detail["commit"]["message"].splitlines()[0]
        files = [file["filename"] for file in detail.get("files", [])]
        reasons = _relevance_reasons(config, message, files)
        if not reasons:
            continue
        relevant.append(
            RelevantCommit(
                sha=detail["sha"],
                message=message,
                date=detail["commit"]["committer"]["date"],
                url=detail["html_url"],
                files=files,
                reasons=reasons,
            )
        )

    return relevant, found_base


def _render_report(config: UpstreamConfig, commits: list[RelevantCommit], found_base: bool) -> str:
    lines = [
        "# Upstream Daggerverse Updates",
        "",
        f"- Upstream: `{config.repository}` / `{config.branch}`",
        f"- Baseline: `{config.base_commit}`",
    ]
    if config.base_note:
        lines.append(f"- Baseline note: {config.base_note}")
    if not found_base:
        lines.append(f"- Warning: baseline commit was not found within {config.max_pages} page(s).")
    lines.append("")

    if not commits:
        lines.extend(
            [
                "No relevant upstream commits found after the configured baseline.",
                "",
                "After porting future upstream changes, update `.github/upstream-watch.json` `base_commit`",
                "to the latest reviewed upstream SHA.",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"Found {len(commits)} relevant upstream commit(s) after the configured baseline.",
            "",
            "Review checklist:",
            "",
            "- Map `uv/**` behavior changes onto Pixi semantics before porting.",
            "- Check workflow and docs changes for equivalent Pixi/Daggerverse behavior.",
            "- After porting or intentionally skipping, update `.github/upstream-watch.json` `base_commit`.",
            "",
            "## Commits",
            "",
        ]
    )

    for commit in commits:
        lines.extend(
            [
                f"### [{commit.short_sha}]({commit.url}) {commit.message}",
                "",
                f"- Date: `{commit.date}`",
                "- Reasons:",
            ]
        )
        for reason in commit.reasons:
            lines.append(f"  - {reason}")
        lines.append("- Files:")
        for filename in commit.files[:20]:
            lines.append(f"  - `{filename}`")
        if len(commit.files) > 20:
            lines.append(f"  - ... {len(commit.files) - 20} more")
        lines.append("")

    return "\n".join(lines)


def _write_github_outputs(outputs: dict[str, str | int | bool]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


def _ensure_labels(repo: str, labels: list[str], color: str, token: str) -> None:
    for label in labels:
        payload = {"name": label, "color": color, "description": "Upstream sync tracking"}
        try:
            _github_request("POST", f"/repos/{repo}/labels", token=token, payload=payload)
        except GitHubError as error:
            if "already_exists" not in str(error):
                print(f"warning: could not ensure label `{label}`: {error}", file=sys.stderr)


def _find_tracking_issue(repo: str, title: str, token: str) -> dict[str, Any] | None:
    issues = _github_request("GET", f"/repos/{repo}/issues", token=token, params={"state": "open", "per_page": 100})
    for issue in issues:
        if issue.get("pull_request"):
            continue
        if issue["title"] == title:
            return issue
    return None


def _create_or_update_issue(config: UpstreamConfig, body: str, token: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise GitHubError("GITHUB_REPOSITORY is required to update a tracking issue")

    _ensure_labels(repo, config.issue_labels, config.issue_label_color, token)
    existing = _find_tracking_issue(repo, config.issue_title, token)
    payload: dict[str, Any] = {"title": config.issue_title, "body": body}
    if config.issue_labels:
        payload["labels"] = config.issue_labels

    if existing is not None:
        updated = _github_request("PATCH", f"/repos/{repo}/issues/{existing['number']}", token=token, payload=payload)
        return updated["html_url"]

    created = _github_request("POST", f"/repos/{repo}/issues", token=token, payload=payload)
    return created["html_url"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(".github/upstream-watch.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base-commit", help="Override the configured baseline commit, mainly for local checks.")
    parser.add_argument("--update-issue", action="store_true", help="Create or update the tracking GitHub issue.")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    config = _load_config(args.config, args.base_commit)
    commits, found_base = _get_relevant_commits(config, token)
    report = _render_report(config, commits, found_base)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")

    issue_url = ""
    if args.update_issue and commits:
        if not token:
            raise GitHubError(f"{args.token_env} is required when --update-issue is set")
        issue_url = _create_or_update_issue(config, report, token)
        print(f"Updated tracking issue: {issue_url}")

    _write_github_outputs(
        {
            "has_updates": bool(commits),
            "commit_count": len(commits),
            "issue_url": issue_url,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
