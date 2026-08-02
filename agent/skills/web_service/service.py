from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from langchain.messages import HumanMessage, SystemMessage

from agent.config import Settings
from agent.brain.llm_provider import build_primary_and_fallback_models
from agent.memory.repository import MemoryRepository
from agent.brain.prompt_cache import build_prompt_cache_key
from agent.brain.response_normalizer import sanitize_final_text
from agent.brain.trace_utils import extract_prompt_cache_trace
from agent.i18n import t
from agent.skills.media_service.local import normalize_spaces
from .schemas import WebResult


@dataclass(frozen=True)
class WebPage:
    url: str
    final_url: str
    title: str
    canonical_url: str
    description: str
    text: str
    links: list[str]
    mime_type: str
    status_code: int
    fetch_strategy: str


def _is_textual_content_type(content_type: str) -> bool:
    lowered = (content_type or "").lower()
    return any(
        lowered.startswith(prefix)
        for prefix in (
            "text/",
            "application/json",
            "application/xml",
            "application/xhtml+xml",
        )
    ) or "html" in lowered


def _compact_lines(text: str, limit: int = 12000) -> str:
    lines = [" ".join(line.split()).strip() for line in str(text or "").splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s<>\]\)\"']+", text or "", flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(0).rstrip(".,;!?")


def _normalize_fetch_strategy(value: str) -> str:
    strategy = str(value or "").strip().lower().replace("_", "-")
    if strategy in {"browser", "render"}:
        return "rendered"
    if strategy in {"rendered", "static", "auto"}:
        return strategy
    return "auto"


def _is_private_host(hostname: str) -> bool:
    host = str(hostname or "").strip().lower().strip("[]")
    if not host:
        return True
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
        return True
    if host.startswith(("127.", "10.", "192.168.", "0.", "169.254.")):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def _validate_public_url(url: str) -> None:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed.")
    hostname = parsed.hostname or ""
    if _is_private_host(hostname):
        raise ValueError("Private, local, or loopback URLs are not allowed.")
    try:
        default_port = 443 if parsed.scheme == "https" else 80
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, parsed.port or default_port, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("URL hostname could not be resolved.") from exc
    if not addresses or any(_is_private_host(address) for address in addresses):
        raise ValueError("URL resolves to a private, local, or reserved address.")


def _extract_main_html(html_text: str) -> str:
    text = str(html_text or "")
    for pattern in (
        r"(?is)<article\b[^>]*>(.*?)</article>",
        r"(?is)<main\b[^>]*>(.*?)</main>",
        r"(?is)<body\b[^>]*>(.*?)</body>",
    ):
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate
    return text


def _strip_html_noise(html_text: str) -> str:
    text = unescape(str(html_text or ""))
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?is)<(script|style|noscript|svg|canvas|iframe|form|header|footer|nav|aside)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<(script|style|noscript|svg|canvas|iframe|form|header|footer|nav|aside)\b[^>]*?/?>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"(?i)</div>", "\n", text)
    text = re.sub(r"(?i)</section>", "\n", text)
    text = re.sub(r"(?i)</article>", "\n\n", text)
    text = re.sub(r"(?i)</li>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    text = re.sub(r"(?i)</h[1-6]>", "\n", text)
    text = re.sub(r"(?i)<tr[^>]*>", "\n", text)
    text = re.sub(r"(?i)</tr>", "\n", text)
    text = re.sub(r"(?i)<t[dh][^>]*>", " ", text)
    text = re.sub(r"(?i)</t[dh]>", " ", text)
    text = re.sub(r"(?i)<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2 (\1)", text)
    text = re.sub(r"(?i)<a[^>]*href='([^']+)'[^>]*>(.*?)</a>", r"\2 (\1)", text)
    return text


def _clean_html_to_text(html_text: str) -> str:
    text = _extract_main_html(html_text)
    text = _strip_html_noise(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return normalize_spaces(text).strip()


def _extract_meta_value(html_text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = unescape(str(match.group(1) or "").strip())
            if value:
                return normalize_spaces(value)
    return ""


def _extract_links(html_text: str, base_url: str, limit: int = 12) -> list[str]:
    urls: list[str] = []
    for href in re.findall(r"""href=["']([^"']+)["']""", html_text or "", flags=re.IGNORECASE):
        candidate = unescape(str(href or "").strip())
        if not candidate or candidate.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, candidate)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if absolute not in urls:
            urls.append(absolute)
        if len(urls) >= limit:
            break
    return urls


def _looks_blocked(page: WebPage) -> bool:
    content = " ".join(
        part.lower()
        for part in (
            page.title,
            page.description,
            page.text,
        )
        if part
    )
    cues = (
        "captcha",
        "access denied",
        "blocked",
        "cloudflare",
        "attention required",
        "bot detection",
        "enable javascript",
        "sign in to continue",
        "verify you are human",
        "just a moment",
        "forbidden",
    )
    return page.status_code in {401, 403, 429, 503} or any(cue in content for cue in cues)


def _parse_page(response: httpx.Response, source_url: str, *, fetch_strategy: str = "static") -> WebPage:
    final_url = str(response.url).strip() or source_url
    mime_type = str(response.headers.get("content-type") or "").strip()
    raw_text = response.text if _is_textual_content_type(mime_type) else ""
    title = ""
    canonical_url = ""
    description = ""
    links: list[str] = []
    text = ""

    if raw_text:
        title = _extract_meta_value(
            raw_text,
            (
                r"<title[^>]*>(.*?)</title>",
                r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            ),
        )
        canonical_url = _extract_meta_value(
            raw_text,
            (
                r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
                r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']',
            ),
        )
        description = _extract_meta_value(
            raw_text,
            (
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']twitter:description["\'][^>]+content=["\']([^"\']+)["\']',
            ),
        )
        cleaned = _clean_html_to_text(raw_text)
        links = _extract_links(raw_text, final_url)
        if cleaned:
            text = cleaned
        elif description:
            text = description

    if not title:
        parsed = urlparse(final_url)
        title = parsed.netloc or source_url
    if not canonical_url:
        canonical_url = final_url

    return WebPage(
        url=source_url,
        final_url=final_url,
        title=title.strip(),
        canonical_url=canonical_url.strip(),
        description=description.strip(),
        text=text.strip(),
        links=links,
        mime_type=mime_type,
        status_code=response.status_code,
        fetch_strategy=fetch_strategy,
    )


class WebService:
    def __init__(self, settings: Settings, memory_repo: MemoryRepository | None = None) -> None:
        self.settings = settings
        self.memory_repo = memory_repo
        self.summary_models: dict[str, Any] = {}
        self.summary_fallback_models: dict[str, Any | None] = {}

    def _get_summary_model(self, scope: str) -> tuple[Any, Any | None]:
        if scope not in self.summary_models:
            primary, fallback = build_primary_and_fallback_models(
                self.settings,
                scope=scope,
                temperature=0,
                max_tokens=700,
            )
            self.summary_models[scope] = primary
            self.summary_fallback_models[scope] = fallback
        return self.summary_models[scope], self.summary_fallback_models.get(scope)

    def _prompt_cache_key(self, scope: str, *, provider_used: str = "primary") -> str:
        if not self.settings.prompt_cache_enabled:
            return ""
        provider_name = self.settings.primary_llm_provider if provider_used != "fallback" else "openrouter"
        return build_prompt_cache_key(
            namespace=self.settings.prompt_cache_namespace,
            scope=f"{provider_name}:{scope}",
            version=self.settings.prompt_cache_version,
        )

    def _trace(self, result: Any, *, scope: str, provider_used: str = "primary") -> dict[str, Any]:
        if result is None:
            return {}
        return extract_prompt_cache_trace(
            result,
            scope=scope,
            model=self.settings.deepseek_model if self.settings.primary_llm_provider == "deepseek_direct" and provider_used == "primary" else self.settings.model,
            prompt_cache_key=self._prompt_cache_key(scope, provider_used=provider_used),
        )

    def _store_url_context(
        self,
        *,
        chat_id: str,
        tool: str,
        page: WebPage,
        instruction: str,
        summary: str = "",
        content: str = "",
    ) -> None:
        if not self.memory_repo or not chat_id.strip():
            return

        title = page.title or page.canonical_url or page.final_url or page.url or "url_context"
        unknown_str = t("skills.unknown", default="không rõ")
        context_parts = [
            t("skills.result_label", default="Result: {text}", text=page.canonical_url or page.final_url or page.url),
            t("skills.title_label", default="Tiêu đề: {title}", title=page.title or unknown_str),
            f"Tool: {tool}",
        ]
        if instruction.strip():
            context_parts.append(t("skills.media_doc_qa_user", default="Yêu cầu bổ sung từ người dùng:\n{instruction}", instruction=instruction.strip()))
        if summary.strip():
            context_parts.append(t("skills.summary_label", default="Tóm tắt: {summary}", summary=_compact_lines(summary, limit=6000)))
        page_text = _compact_lines(content or page.text or page.description or "", limit=12000)
        if page_text:
            context_parts.append(f"Nội dung: {page_text}")

        try:
            self.memory_repo.write(
                chat_id=chat_id,
                content="\n".join(context_parts).strip(),
                memory_type="url_context",
                title=title,
                tags=[
                    "web",
                    "url_context",
                    tool,
                    page.canonical_url or page.final_url or page.url,
                ],
                importance=4,
                source_text=page_text or summary or instruction or title,
            )
        except Exception:
            pass

    def _load_url_context_rows(self, *, chat_id: str, query: str, limit: int = 4) -> list[dict[str, Any]]:
        if not self.memory_repo or not chat_id.strip():
            return []
        rows = self.memory_repo.search(
            chat_id=chat_id,
            query=query or t("skills.url_followup_fallback", default="hỏi tiếp link này"),
            limit=max(1, min(limit, 8)),
            memory_type="url_context",
        )
        if rows:
            return rows
        recent_rows = self.memory_repo.recent(chat_id=chat_id, limit=max(1, min(limit, 8)))
        return [row for row in recent_rows if str(row.get("memory_type") or "").strip() == "url_context"]

    def _answer_from_url_context(
        self,
        *,
        question: str,
        title: str,
        url: str,
        description: str,
        content: str,
        scope: str,
    ) -> tuple[str, dict[str, Any]]:
        question_text = str(question or "").strip()
        if not question_text:
            question_text = "Hãy tóm tắt và nêu điểm đáng chú ý của link này."
        deep = any(
            cue in " ".join(question_text.lower().split())
            for cue in (
                "phân tích sâu",
                "phan tich sau",
                "chi tiết hơn",
                "chi tiet hon",
                "kỹ hơn",
                "ky hon",
                "đầy đủ hơn",
                "day du hon",
                "longer",
                "deeper",
            )
        )
        cleaned = _compact_lines(content, limit=18000)
        if not cleaned:
            cleaned = description or title or url
        model_scope = f"{scope}:{'deep' if deep else 'default'}"
        primary, fallback = self._get_summary_model(model_scope)
        prompt = t(
            "skills.web_ask_prompt",
            default=(
                f"URL: {url or 'không rõ'}\n"
                f"Tiêu đề: {title or 'không rõ'}\n"
                f"Mô tả trang: {description or 'không có'}\n\n"
                f"Ngữ cảnh trích xuất:\n{cleaned}\n\n"
                f"Câu hỏi của người dùng:\n{question_text}"
            ),
            url=url or t("skills.unknown", default="không rõ"),
            title=title or t("skills.unknown", default="không rõ"),
            description=description or t("skills.none", default="không có"),
            context=cleaned,
            question=question_text,
        )
        system_prompt = t(
            "skills.web_ask_system",
            default=(
                "Bạn là trợ lý hỏi đáp trang web. Trả lời bằng tiếng Việt tự nhiên, rõ ý, "
                "ưu tiên thông tin hữu ích, trình bày dễ đọc trên Telegram, và không dùng markdown."
            ),
        )
        human_message = HumanMessage(content=prompt)
        result = None
        provider_used = "primary"
        try:
            result = primary.invoke([SystemMessage(content=system_prompt), human_message])
        except Exception as primary_exc:
            if fallback is None:
                raise
            try:
                result = fallback.invoke([SystemMessage(content=system_prompt), human_message])
                provider_used = "fallback"
            except Exception:
                raise primary_exc
        answer_text = sanitize_final_text(str(getattr(result, "content", "") or ""))
        if not answer_text:
            answer_text = _compact_lines(cleaned, limit=4000)
        trace = self._trace(result, scope=scope, provider_used=provider_used)
        trace["provider"] = provider_used
        return answer_text, trace

    def _fetch_page(self, url: str, fetch_strategy: str = "auto") -> WebPage:
        source_url = str(url or "").strip()
        if not source_url:
            raise ValueError("URL is required.")
        _validate_public_url(source_url)

        strategy = _normalize_fetch_strategy(fetch_strategy)

        referer = self.settings.openrouter_referer
        parsed_ref = urlparse(referer)
        domain = parsed_ref.netloc or "n8n.example.com"
        headers = {
            "User-Agent": f"Mozilla/5.0 (compatible; MiaWeb/1.0; +https://{domain})",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
        }
        with httpx.Client(
            follow_redirects=False,
            timeout=self.settings.request_timeout_seconds,
            headers=headers,
        ) as client:
            current_url = source_url
            max_redirects = max(0, int(self.settings.web_max_redirects))
            for redirect_count in range(max_redirects + 1):
                _validate_public_url(current_url)
                with client.stream("GET", current_url) as streamed:
                    if streamed.status_code in {301, 302, 303, 307, 308}:
                        location = str(streamed.headers.get("location") or "").strip()
                        if not location:
                            streamed.raise_for_status()
                        if redirect_count >= max_redirects:
                            raise ValueError("URL exceeded the redirect limit.")
                        current_url = urljoin(current_url, location)
                        continue
                    streamed.raise_for_status()
                    content_length = int(streamed.headers.get("content-length") or 0)
                    max_bytes = max(1024, int(self.settings.web_max_response_bytes))
                    if content_length and content_length > max_bytes:
                        raise ValueError("Web response is larger than the configured limit.")
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in streamed.iter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError("Web response is larger than the configured limit.")
                        chunks.append(chunk)
                    response = httpx.Response(
                        status_code=streamed.status_code,
                        headers=streamed.headers,
                        content=b"".join(chunks),
                        request=streamed.request,
                    )
                    _validate_public_url(str(response.url))
                    return _parse_page(response, source_url, fetch_strategy=strategy)
            raise ValueError("URL could not be fetched safely.")

    def _format_read_result(self, page: WebPage, *, max_chars: int = 12000) -> tuple[str, list[str]]:
        content = page.text or page.description or ""
        warnings: list[str] = []
        if page.fetch_strategy == "rendered":
            warnings.append(
                t(
                    "skills.web_rendered_fallback",
                    default="Mia chưa có browser renderer riêng, nên chế độ rendered đang fallback sang fetch tĩnh và trích xuất nội dung công khai.",
                )
            )
        if _looks_blocked(page):
            warnings.append(
                t(
                    "skills.web_possible_block",
                    default="Trang này có dấu hiệu chặn truy cập tự động hoặc yêu cầu đăng nhập.",
                )
            )
        if not content:
            warnings.append(t("skills.web_no_text", default="Không trích xuất được nội dung chữ đáng kể từ trang này."))
        visible = _compact_lines(content, limit=max(3000, min(max_chars or 12000, 20000)))
        if len(content) > len(visible):
            warnings.append(t("skills.web_text_shortened", default="Nội dung đã được rút gọn để dễ đọc."))
        unknown_str = t("skills.unknown", default="không rõ")
        lines = [
            t("skills.title_label", default="Tiêu đề: {title}", title=page.title or unknown_str),
            t("skills.result_label", default="Result: {text}", text=page.canonical_url or page.final_url or page.url),
        ]
        if page.description:
            lines.append(t("skills.extra_details_label", default="Chi tiết bổ sung: {text}", text=page.description))
        if visible:
            lines.extend([t("skills.content_label", default="Nội dung: {content}", content="").replace(": ", ":"), visible])
        elif page.links:
            lines.append(t("skills.web_links_only", default="Trang này chủ yếu có liên kết, chưa có nhiều văn bản để trích xuất."))
        return "\n".join(lines).strip(), warnings

    def _summarize_text(
        self,
        *,
        title: str,
        url: str,
        description: str,
        content: str,
        instruction: str,
        scope: str,
    ) -> tuple[str, dict[str, Any]]:
        deep = any(
            cue in " ".join(str(instruction or "").lower().split())
            for cue in (
                "phân tích sâu",
                "phan tich sau",
                "chi tiết hơn",
                "chi tiet hon",
                "kỹ hơn",
                "ky hon",
                "nhiều ý",
                "nhieu y",
                "đầy đủ hơn",
                "day du hon",
                "longer",
                "deeper",
            )
        )
        cleaned = _compact_lines(content, limit=18000)
        if not cleaned:
            cleaned = description or title or url
        model_scope = f"{scope}:{'deep' if deep else 'default'}"
        primary, fallback = self._get_summary_model(model_scope)
        prompt = t(
            "skills.web_summarize_prompt",
            default=(
                f"URL: {url}\n"
                f"Tiêu đề: {title or 'không rõ'}\n"
                f"Mô tả trang: {description or 'không có'}\n\n"
                f"Nội dung trích xuất:\n{cleaned}\n\n"
                f"Yêu cầu bổ sung từ người dùng:\n{instruction or 'tóm tắt link này'}"
            ),
            url=url,
            title=title or t("skills.unknown", default="không rõ"),
            description=description or t("skills.none", default="không có"),
            content=cleaned,
            instruction=instruction or t("skills.web_scrape_fallback", default="tóm tắt link này"),
        )
        system_prompt = t(
            "skills.web_summarize_system",
            default=(
                "Bạn là trợ lý tóm tắt trang web. Trả lời bằng tiếng Việt tự nhiên, rõ ý, "
                "ưu tiên thông tin hữu ích, trình bày dễ đọc trên Telegram, và không dùng markdown."
            ),
        )
        human_message = HumanMessage(content=prompt)
        result = None
        provider_used = "primary"
        try:
            result = primary.invoke([SystemMessage(content=system_prompt), human_message])
        except Exception as primary_exc:
            if fallback is None:
                raise
            try:
                result = fallback.invoke([SystemMessage(content=system_prompt), human_message])
                provider_used = "fallback"
            except Exception:
                raise primary_exc
        summary_text = sanitize_final_text(str(getattr(result, "content", "") or ""))
        if not summary_text:
            summary_text = _compact_lines(cleaned, limit=4000)
        trace = self._trace(result, scope=scope, provider_used=provider_used)
        trace["provider"] = provider_used
        return summary_text, trace

    def read_url(self, *, url: str, instruction: str = "", request_id: str = "", chat_id: str = "", fetch_strategy: str = "auto", max_chars: int = 0) -> WebResult:
        page = self._fetch_page(url, fetch_strategy=fetch_strategy)
        text, warnings = self._format_read_result(page, max_chars=max_chars or 12000)
        self._store_url_context(
            chat_id=chat_id,
            tool="read_url",
            page=page,
            instruction=instruction,
            content=page.text or page.description or "",
        )
        return WebResult(
            tool="read_url",
            url=page.url,
            final_url=page.final_url,
            title=page.title,
            canonical_url=page.canonical_url,
            text=text,
            data={
                "url": page.url,
                "final_url": page.final_url,
                "title": page.title,
                "canonical_url": page.canonical_url,
                "description": page.description,
                "text": page.text,
                "links": page.links,
                "mime_type": page.mime_type,
                "status_code": page.status_code,
                "fetch_strategy": page.fetch_strategy,
                "instruction": instruction,
                "request_id": request_id,
                "chat_id": chat_id,
            },
            warnings=warnings,
            trace={},
        )

    def summarize_url(self, *, url: str, instruction: str = "", request_id: str = "", chat_id: str = "", fetch_strategy: str = "auto", max_chars: int = 0) -> WebResult:
        page = self._fetch_page(url, fetch_strategy=fetch_strategy)
        read_text, warnings = self._format_read_result(page, max_chars=max_chars or 12000)
        summary_text, trace = self._summarize_text(
            title=page.title,
            url=page.canonical_url or page.final_url or page.url,
            description=page.description,
            content=page.text or page.description or "",
            instruction=instruction,
            scope="web:summary",
        )
        final_text = summary_text
        summary_title = t("skills.web_summary_title", default="Tóm tắt {title}", title=page.title)
        if page.title and page.title.lower() not in final_text.lower():
            final_text = f"{summary_title}\n{final_text}".strip()
        followup_hint = t("skills.web_followup_hint", default="Nếu muốn, anh có thể hỏi tiếp ngay trên link này.")
        if followup_hint.lower() not in final_text.lower():
            final_text = f"{final_text}\n\n{followup_hint}".strip()
        shortened_warning = t("skills.web_text_shortened", default="Nội dung đã được rút gọn để dễ đọc.")
        if warnings and shortened_warning not in warnings and read_text:
            warnings.append(shortened_warning)
        self._store_url_context(
            chat_id=chat_id,
            tool="summarize_url",
            page=page,
            instruction=instruction,
            summary=summary_text,
            content=page.text or page.description or "",
        )
        return WebResult(
            tool="summarize_url",
            url=page.url,
            final_url=page.final_url,
            title=page.title,
            canonical_url=page.canonical_url,
            text=final_text,
            data={
                "url": page.url,
                "final_url": page.final_url,
                "title": page.title,
                "canonical_url": page.canonical_url,
                "description": page.description,
                "content": page.text,
                "links": page.links,
                "summary": summary_text,
                "fetch_strategy": page.fetch_strategy,
                "instruction": instruction,
                "request_id": request_id,
                "chat_id": chat_id,
            },
            warnings=warnings,
            trace={"llm": trace},
        )

    def ask_url(self, *, url: str, instruction: str = "", request_id: str = "", chat_id: str = "", fetch_strategy: str = "auto", max_chars: int = 0) -> WebResult:
        question = str(instruction or "").strip()
        warnings: list[str] = []
        page: WebPage | None = None
        title = ""
        canonical_url = ""
        description = ""
        content = ""
        context_mode = "memory"

        if url.strip():
            page = self._fetch_page(url, fetch_strategy=fetch_strategy)
            title = page.title
            canonical_url = page.canonical_url or page.final_url or page.url
            description = page.description
            content = page.text or page.description or ""
            context_mode = "url"
        else:
            rows = self._load_url_context_rows(chat_id=chat_id, query=question, limit=4)
            if not rows:
                message = t("skills.web_no_recent_links", default="Mia chưa có link gần đây để hỏi tiếp. Anh gửi lại link hoặc nói rõ link nào nhé.")
                return WebResult(
                    tool="ask_url",
                    url="",
                    final_url="",
                    title="",
                    canonical_url="",
                    text=message,
                    data={
                        "question": question,
                        "context_mode": "missing",
                        "request_id": request_id,
                        "chat_id": chat_id,
                    },
                    warnings=[t("skills.web_no_recent_links_warning", default="Không tìm thấy ngữ cảnh link gần đây.")],
                    trace={},
                )

            context_lines: list[str] = []
            for row in rows[:4]:
                row_title = str(row.get("title") or "").strip()
                chunk_text = str(row.get("chunk_text") or "").strip()
                tags = row.get("tags") or []
                if row_title and not title:
                    title = row_title
                if chunk_text:
                    context_label = t("skills.unknown", default="Ngữ cảnh") if not row_title else row_title
                    context_lines.append(f"{context_label}: {chunk_text}")
                    if not canonical_url:
                        canonical_url = _extract_first_url(chunk_text)
                if not canonical_url and isinstance(tags, list):
                    for tag in tags:
                        found = _extract_first_url(str(tag))
                        if found:
                            canonical_url = found
                            break
            content = "\n\n".join(context_lines).strip()

        answer_text, trace = self._answer_from_url_context(
            question=question,
            title=title,
            url=canonical_url or (page.canonical_url if page else ""),
            description=description,
            content=content,
            scope="web:ask",
        )
        if page is not None:
            self._store_url_context(
                chat_id=chat_id,
                tool="ask_url",
                page=page,
                instruction=question,
                content=page.text or page.description or "",
            )
        return WebResult(
            tool="ask_url",
            url=url.strip() or canonical_url or (page.url if page else ""),
            final_url=page.final_url if page else canonical_url,
            title=title or (page.title if page else ""),
            canonical_url=canonical_url or (page.canonical_url if page else ""),
            text=answer_text,
            data={
                "question": question,
                "context_mode": context_mode,
                "title": title or (page.title if page else ""),
                "canonical_url": canonical_url or (page.canonical_url if page else ""),
                "fetch_strategy": page.fetch_strategy if page else _normalize_fetch_strategy(fetch_strategy),
                "request_id": request_id,
                "chat_id": chat_id,
            },
            warnings=warnings,
            trace={"llm": trace},
        )
