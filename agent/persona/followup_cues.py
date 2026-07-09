from __future__ import annotations

from agent.i18n import t

DOCUMENT_FOLLOWUP_CUES = tuple(t("followup_cues.document"))
URL_FOLLOWUP_CUES = tuple(t("followup_cues.url"))
GITHUB_SEARCH_FOLLOWUP_CUES = tuple(t("followup_cues.github_search"))
GITHUB_REPO_DRILLDOWN_CUES = tuple(t("followup_cues.github_drilldown"))
GITHUB_REPO_TECH_CUES = tuple(t("followup_cues.github_tech"))
GITHUB_REPO_RELEASE_CUES = tuple(t("followup_cues.github_release"))
GITHUB_REPO_PR_CUES = tuple(t("followup_cues.github_pr"))
GITHUB_REPO_ISSUE_CUES = tuple(t("followup_cues.github_issue"))

GITHUB_REPO_TECH_FILE_PROBES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "uv.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "README.md",
)
