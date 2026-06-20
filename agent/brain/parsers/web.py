from __future__ import annotations

import re

from agent.brain.parsers.common import (
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    strip_prefixes,
)

NEWS_TOPIC_PREFIXES = (
    "tin tuc",
    "tin tức",
    "news",
    "doc bao",
    "đọc báo",
    "bao hom nay",
    "báo hôm nay",
)

NEWS_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kinh-doanh": (
        "kinh doanh",
        "kinh te",
        "tai chinh",
        "chung khoan",
        "doanh nghiep",
        "business",
        "finance",
        "stocks",
        "thit truong",
    ),
    "the-gioi": (
        "the gioi",
        "quoc te",
        "international",
        "world",
        "global",
        "my",
        "my trung",
    ),
    "so-hoa": (
        "so hoa",
        "cong nghe",
        "technology",
        "tech",
        "ai",
        "robot",
        "internet",
        "game",
        "gaming",
        "nintendo",
        "playstation",
        "xbox",
        "apple",
        "iphone",
        "android",
        "samsung",
        "meta",
        "openai",
    ),
    "thoi-su": (
        "thoi su",
        "xa hoi",
        "chinh tri",
        "politics",
        "news",
        "su kien",
    ),
    "suc-khoe": (
        "suc khoe",
        "health",
        "y te",
        "benh",
        "dich benh",
    ),
    "the-thao": (
        "the thao",
        "sport",
        "bong da",
        "tennis",
        "basketball",
        "football",
    ),
    "giai-tri": (
        "giai tri",
        "entertainment",
        "am nhac",
        "phim anh",
        "showbiz",
    ),
    "phap-luat": (
        "phap luat",
        "law",
        "luat",
        "toa an",
    ),
    "giao-duc": (
        "giao duc",
        "education",
        "truong hoc",
        "hoc sinh",
        "sinh vien",
    ),
    "doi-song": (
        "doi song",
        "life",
        "gia dinh",
        "phong cach song",
    ),
    "xe": (
        "xe",
        "oto",
        "o to",
        "xe may",
        "car",
        "motor",
    ),
    "du-lich": (
        "du lich",
        "travel",
        "tour",
        "holiday",
    ),
    "khoa-hoc": (
        "khoa hoc",
        "science",
        "research",
    ),
}

URL_READ_CUES = (
    "doc link",
    "đọc link",
    "mo link",
    "mở link",
    "xem link",
    "open link",
    "read link",
    "vao link",
    "vào link",
)

URL_ASK_CUES = (
    "hoi tiep",
    "hỏi tiếp",
    "hoi them",
    "hỏi thêm",
    "trong link nay",
    "trong link này",
    "trong bai nay",
    "trong bài này",
    "link nay noi gi",
    "link này nói gì",
    "bai nay noi gi",
    "bài này nói gì",
    "trang nay noi gi",
    "trang này nói gì",
    "link nay co nhac gi",
    "link này có nhắc gì",
    "bai nay co nhac gi",
    "bài này có nhắc gì",
    "noi ve gi",
    "nói về gì",
    "phan nao",
    "phần nào",
)

URL_SUMMARY_CUES = (
    "tom tat link",
    "tóm tắt link",
    "phan tich link",
    "phân tích link",
    "summary link",
    "summarize link",
    "noi dung link",
    "nội dung link",
    "giai thich link",
    "giải thích link",
)


def extract_news_topic(text: str) -> str:
    topic = strip_prefixes(text, NEWS_TOPIC_PREFIXES)
    topic = re.sub(
        r"^(ve|về|cua|của|cho|theo|chu de|chủ đề)\s+",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    topic = re.sub(
        r"^(hom nay|hôm nay|moi nhat|mới nhất|moi|mới)(?:\s+|$)",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    return " ".join(topic.split()).strip()


def news_topic_to_feed_slug(topic: str) -> str:
    normalized = normalize_query_text(topic)
    if not normalized:
        return ""
    for feed_slug, keywords in NEWS_TOPIC_KEYWORDS.items():
        if any_keyword_matches(normalized, keywords):
            return feed_slug
    return ""


def looks_like_news_request(text: str) -> bool:
    normalized = normalize_query_text(text)
    if not normalized:
        return False

    explicit_cues = (
        "tin tuc",
        "tin tức",
        "doc bao",
        "đọc báo",
        "bao hom nay",
        "báo hôm nay",
        "bao moi",
        "báo mới",
        "tin moi",
        "tin mới",
        "news",
    )
    if any(keyword_matches(normalized, cue) for cue in explicit_cues):
        return True

    topic_keywords = tuple(keyword for keywords in NEWS_TOPIC_KEYWORDS.values() for keyword in keywords)
    if re.search(r"(?<!thong )\btin\b", normalized) and any(keyword_matches(normalized, keyword) for keyword in topic_keywords):
        return True
    if re.search(r"\bbao\b", normalized) and any(keyword_matches(normalized, keyword) for keyword in topic_keywords):
        return True
    return False


def extract_shortlink_parts(text: str) -> tuple[str, str]:
    match = re.search(r"https?://[^\s<>\"']+", text or "", flags=re.IGNORECASE)
    if not match:
        return "", ""
    url = match.group(0).rstrip("),.;!?")
    ttl = " ".join((text or "").replace(url, " ").split()).strip()
    ttl = strip_prefixes(ttl, ("rut gon link", "tao link ngan", "shortlink", "short link"))
    return url, ttl


def extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s<>\"')\]]+", text or "", flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(0).rstrip("),.;!?")
