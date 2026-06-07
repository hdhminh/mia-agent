from __future__ import annotations

import re
from typing import Any

from mia_core import capabilities as caps
from mia_core.config import Settings
from mia_core.error_envelope import ErrorEnvelope
from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient
from mia_core.memory import MemoryRepository
from langchain.messages import HumanMessage, SystemMessage
from mia_core.response_normalizer import (
    coerce_message_text as normalized_coerce_message_text,
    sanitize_final_text as normalized_sanitize_final_text,
)
from mia_core.prompts import (
    GITHUB_SEARCH_FOLLOWUP_CUES,
    GITHUB_REPO_DRILLDOWN_CUES,
    GITHUB_REPO_TECH_CUES,
    GITHUB_REPO_TECH_FILE_PROBES,
)


class GitHubHandler:
    def __init__(self, service: Any) -> None:
        self.service = service
        self.tool_gateway = service.tool_gateway
        self.memory_repo = service.memory_repo
        self.settings = service.settings
        self.document_followup_model = service.document_followup_model
        self.document_followup_fallback_model = service.document_followup_fallback_model

    @staticmethod
    def _error_response(
        request: MiaChatRequest,
        error: ErrorEnvelope,
        *,
        tools_called: list[str] | None = None,
    ) -> MiaChatResponse:
        return MiaChatResponse(
            ok=False,
            final_text=error.display_text(),
            tools_called=tools_called or [],
            thread_id=request.resolved_thread_id(),
            request_id=request.resolved_request_id(),
            trace={"error": error.model_dump(mode="json")},
            error=error,
        )

    def _github_repo_probe_order(self, repo_context: dict[str, str], readme_only: bool = False) -> list[str]:
        language = str(repo_context.get("language") or "").lower()
        probe_order = ["README.md"]

        if readme_only:
            return probe_order

        if "python" in language:
            probe_order.extend(
                [
                    "pyproject.toml",
                    "requirements.txt",
                    "uv.lock",
                    "poetry.lock",
                    "Pipfile",
                    "Dockerfile",
                ]
            )
        elif any(token in language for token in ("javascript", "typescript", "node", "react", "vue", "svelte")):
            probe_order.extend(
                [
                    "package.json",
                    "pnpm-lock.yaml",
                    "package-lock.json",
                    "yarn.lock",
                    "tsconfig.json",
                    "Dockerfile",
                ]
            )
        elif "go" in language:
            probe_order.extend(["go.mod", "go.sum", "Dockerfile", "Makefile"])
        elif any(token in language for token in ("rust", "cargo")):
            probe_order.extend(["Cargo.toml", "Cargo.lock", "Dockerfile"])
        elif any(token in language for token in ("java", "kotlin")):
            probe_order.extend(["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "Dockerfile"])
        else:
            probe_order.extend(
                [
                    "package.json",
                    "pyproject.toml",
                    "requirements.txt",
                    "go.mod",
                    "Cargo.toml",
                    "Dockerfile",
                    "docker-compose.yml",
                    "Makefile",
                ]
            )

        probe_order.extend(
            [
                "docker-compose.yml",
                "docker-compose.yaml",
                "Makefile",
            ]
        )
        deduped: list[str] = []
        seen: set[str] = set()
        for path in probe_order:
            clean = path.strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(clean)
        return deduped

    def _collect_github_repo_analysis(
        self,
        request: MiaChatRequest,
        context: MiaContext,
        repo_context: dict[str, str],
        readme_only: bool = False,
    ) -> tuple[list[tuple[str, str]], list[str], list[dict[str, str]], ErrorEnvelope | None]:
        sections: list[tuple[str, str]] = []
        tools_called: list[str] = []
        code_search_hits: list[dict[str, str]] = []
        last_error: ErrorEnvelope | None = None

        repo_info_result = None
        try:
            repo_info_result = self.tool_gateway.run_tool(
                "github.get_repo",
                {
                    "repo": repo_context.get("repo", ""),
                    "owner": repo_context.get("owner", ""),
                    "repoName": repo_context.get("repoName", ""),
                    "repoUrl": repo_context.get("repoUrl", ""),
                },
                context,
                request_text=request.text,
            )
        except Exception:
            repo_info_result = None
        if repo_info_result and repo_info_result.ok and repo_info_result.text.strip():
            tools_called.append("github_get_repo")
            sections.append(("Repo info", repo_info_result.text.strip()))
        elif repo_info_result and not repo_info_result.ok and repo_info_result.error:
            last_error = repo_info_result.error

        if not readme_only:
            repo_tree_result = None
            try:
                repo_tree_result = self.tool_gateway.run_tool(
                    "github.get_repo_tree",
                    {
                        "repo": repo_context.get("repo", ""),
                        "owner": repo_context.get("owner", ""),
                        "repoName": repo_context.get("repoName", ""),
                        "repoUrl": repo_context.get("repoUrl", ""),
                        "ref": repo_context.get("ref", ""),
                        "path": "",
                        "limit": 20,
                    },
                    context,
                    request_text=f"{request.text} :: repo tree",
                )
            except Exception:
                repo_tree_result = None
            if repo_tree_result and repo_tree_result.ok and repo_tree_result.text.strip():
                tools_called.append("github_get_repo_tree")
                sections.append(("Repo tree", repo_tree_result.text.strip()))
            elif repo_tree_result and not repo_tree_result.ok and repo_tree_result.error:
                last_error = repo_tree_result.error

        probe_order = self._github_repo_probe_order(repo_context, readme_only=readme_only)
        max_extra_files = 1 if readme_only else 4
        extra_reads = 0
        for path in probe_order:
            if extra_reads >= max_extra_files:
                break
            result = None
            try:
                result = self.tool_gateway.run_tool(
                    "github.get_file",
                    {
                        "repo": repo_context.get("repo", ""),
                        "owner": repo_context.get("owner", ""),
                        "repoName": repo_context.get("repoName", ""),
                        "repoUrl": repo_context.get("repoUrl", ""),
                        "path": path,
                        "ref": "",
                        "maxChars": 5000 if path.lower() == "readme.md" else 3500,
                    },
                    context,
                    request_text=f"{request.text} :: {path}",
                )
            except Exception:
                continue
            if not result.ok or not result.text.strip():
                if not result.ok and result.error:
                    last_error = result.error
                continue
            if path.lower() == "readme.md":
                tools_called.append("github_get_file")
                sections.append(("README", result.text.strip()))
                extra_reads += 1
                continue
            tools_called.append("github_get_file")
            sections.append((path, result.text.strip()))
            extra_reads += 1

        if not readme_only:
            code_search_queries = self._github_repo_code_search_queries(repo_context)
            max_searches = 2
            for query in code_search_queries[:max_searches]:
                try:
                    result = self.tool_gateway.run_tool(
                        "github.search_code",
                        {
                            "repo": repo_context.get("repo", ""),
                            "owner": repo_context.get("owner", ""),
                            "repoName": repo_context.get("repoName", ""),
                            "repoUrl": repo_context.get("repoUrl", ""),
                            "query": query,
                            "limit": 5,
                        },
                        context,
                        request_text=f"{request.text} :: code search :: {query}",
                    )
                except Exception:
                    continue
                if not result.ok or not result.text.strip():
                    if not result.ok and result.error:
                        last_error = result.error
                    continue
                tools_called.append("github_search_code")
                sections.append((f"Code search: {query}", result.text.strip()))
                code_search_hits.append({"query": query, "text": result.text.strip()})

        return sections, tools_called, code_search_hits, last_error

    def _github_repo_code_search_queries(self, repo_context: dict[str, str]) -> list[str]:
        language = str(repo_context.get("language") or "").lower()
        description = str(repo_context.get("description") or "").lower()
        queries: list[str] = []

        if "python" in language:
            queries.extend([
                'def main',
                '__name__ == "__main__"',
                "FastAPI",
                "Streamlit",
                "click",
                "typer",
            ])
        elif any(token in language for token in ("javascript", "typescript", "node", "react", "vue", "svelte")):
            queries.extend([
                "app.listen",
                "createRoot",
                "export default",
                "main.ts",
                "index.ts",
                "vite",
            ])
        elif "go" in language:
            queries.extend([
                "func main",
                "cobra.Command",
                "cmd/",
                "main.go",
            ])
        elif any(token in language for token in ("java", "kotlin")):
            queries.extend([
                "public static void main",
                "SpringApplication.run",
                "@SpringBootApplication",
            ])
        elif any(token in language for token in ("rust", "cargo")):
            queries.extend([
                "fn main",
                "cargo",
                "mod ",
            ])
        else:
            queries.extend([
                "main",
                "app",
                "server",
                "cli",
            ])

        if any(token in description for token in ("fastapi", "streamlit", "gradio", "cli", "api", "server", "web", "app")):
            queries.extend([
                "FastAPI",
                "Streamlit",
                "Gradio",
                "app",
                "server",
            ])

        deduped: list[str] = []
        seen: set[str] = set()
        for query in queries:
            clean = " ".join(str(query or "").split()).strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(clean)
        return deduped[:8]

    def _extract_github_repo_commands(self, sections: list[tuple[str, str]]) -> list[str]:
        command_patterns = (
            r"^\s*(uv|python|pip|poetry|docker|docker-compose|make|npm|pnpm|yarn|go|cargo|git|bash|sh|curl|powershell|pwsh|ffmpeg|conda)\b.*$",
            r"^\s*(uv\s+sync|uv\s+run\s+\S+|python\s+\S+|pip\s+\S+|docker\s+\S+|docker-compose\s+\S+|make\s+\S+|npm\s+\S+|pnpm\s+\S+|yarn\s+\S+|go\s+\S+|cargo\s+\S+|git\s+\S+|ffmpeg\s+\S+).*$",
        )
        commands: list[str] = []
        seen: set[str] = set()
        for _, text in sections:
            for raw_line in str(text or "").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if len(line) > 180:
                    continue
                if not any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in command_patterns):
                    continue
                if line.startswith((">", "-", "*", "•", "#")):
                    line = line.lstrip("> -*•#").strip()
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                commands.append(line)
                if len(commands) >= 10:
                    return commands
        return commands

    def _limit_text_to_bullets(self, text: str, max_bullets: int = 6) -> str:
        cleaned = normalized_sanitize_final_text(text or "")
        if not cleaned:
            return cleaned

        lines = [line.rstrip() for line in cleaned.splitlines()]
        bullet_lines: list[str] = []
        bullet_pattern = re.compile(r"^\s*(?:[-*•]|(?:\d+[.)]))\s+(.*\S)\s*$")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            match = bullet_pattern.match(stripped)
            if match:
                bullet_lines.append(match.group(1).strip())

        if len(bullet_lines) <= max_bullets:
            if bullet_lines:
                return "\n".join(f"- {item}" for item in bullet_lines)
            fallback_lines = [line for line in (part.strip() for part in cleaned.splitlines()) if line]
            if not fallback_lines:
                return cleaned
            return "\n".join(f"- {line}" for line in fallback_lines[:max_bullets])

        limited = [f"- {item}" for item in bullet_lines[:max_bullets - 1]]
        remaining_count = len(bullet_lines) - (max_bullets - 1)
        limited.append(
            f"- Còn {remaining_count} ý nữa đã được lược bớt; nếu anh muốn, Mia sẽ bóc tiếp chi tiết từng file hoặc lệnh."
        )
        return "\n".join(limited)

    def _summarize_github_repo_analysis(
        self,
        request: MiaChatRequest,
        repo_context: dict[str, str],
        sections: list[tuple[str, str]],
    ) -> tuple[str, dict[str, Any]]:
        repo_lines = [f"- {key}: {value}" for key, value in repo_context.items() if value]
        section_text = "\n\n".join(f"[{title}]\n{text}" for title, text in sections if text.strip())
        command_lines = self._extract_github_repo_commands(sections)
        command_text = "\n".join(f"- {line}" for line in command_lines) if command_lines else "không thấy lệnh rõ ràng trong dữ liệu"
        result, provider_used = self.service._invoke_model_with_fallback(
            self.document_followup_model,
            self.document_followup_fallback_model,
            [
                SystemMessage(
                    content=(
                        "Bạn là Mia. Hãy trả lời ngắn gọn, dễ đọc, đúng trọng tâm kỹ thuật, dựa hoàn toàn trên dữ liệu được cung cấp. "
                        "Không bịa thông tin nếu chưa thấy trong nội dung. Không trả lời kiểu menu, không hỏi người dùng chọn tiếp một mục khác.\n"
                        "Bắt buộc theo format sau, mỗi mục 1-3 dòng ngắn:\n"
                        "1. Mục đích repo\n"
                        "2. Tech stack / runtime\n"
                        "3. Lệnh quan trọng: phải nêu rõ lệnh chạy hoặc cài đặt nếu đã thấy; nếu không thấy thì ghi rõ 'chưa thấy lệnh cụ thể'\n"
                        "4. File quan trọng\n"
                        "5. Tín hiệu code search\n"
                        "6. Rủi ro / lưu ý\n"
                        "7. Gợi ý đọc tiếp\n"
                        "Yêu cầu trình bày:\n"
                        "- Ưu tiên bullet ngắn, flat bullet, không văn xuôi dài.\n"
                        "- Không quá 6 bullet chính.\n"
                        "- Nếu có lệnh thì ghi đúng nguyên văn lệnh đã xuất hiện trong dữ liệu, không tự chế.\n"
                        "- Nếu user hỏi về kĩ thuật/build/setup/runtime thì mục 'Lệnh quan trọng' phải nổi bật nhất.\n"
                        "- Nếu dữ liệu chưa đủ, chỉ nói phần nào chưa thấy, không suy diễn."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Câu hỏi của người dùng:\n{request.text}\n\n"
                        f"Repo đang phân tích:\n{chr(10).join(repo_lines) if repo_lines else 'không rõ'}\n\n"
                        f"Lệnh đã trích từ dữ liệu:\n{command_text}\n\n"
                        f"Dữ liệu đã đọc:\n{section_text or 'không có dữ liệu bổ sung'}\n\n"
                        "Hãy viết câu trả lời cuối cùng, không nhắc tên tool."
                    )
                ),
            ],
            scope="agent:github-repo-analysis",
        )
        analysis_text = self._limit_text_to_bullets(normalized_coerce_message_text(result.content), max_bullets=6)
        analysis_trace = self.service._cache_trace(result, scope="agent:github-repo-analysis", provider_used=provider_used)
        analysis_trace["provider"] = provider_used
        return analysis_text, analysis_trace

    def _write_github_repo_analysis_memory(
        self,
        request: MiaChatRequest,
        repo_context: dict[str, str],
        sections: list[tuple[str, str]],
        summary_text: str,
        code_search_hits: list[dict[str, str]],
    ) -> None:
        repo_name = str(repo_context.get("repo") or repo_context.get("repoName") or "github repo").strip()
        if not summary_text.strip():
            return

        lines = [
            f"Repo đã phân tích: {repo_name}",
        ]
        if repo_context.get("repoUrl"):
            lines.append(f"URL: {repo_context['repoUrl']}")
        if repo_context.get("language"):
            lines.append(f"Language: {repo_context['language']}")
        if repo_context.get("description"):
            lines.append(f"Description: {repo_context['description']}")
        lines.append("")
        lines.append("Tóm tắt kỹ thuật:")
        lines.append(summary_text.strip())

        if sections:
            lines.append("")
            lines.append("Dữ liệu đã đọc:")
            for title, text in sections[:8]:
                snippet = " ".join(str(text or "").split()).strip()
                if len(snippet) > 350:
                    snippet = snippet[:350].rstrip() + "..."
                lines.append(f"- {title}: {snippet}")

        if code_search_hits:
            lines.append("")
            lines.append("Code search:")
            for hit in code_search_hits[:4]:
                query = str(hit.get("query") or "").strip()
                snippet = " ".join(str(hit.get("text") or "").split()).strip()
                if len(snippet) > 260:
                    snippet = snippet[:260].rstrip() + "..."
                lines.append(f"- {query}: {snippet}")

        try:
            self.memory_repo.write(
                chat_id=request.chat_id,
                content="\n".join(lines).strip(),
                memory_type="github_repo_analysis",
                title=repo_name,
                tags=[
                    "github",
                    "repo_analysis",
                    repo_name,
                    str(repo_context.get("language") or "").strip(),
                ],
                importance=5,
                source_text=summary_text.strip(),
            )
        except Exception:
            pass

    @staticmethod
    def _parse_github_search_memory(content: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        compact = " ".join(str(content or "").split())
        chunks = re.split(r"(?=\b\d+\.\s+)", compact) if compact else []
        if not chunks:
            chunks = str(content or "").splitlines()

        for raw_line in chunks:
            line = raw_line.strip()
            match = re.match(
                r"^(?P<index>\d+)\.\s*(?P<name>[^|]+?)(?:\s*\|\s*(?P<rest>.*))?$",
                line,
            )
            if not match:
                continue
            name = str(match.group("name") or "").strip()
            rest = str(match.group("rest") or "").strip()
            url = ""
            description = ""
            stars = ""
            forks = ""
            language = ""
            if rest:
                parts = [part.strip() for part in rest.split("|") if part.strip()]
                for part in parts:
                    if part.startswith("http://") or part.startswith("https://"):
                        url = part
                    elif part.endswith("★") or part.endswith("⑂"):
                        if part.endswith("★"):
                            stars = part
                        elif part.endswith("⑂"):
                            forks = part
                    elif not language and len(part) <= 40 and re.fullmatch(r"[A-Za-z0-9_.#+-]+", part):
                        language = part
                    elif not description:
                        description = part
                    else:
                        description = f"{description} | {part}".strip(" |")
            rows.append(
                {
                    "name": name,
                    "url": url,
                    "description": description,
                    "stars": stars,
                    "forks": forks,
                    "language": language,
                }
            )
        return rows

    @staticmethod
    def _repo_context_from_search_row(row: dict[str, str]) -> dict[str, str]:
        name = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        description = str(row.get("description") or "").strip()
        language = str(row.get("language") or "").strip()
        stars = str(row.get("stars") or "").strip()
        forks = str(row.get("forks") or "").strip()
        owner = ""
        repo_name = ""
        if name and "/" in name:
            owner, repo_name = name.split("/", 1)
        if not owner and url:
            match = re.search(r"https?://github\.com/([^/]+)/([^/]+)", url, flags=re.IGNORECASE)
            if match:
                owner = match.group(1).strip()
                repo_name = match.group(2).strip()
        repo = f"{owner}/{repo_name}".strip("/") if owner and repo_name else name
        repo_url = url or (f"https://github.com/{repo}" if repo and "/" in repo else "")
        context = {
            "repo": repo,
            "owner": owner,
            "repoName": repo_name,
            "repoUrl": repo_url,
            "description": description,
            "language": language,
            "stars": stars,
            "forks": forks,
        }
        return {key: value for key, value in context.items() if value}

    @staticmethod
    def _repo_context_from_selected_memory(content: str) -> dict[str, str]:
        text = str(content or "").strip()
        if not text:
            return {}
        name = ""
        url = ""
        description = ""
        language = ""
        stars = ""
        forks = ""
        name_match = re.search(r"Repo đã (?:chọn|phân tích):\s*(.+?)(?:\s+URL:|\s+Nguồn search:|\s+Nguon search:|$)", text, flags=re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
        if not name:
            first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
            if first_line:
                name = first_line
        name = re.split(r"\s+URL:\s*", name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        name = re.split(r"\s+Nguồn search:\s*", name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        name = re.split(r"\s+Nguon search:\s*", name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            lower = line.lower()
            if lower.startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif lower.startswith("language:"):
                language = line.split(":", 1)[1].strip()
            elif lower.startswith("stars:"):
                stars = line.split(":", 1)[1].strip()
            elif lower.startswith("forks:"):
                forks = line.split(":", 1)[1].strip()
        url_match = re.search(r"https?://github\.com/[^ \n]+", text, flags=re.IGNORECASE)
        if url_match:
            url = url_match.group(0).strip()
        owner = ""
        repo_name = ""
        if url:
            match = re.search(r"https?://github\.com/([^/]+)/([^/]+)", url, flags=re.IGNORECASE)
            if match:
                owner = match.group(1).strip()
                repo_name = match.group(2).strip()
        if not owner and name and "/" in name:
            owner, repo_name = name.split("/", 1)
        repo = f"{owner}/{repo_name}".strip("/") if owner and repo_name else name
        repo_url = url or (f"https://github.com/{repo}" if repo and "/" in repo else "")
        context = {
            "repo": repo,
            "owner": owner,
            "repoName": repo_name,
            "repoUrl": repo_url,
            "description": description,
            "language": language,
            "stars": stars,
            "forks": forks,
        }
        return {key: value for key, value in context.items() if value}

    def _latest_selected_github_repo_context(self, request: MiaChatRequest) -> dict[str, str]:
        recent_rows = self.memory_repo.recent(chat_id=request.chat_id, limit=8)
        analysis_rows = [row for row in recent_rows if str(row.get("memory_type") or "") == "github_repo_analysis"]
        if analysis_rows:
            analysis_content = str(analysis_rows[0].get("content") or "")
            analysis_context = self._repo_context_from_selected_memory(analysis_content)
            if analysis_context:
                return analysis_context

        selected_rows = [row for row in recent_rows if str(row.get("memory_type") or "") == "github_repo_selected"]
        if selected_rows:
            selected_content = str(selected_rows[0].get("content") or "")
            selected_context = self._repo_context_from_selected_memory(selected_content)
            if selected_context:
                return selected_context

        search_rows = [row for row in recent_rows if str(row.get("memory_type") or "") == "github_repo_search"]
        if search_rows:
            parsed_search_rows = self._parse_github_search_memory(str((search_rows[0] or {}).get("content") or "")) if search_rows else []
            if parsed_search_rows:
                for candidate in parsed_search_rows[:3]:
                    repo_context = self._repo_context_from_search_row(candidate)
                    if repo_context:
                        return repo_context
        return {}

    def _try_github_selected_repo_followup(self, request: MiaChatRequest, context: MiaContext) -> MiaChatResponse | None:
        text = " ".join(str(request.text or "").split()).strip()
        if not text:
            return None

        normalized = text.lower()
        repo_context = self._latest_selected_github_repo_context(request)
        if not repo_context:
            return None

        wants_readme = any(
            cue in normalized
            for cue in (
                "readme",
                "read me",
                "tóm tắt readme",
                "tom tat readme",
                "summary readme",
                "summarize readme",
                "overview readme",
            )
        )
        wants_overview = any(
            cue in normalized
            for cue in (
                "xem tong quan",
                "xem tổng quan",
                "tong quan",
                "tổng quan",
                "overview",
                "thong tin repo",
                "thông tin repo",
            )
        )
        wants_tree = any(
            cue in normalized
            for cue in (
                "cau truc",
                "cấu trúc",
                "tree",
                "repo tree",
                "cay repo",
                "cây repo",
            )
        )
        wants_tech = any(cue in normalized for cue in GITHUB_REPO_TECH_CUES)
        wants_branch = any(cue in normalized for cue in ("branch", "branches", "nhanh", "nhánh"))

        if not (wants_readme or wants_overview or wants_branch or wants_tree or wants_tech):
            return None

        if wants_tree and not (wants_readme or wants_overview or wants_tech):
            tool_args = {
                "repo": repo_context.get("repo", ""),
                "owner": repo_context.get("owner", ""),
                "repoName": repo_context.get("repoName", ""),
                "repoUrl": repo_context.get("repoUrl", ""),
                "ref": repo_context.get("ref", ""),
                "path": "",
                "limit": 20,
            }
            try:
                result = self.tool_gateway.run_tool(
                    "github.get_repo_tree",
                    tool_args,
                    context,
                    request_text=request.text,
                )
            except Exception:
                return None
            if not result.ok:
                error = result.error or ErrorEnvelope.build(
                    code="github_get_repo_tree_failed",
                    category="external",
                    severity="error",
                    message=str(result.text or "github.get_repo_tree failed."),
                    user_message=str(result.text or "Mia chưa đọc được cây repo này."),
                    request_id=request.resolved_request_id(),
                    thread_id=request.resolved_thread_id(),
                    chat_id=request.chat_id,
                )
                return self._error_response(request, error, tools_called=["github_get_repo_tree"])
            if not result.text.strip():
                return None
            return MiaChatResponse(
                ok=True,
                final_text=self._limit_text_to_bullets(normalized_sanitize_final_text(result.text), max_bullets=6),
                tools_called=["github_get_repo_tree"],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={"tool": result.payload.get("data", {}) if isinstance(result.payload, dict) else {}},
            )

        if wants_readme or wants_overview or wants_tech or wants_tree:
            readme_only = wants_readme and not (wants_overview or wants_tree or wants_tech)
            sections, tools_called, code_search_hits, last_error = self._collect_github_repo_analysis(
                request,
                context,
                repo_context,
                readme_only=readme_only,
            )
            if not sections:
                if last_error is not None:
                    return self._error_response(request, last_error, tools_called=tools_called or ["github_get_repo", "github_get_file"])
                return MiaChatResponse(
                    ok=False,
                    final_text="Mia chưa đọc được đủ dữ liệu của repo này để phân tích sâu. Anh thử lại hoặc chọn repo khác nhé.",
                    tools_called=tools_called or ["github_get_repo", "github_get_file"],
                    thread_id=request.resolved_thread_id(),
                    request_id=request.resolved_request_id(),
                    trace={},
                )
            summary_text, summary_trace = self._summarize_github_repo_analysis(request, repo_context, sections)
            final_text = summary_text or normalized_sanitize_final_text("\n\n".join(text for _, text in sections))
            self._write_github_repo_analysis_memory(
                request=request,
                repo_context=repo_context,
                sections=sections,
                summary_text=final_text,
                code_search_hits=code_search_hits,
            )
            return MiaChatResponse(
                ok=True,
                final_text=final_text,
                tools_called=tools_called or ["github_get_repo", "github_get_file"],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={"llm": summary_trace},
            )

        if wants_branch:
            tool_args = {
                "repo": repo_context.get("repo", ""),
                "owner": repo_context.get("owner", ""),
                "repoName": repo_context.get("repoName", ""),
                "repoUrl": repo_context.get("repoUrl", ""),
                "limit": 20,
            }
            try:
                result = self.tool_gateway.run_tool(
                    "github.list_branches",
                    tool_args,
                    context,
                    request_text=request.text,
                )
            except Exception:
                return None
            if not result.ok:
                error = result.error or ErrorEnvelope.build(
                    code="github_list_branches_failed",
                    category="external",
                    severity="error",
                    message=str(result.text or "github.list_branches failed."),
                    user_message=str(result.text or "Mia chưa đọc được danh sách branch."),
                    request_id=request.resolved_request_id(),
                    thread_id=request.resolved_thread_id(),
                    chat_id=request.chat_id,
                )
                return self._error_response(request, error, tools_called=["github_list_branches"])
            if not result.text.strip():
                return None
            return MiaChatResponse(
                ok=True,
                final_text=normalized_sanitize_final_text(result.text),
                tools_called=["github_list_branches"],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={"tool": result.payload.get("data", {}) if isinstance(result.payload, dict) else {}},
            )

        return None

    def _try_github_search_followup(self, request: MiaChatRequest) -> MiaChatResponse | None:
        text = " ".join(str(request.text or "").split()).strip()
        if not text:
            return None

        normalized = text.lower()
        recent_rows = self.memory_repo.recent(chat_id=request.chat_id, limit=8)
        search_rows = [row for row in recent_rows if str(row.get("memory_type") or "") == "github_repo_search"]
        selected_rows = [row for row in recent_rows if str(row.get("memory_type") or "") == "github_repo_selected"]
        if not search_rows and not selected_rows:
            return None

        latest_search = search_rows[0] if search_rows else None
        parsed_search_rows = self._parse_github_search_memory(str((latest_search or {}).get("content") or "")) if latest_search else []
        if not parsed_search_rows:
            return None

        selection_match = re.search(
            r"(?:repo|kq|ket qua|kết quả|ket qua|so|số|thu|thứ)?\s*#?\s*(\d+)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        selection_index = int(selection_match.group(1)) if selection_match else 0
        has_drilldown_cue = any(cue.lower() in normalized for cue in GITHUB_REPO_DRILLDOWN_CUES)
        has_selection_cue = any(cue in normalized for cue in GITHUB_SEARCH_FOLLOWUP_CUES) or bool(selection_match)
        explicit_selection = selection_index > 0 or bool(selection_match)

        if selection_index <= 0 and not has_drilldown_cue and not has_selection_cue:
            return None

        selected_row: dict[str, str] | None = None
        if 1 <= selection_index <= len(parsed_search_rows):
            selected_row = parsed_search_rows[selection_index - 1]
        elif selected_rows:
            selected_content = str(selected_rows[0].get("content") or "")
            selected_context = self._repo_context_from_selected_memory(selected_content)
            if selected_context:
                selected_row = {
                    "name": selected_context.get("repo", ""),
                    "url": selected_context.get("repoUrl", ""),
                    "description": "",
                    "stars": "",
                    "forks": "",
                    "language": "",
                }
        elif has_drilldown_cue and len(parsed_search_rows) == 1:
            selected_row = parsed_search_rows[0]

        if not selected_row:
            if has_drilldown_cue and parsed_search_rows:
                return MiaChatResponse(
                    ok=True,
                    final_text=(
                        "Mia đã tìm được repo rồi, nhưng anh chưa chọn repo cụ thể. "
                        "Anh trả số thứ tự, ví dụ repo 1 hoặc repo 2, rồi Mia sẽ đi sâu tiếp."
                    ),
                    tools_called=["memory_search"],
                    thread_id=request.resolved_thread_id(),
                    request_id=request.resolved_request_id(),
                    trace={},
                )
            return None

        repo_context = self._repo_context_from_search_row(selected_row)
        if not repo_context:
            return None

        if explicit_selection:
            if selected_row.get("name"):
                selection_title = f"Repo đã chọn: {selected_row['name']}"
            else:
                selection_title = "Repo đã chọn"
            selection_content_lines = [selection_title]
            if selected_row.get("url"):
                selection_content_lines.append(f"URL: {selected_row['url']}")
            if selected_row.get("description"):
                selection_content_lines.append(f"Description: {selected_row['description']}")
            if selected_row.get("language"):
                selection_content_lines.append(f"Language: {selected_row['language']}")
            if selected_row.get("stars"):
                selection_content_lines.append(f"Stars: {selected_row['stars']}")
            if selected_row.get("forks"):
                selection_content_lines.append(f"Forks: {selected_row['forks']}")
            if latest_search and latest_search.get("title"):
                selection_content_lines.append(f"Nguồn search: {latest_search.get('title')}")
            try:
                self.memory_repo.write(
                    chat_id=request.chat_id,
                    content="\n".join(selection_content_lines).strip(),
                    memory_type="github_repo_selected",
                    title=str(selected_row.get("name") or latest_search.get("title") or "github repo").strip(),
                    tags=["github", "selected_repo", str(selected_row.get("name") or "").strip()],
                    importance=4,
                    source_text="\n".join(selection_content_lines).strip(),
                )
            except Exception:
                pass

        if explicit_selection and not has_drilldown_cue:
            repo_name = repo_context.get("repo") or selected_row.get("name") or "repo này"
            return MiaChatResponse(
                ok=True,
                final_text=(
                    f"Mia đã chọn {repo_name}. "
                    "Anh muốn mình đi sâu phần nào tiếp theo: tóm tắt README, xem tổng quan, cấu trúc repo, kĩ thuật build, branch, file, code search hay diff?"
                ),
                tools_called=["memory_search"],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={},
            )

        if not explicit_selection and has_drilldown_cue:
            updated_metadata = dict(request.metadata or {})
            updated_metadata.update(repo_context)
            request.metadata = updated_metadata
            return None

        updated_metadata = dict(request.metadata or {})
        updated_metadata.update(repo_context)
        request.metadata = updated_metadata
        return None
