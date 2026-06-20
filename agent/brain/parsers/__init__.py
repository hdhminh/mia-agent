from __future__ import annotations

from agent.brain.parsers.common import (
    RequestProfile,
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    looks_multi_step,
    is_soft_followup_only,
    strip_prefixes,
    strip_conversational_fillers,
)
from agent.brain.parsers.google import (
    extract_sheet_range,
    _calendar_range_from_text,
)
from agent.brain.parsers.github import (
    extract_github_repo_context,
)
from agent.brain.parsers.web import (
    extract_news_topic,
    news_topic_to_feed_slug,
    looks_like_news_request,
    extract_shortlink_parts,
    extract_first_url,
)
