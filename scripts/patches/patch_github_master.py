#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[2] / "workflows/core/workflow_sub_github_master.json"


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"pattern not found: {old[:80]!r}")
    return text.replace(old, new, 1)


def patch_github_input(js_code: str) -> str:
    js_code = replace_once(
        js_code,
        "const useAuth = tool === 'github.search_code';",
        "let useAuth = ['github.search_code', 'github.search_repos', 'github.list_user_repos'].includes(tool);",
    )

    js_code = replace_once(
        js_code,
        "const queryInput = clean(args.query || source.query || '');\n",
        "const queryInput = clean(args.query || source.query || '');\nconst topicInput = clean(args.topic || source.topic || '');\nconst languageInput = clean(args.language || source.language || '');\nconst sortByInput = clean(args.sortBy || args.sort_by || source.sortBy || source.sort_by || '');\nconst usernameInput = clean(args.username || source.username || '');\nconst visibilityInput = clean(args.visibility || source.visibility || '');\nconst pageInput = Number(args.page || source.page || 1) || 1;\n",
    )

    js_code = replace_once(
        js_code,
        "let query = queryInput;\nlet limit = limitInput > 0 ? limitInput : 20;\n",
        "let query = queryInput;\nlet topic = topicInput;\nlet language = languageInput;\nlet sortBy = sortByInput;\nlet username = usernameInput;\nlet visibility = visibilityInput;\nlet page = pageInput > 0 ? pageInput : 1;\nlet limit = limitInput > 0 ? limitInput : 20;\n",
    )

    js_code = replace_once(
        js_code,
        "  case 'github.search_code':\n  case 'github_search_code':\n",
        "  case 'github.list_user_repos':\n  case 'github_list_user_repos':\n    if (!username) {\n      endpointPath = `/user/repos?per_page=${Math.max(1, Math.min(limit, 100))}&page=${Math.max(1, page)}`;\n    } else {\n      endpointPath = `/users/${encodeURIComponent(username)}/repos?per_page=${Math.max(1, Math.min(limit, 100))}&page=${Math.max(1, page)}`;\n    }\n    if (visibility) {\n      endpointPath += `${endpointPath.includes('?') ? '&' : '?'}visibility=${encodeURIComponent(visibility)}`;\n    }\n    summaryLabel = 'user_repos';\n    useAuth = true;\n    break;\n  case 'github.search_repos':\n  case 'github_search_repos':\n    if (!query && !topic) {\n      return [{ json: { ok: false, error: 'Missing search query.', tool, requestId: clean(source.requestId || '') } }];\n    }\n    if (!query) {\n      query = topic;\n    }\n    const qParts = [query].filter(Boolean);\n    if (topic && !qParts.join(' ').includes(`topic:${topic}`)) {\n      qParts.push(`topic:${topic}`);\n    }\n    if (language) {\n      qParts.push(`language:${language}`);\n    }\n    const sortMap = {\n      best_match: '',\n      most_stars: 'stars',\n      fewest_stars: 'stars',\n      most_forks: 'forks',\n      fewest_forks: 'forks',\n      recently_updated: 'updated',\n      least_recently_updated: 'updated',\n    };\n    const orderMap = {\n      best_match: 'desc',\n      most_stars: 'desc',\n      fewest_stars: 'asc',\n      most_forks: 'desc',\n      fewest_forks: 'asc',\n      recently_updated: 'desc',\n      least_recently_updated: 'asc',\n    };\n    const sortField = sortMap[sortBy] || '';\n    const orderField = orderMap[sortBy] || 'desc';\n    endpointPath = `/search/repositories?${buildQueryString({\n      q: qParts.join(' ').trim(),\n      sort: sortField,\n      order: sortField ? orderField : '',\n      per_page: Math.max(1, Math.min(limit, 100)),\n      page: Math.max(1, page),\n    })}`;\n    summaryLabel = 'search_repos';\n    useAuth = true;\n    break;\n  case 'github.search_code':\n  case 'github_search_code':\n",
    )

    return js_code


def patch_github_result(js_code: str) -> str:
    js_code = replace_once(
        js_code,
        "} else if (source.summaryLabel === 'search') {",
        "} else if (source.summaryLabel === 'user_repos') {\n  const rows = Array.isArray(data) ? data : items;\n  text = normalizeArrayRows(rows, (repoItem, index) => {\n    const name = clean(repoItem.full_name || repoItem.name || `repo-${index + 1}`);\n    const description = clean(repoItem.description || '');\n    const stars = Number(repoItem.stargazers_count || 0);\n    const language = clean(repoItem.language || '');\n    const htmlUrl = clean(repoItem.html_url || '');\n    const extra = [\n      stars ? `${stars}★` : '',\n      language,\n    ].filter(Boolean).join(' | ');\n    return `${index + 1}. ${name}${extra ? ` | ${extra}` : ''}${description ? ` | ${description}` : ''}${htmlUrl ? ` | ${htmlUrl}` : ''}`.trim();\n  });\n  links = rows.map((item) => clean(item.html_url || '')).filter(Boolean).slice(0, 10);\n  result = rows;\n} else if (source.summaryLabel === 'search_repos') {\n  const rows = Array.isArray(data.items) ? data.items : [];\n  text = [\n    data.total_count ? `Total matched: ${data.total_count}` : '',\n    normalizeArrayRows(rows, (repoItem, index) => {\n      const name = clean(repoItem.full_name || repoItem.name || `repo-${index + 1}`);\n      const description = clean(repoItem.description || '');\n      const stars = Number(repoItem.stargazers_count || 0);\n      const forks = Number(repoItem.forks_count || 0);\n      const language = clean(repoItem.language || '');\n      const htmlUrl = clean(repoItem.html_url || '');\n      const metrics = [\n        stars ? `${stars}★` : '',\n        forks ? `${forks}⑂` : '',\n        language,\n      ].filter(Boolean).join(' | ');\n      return `${index + 1}. ${name}${metrics ? ` | ${metrics}` : ''}${description ? ` | ${description}` : ''}${htmlUrl ? ` | ${htmlUrl}` : ''}`.trim();\n    }),\n  ].filter(Boolean).join('\\n');\n  links = rows.map((item) => clean(item.html_url || '')).filter(Boolean).slice(0, 10);\n  result = rows;\n} else if (source.summaryLabel === 'search') {\n",
    )
    js_code = replace_once(
        js_code,
        "    data: output,\n    meta: {",
        "    data: output,\n    followupPrompt: source.summaryLabel === 'search_repos' || source.summaryLabel === 'user_repos' ? 'Anh muốn mình đi sâu repo nào? Trả số thứ tự hoặc tên repo, ví dụ: repo 1.' : '',\n    meta: {",
    )
    return js_code


def main() -> None:
    workflow = json.loads(PATH.read_text())
    changed = False
    for node in workflow.get("nodes", []):
        params = node.get("parameters") or {}
        js_code = params.get("jsCode")
        if not isinstance(js_code, str):
            continue
        if node.get("name") == "Normalize GitHub Input":
            new_js_code = patch_github_input(js_code)
            if new_js_code != js_code:
                params["jsCode"] = new_js_code
                node["parameters"] = params
                changed = True
        elif node.get("name") == "Normalize GitHub Result":
            new_js_code = patch_github_result(js_code)
            if new_js_code != js_code:
                params["jsCode"] = new_js_code
                node["parameters"] = params
                changed = True
    if changed:
        PATH.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
        print(f"patched {PATH}")
    else:
        print(f"no changes needed for {PATH}")


if __name__ == "__main__":
    main()
