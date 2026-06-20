from __future__ import annotations

import re
from typing import Any

from langchain.messages import AIMessage, HumanMessage, ToolMessage

from agent.brain.parsers.common import normalize_query_text
from agent.i18n import t


def coerce_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item["text"]))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "")


def sanitize_final_text(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1: \2", cleaned)
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"(?m)^\s*[-*]\s+", "- ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned
    return t("error.fallback_response")


def current_turn_messages(messages: list[Any]) -> list[Any]:
    last_human_index = -1
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            last_human_index = index
    if last_human_index == -1:
        return messages
    return messages[last_human_index:]


def extract_tools_called(messages: list[Any]) -> list[str]:
    calls: list[str] = []
    for message in current_turn_messages(messages):
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for item in tool_calls:
            name = str(item.get("name") or "").strip()
            if name and name not in calls:
                calls.append(name)
    return calls


def extract_urls(text: str) -> list[str]:
    seen: list[str] = []
    for url in re.findall(r"https?://[^\s)>\]]+", text or ""):
        cleaned = url.rstrip(".,;")
        if cleaned not in seen:
            seen.append(cleaned)
    return seen


def cap_visible_links(text: str, limit: int = 3) -> str:
    urls = extract_urls(text)
    if len(urls) <= limit:
        return text

    extra_urls = set(urls[limit:])
    kept_lines: list[str] = []
    for line in str(text or "").splitlines():
        line_urls = extract_urls(line)
        if line_urls and all(url in extra_urls for url in line_urls):
            continue
        for url in line_urls:
            if url in extra_urls:
                line = line.replace(url, "").rstrip(" .:-")
        kept_lines.append(line.rstrip())

    cleaned = "\n".join(kept_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or text


def looks_like_not_found(text: str) -> bool:
    normalized = normalize_query_text(text)
    cues = (
        "khong tim thay",
        "khong thay",
        "chua tim thay",
        "khong co ket qua",
        "khong co thong tin",
        "not found",
        "no result",
        "no information",
        "cannot find",
        "could not find",
    )
    return any(cue in normalized for cue in cues)


def tool_messages_by_name(messages: list[Any], tool_name: str) -> list[str]:
    texts: list[str] = []
    current_tool_name = ""
    for message in current_turn_messages(messages):
        if isinstance(message, AIMessage):
            tool_calls = getattr(message, "tool_calls", None) or []
            if tool_calls:
                current_tool_name = str(tool_calls[-1].get("name") or "").strip()
        elif isinstance(message, ToolMessage):
            if current_tool_name == tool_name:
                text = coerce_message_text(message.content).strip()
                if text:
                    texts.append(text)
    return texts


def all_tool_messages(messages: list[Any]) -> list[str]:
    texts: list[str] = []
    for message in current_turn_messages(messages):
        if isinstance(message, ToolMessage):
            text = coerce_message_text(message.content).strip()
            if text:
                texts.append(text)
    return texts


def resolve_fallback_text(messages: list[Any]) -> str:
    for message in reversed(current_turn_messages(messages)):
        if isinstance(message, AIMessage):
            text = sanitize_final_text(coerce_message_text(message.content))
            if text and t("error.fallback_response") not in text:
                return text
        if isinstance(message, ToolMessage):
            text = coerce_message_text(message.content).strip()
            if text:
                return text
    return t("error.fallback_response")


def prefer_tool_truth(final_text: str, messages: list[Any], tools_called: list[str]) -> str:
    if not looks_like_not_found(final_text):
        return final_text

    url_tools = {
        "docs_search_doc",
        "drive_search_file",
        "drive_list_files",
        "search_web",
        "read_url",
        "summarize_url",
        "ask_url",
        "news_get",
        "gmail_list_inbox",
    }
    if not any(tool in url_tools for tool in tools_called):
        return final_text

    for tool_text in all_tool_messages(messages):
        if extract_urls(tool_text):
            return sanitize_final_text(tool_text)
    return final_text


def prefer_docs_search_output(request_text: str, final_text: str, messages: list[Any], tools_called: list[str]) -> str:
    if "docs_search_doc" not in tools_called:
        return final_text

    normalized = normalize_query_text(request_text)
    search_cues = ("tim doc", "search doc", "tim tai lieu", "doc project", "tai lieu")
    if not any(cue in normalized for cue in search_cues):
        return final_text

    for tool_text in tool_messages_by_name(messages, "docs_search_doc"):
        if extract_urls(tool_text):
            return sanitize_final_text(tool_text)
    return final_text


def ensure_tool_links(
    final_text: str,
    messages: list[Any],
    tools_called: list[str],
    *,
    tool_name: str,
    label: str,
    limit: int = 3,
) -> str:
    if tool_name not in tools_called:
        return final_text
    if extract_urls(final_text):
        return final_text

    urls: list[str] = []
    for tool_text in tool_messages_by_name(messages, tool_name):
        for url in extract_urls(tool_text):
            if url not in urls:
                urls.append(url)

    if not urls:
        return final_text

    lines = [final_text.rstrip(), "", label]
    for index, url in enumerate(urls[:limit], start=1):
        lines.append(f"{index}. {url}")
    return "\n".join(lines).strip()
