from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agent.i18n import t


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_json(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _first_non_empty(*values: str) -> str:
    for value in values:
        text = _normalize_text(value)
        if text:
            return text
    return ""


CONFIRMATION_CUES = (
    "xác nhận",
    "xac nhan",
    "đồng ý",
    "dong y",
    "ok",
    "okay",
    "tiếp tục",
    "tiep tuc",
    "làm đi",
    "lam di",
    "chạy đi",
    "chay di",
    "confirm",
    "yes",
    "go ahead",
)

CANCELLATION_CUES = (
    "hủy",
    "huy",
    "cancel",
    "thôi",
    "thoi",
    "không làm",
    "khong lam",
    "đừng làm",
    "dung lam",
)

NEGATION_CUES = ("không", "khong", "chưa", "chua", "đừng", "dung", "not ", "do not")

DANGEROUS_GATEWAY_NAMES = {
    "calendar.create_event",
    "calendar.reschedule_event",
    "calendar.delete_event",
    "gmail.send_email",
    "gmail.draft_email",
    "gmail.reply_email",
    "gmail.mark_read",
    "gmail.archive",
    "drive.create_folder",
    "drive.create_file",
    "drive.upload_file",
    "drive.copy_file",
    "drive.move_file",
    "drive.rename_file",
    "drive.delete_file",
    "drive.delete_folder",
    "drive.share_file",
    "docs.create_doc",
    "docs.append_doc",
    "docs.update_doc",
    "docs.delete_doc",
    "sheets.create_sheet",
    "sheets.append_row",
    "sheets.update_cell",
    "sheets.update_range",
    "sheets.delete_sheet",
    "shortlink.create",
    "tasks.create",
    "tasks.update",
    "tasks.complete",
    "tasks.delete",
    "automation.create",
    "automation.pause",
    "automation.resume",
    "automation.delete",
    "automation.run_now",
    "github.create_issue",
    "github.update_issue",
    "github.comment_issue",
    "github.create_branch",
    "github.update_file",
    "github.create_pull_request",
    "github.comment_pull_request",
    "github.rerun_failed_workflow",
    "code.apply_to_local",
    "code.create_pull_request",
    "code.apply_to_existing_project",
    "code.publish_project",
    "code.fix_from_issue",
}


def is_confirmation_text(text: str) -> bool:
    normalized = _normalize_text(text).lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE).strip()
    if not normalized:
        return False
    if any(cue in normalized for cue in NEGATION_CUES):
        return False
    accepted = {re.sub(r"[^\w\s-]", "", cue.lower(), flags=re.UNICODE) for cue in CONFIRMATION_CUES}
    if normalized in accepted:
        return True
    return bool(re.fullmatch(r"(?:xác nhận|xac nhan|confirm)\s+(?:#?\d+)", normalized))


def is_cancellation_text(text: str) -> bool:
    normalized = _normalize_text(text).lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE).strip()
    return normalized in {
        re.sub(r"[^\w\s-]", "", cue.lower(), flags=re.UNICODE)
        for cue in CANCELLATION_CUES
    }


def should_require_confirmation(gateway_name: str, args: dict[str, Any] | None = None, request_text: str = "") -> bool:
    gateway = _normalize_text(gateway_name)
    if gateway not in DANGEROUS_GATEWAY_NAMES:
        return False
    return True


def _summarize_gateway_action(gateway_name: str, args: dict[str, Any] | None = None) -> str:
    payload = _normalize_json(args or {})
    gateway = _normalize_text(gateway_name)
    if gateway == "gmail.send_email":
        to = _first_non_empty(payload.get("to"), payload.get("toEmail"))
        subject = _first_non_empty(payload.get("subject"))
        parts = [t("approval.action.gmail_send", default="gửi email")]
        if to:
            parts.append(t("approval.action.gmail_send_to", default=f"tới {to}", to=to))
        if subject:
            parts.append(t("approval.action.gmail_send_subject", default=f"tiêu đề {subject}", subject=subject))
        return " ".join(parts)
    if gateway == "gmail.reply_email":
        target = _first_non_empty(payload.get("messageId"), payload.get("searchQuery"))
        return t("approval.action.gmail_reply", default=f"trả lời email {target}", target=target).strip()
    if gateway == "calendar.create_event":
        title = _first_non_empty(payload.get("title"), payload.get("summary"))
        start_at = _first_non_empty(payload.get("startAt"), payload.get("start_at"))
        end_at = _first_non_empty(payload.get("endAt"), payload.get("end_at"))
        parts = [t("approval.action.calendar_create", default="tạo lịch")]
        if title:
            parts.append(t("approval.action.calendar_create_title", default=f"'{title}'", title=title))
        if start_at or end_at:
            parts.append(t("approval.action.calendar_create_time", default=f"từ {start_at or '?'} đến {end_at or '?'}", start=start_at or '?', end=end_at or '?'))
        return " ".join(parts)
    if gateway == "calendar.reschedule_event":
        target = _first_non_empty(payload.get("eventId"), payload.get("query"))
        start_at = _first_non_empty(payload.get("startAt"), payload.get("start_at"))
        end_at = _first_non_empty(payload.get("endAt"), payload.get("end_at"))
        parts = [t("approval.action.calendar_reschedule", default="dời lịch")]
        if target:
            parts.append(target)
        if start_at or end_at:
            parts.append(t("approval.action.calendar_reschedule_time", default=f"sang {start_at or '?'} - {end_at or '?'}", start=start_at or '?', end=end_at or '?'))
        return " ".join(parts)
    if gateway == "calendar.delete_event":
        target = _first_non_empty(payload.get("eventId"), payload.get("query"))
        return t("approval.action.calendar_delete", default=f"xóa lịch {target}", target=target).strip()
    if gateway == "drive.move_file":
        file_name = _first_non_empty(payload.get("fileName"), payload.get("file_id"), payload.get("fileId"))
        target = _first_non_empty(payload.get("targetFolderName"), payload.get("target_folder_name"), payload.get("targetFolderId"))
        parts = [t("approval.action.drive_move", default="di chuyển file")]
        if file_name:
            parts.append(file_name)
        if target:
            parts.append(t("approval.action.drive_move_to", default=f"sang {target}", target=target))
        return " ".join(parts)
    if gateway == "drive.rename_file":
        file_name = _first_non_empty(payload.get("fileName"), payload.get("fileId"))
        new_name = _first_non_empty(payload.get("newName"), payload.get("new_name"))
        parts = [t("approval.action.drive_rename", default="đổi tên file")]
        if file_name:
            parts.append(file_name)
        if new_name:
            parts.append(t("approval.action.drive_rename_to", default=f"thành {new_name}", new_name=new_name))
        return " ".join(parts)
    if gateway == "drive.delete_file":
        file_name = _first_non_empty(payload.get("fileName"), payload.get("fileId"))
        return t("approval.action.drive_delete_file", default=f"xóa file {file_name}", file_name=file_name).strip()
    if gateway == "drive.delete_folder":
        file_name = _first_non_empty(payload.get("fileName"), payload.get("folderName"), payload.get("fileId"))
        return t("approval.action.drive_delete_folder", default=f"xóa folder {file_name}", file_name=file_name).strip()
    if gateway == "drive.share_file":
        file_name = _first_non_empty(payload.get("fileName"), payload.get("fileId"))
        email = _first_non_empty(payload.get("email"))
        role = _first_non_empty(payload.get("role"))
        parts = [t("approval.action.drive_share", default="chia sẻ file")]
        if file_name:
            parts.append(file_name)
        if email:
            parts.append(t("approval.action.drive_share_to", default=f"cho {email}", email=email))
        if role:
            parts.append(t("approval.action.drive_share_role", default=f"quyền {role}", role=role))
        return " ".join(parts)
    if gateway == "docs.create_doc":
        title = _first_non_empty(payload.get("title"), payload.get("docName"))
        return t("approval.action.docs_create", default=f"tạo doc {title}", title=title).strip()
    if gateway == "docs.append_doc":
        title = _first_non_empty(payload.get("docName"), payload.get("documentId"))
        return t("approval.action.docs_append", default=f"thêm nội dung vào doc {title}", title=title).strip()
    if gateway == "docs.update_doc":
        title = _first_non_empty(payload.get("docName"), payload.get("documentId"))
        return t("approval.action.docs_update", default=f"cập nhật doc {title}", title=title).strip()
    if gateway == "docs.delete_doc":
        title = _first_non_empty(payload.get("docName"), payload.get("documentId"))
        return t("approval.action.docs_delete", default=f"xóa doc {title}", title=title).strip()
    if gateway == "sheets.create_sheet":
        title = _first_non_empty(payload.get("title"), payload.get("sheetName"))
        return t("approval.action.sheets_create", default=f"tạo sheet {title}", title=title).strip()
    if gateway == "sheets.append_row":
        title = _first_non_empty(payload.get("sheetName"), payload.get("spreadsheetId"))
        return t("approval.action.sheets_append", default=f"thêm dòng vào sheet {title}", title=title).strip()
    if gateway == "sheets.update_cell":
        sheet = _first_non_empty(payload.get("sheetName"), payload.get("spreadsheetId"))
        cell = _first_non_empty(payload.get("cell"))
        return t("approval.action.sheets_update_cell", default=f"cập nhật ô {cell} của sheet {sheet}", cell=cell, sheet=sheet).strip()
    if gateway == "sheets.update_range":
        sheet = _first_non_empty(payload.get("sheetName"), payload.get("spreadsheetId"))
        range_name = _first_non_empty(payload.get("rangeName"), payload.get("range"))
        return t("approval.action.sheets_update_range", default=f"cập nhật vùng {range_name} của sheet {sheet}", range_name=range_name, sheet=sheet).strip()
    if gateway == "sheets.delete_sheet":
        title = _first_non_empty(payload.get("sheetName"), payload.get("spreadsheetId"))
        return t("approval.action.sheets_delete", default=f"xóa sheet {title}", title=title).strip()
    if gateway == "github.create_issue":
        repo = _first_non_empty(payload.get("repo"))
        title = _first_non_empty(payload.get("title"))
        parts = [t("approval.action.github_create_issue", default="tạo issue GitHub")]
        if repo:
            parts.append(repo)
        if title:
            parts.append(t("approval.action.github_title", default=f"tiêu đề {title}", title=title))
        return " ".join(parts)
    if gateway == "github.update_issue":
        repo = _first_non_empty(payload.get("repo"))
        number = _first_non_empty(payload.get("number"))
        state = _first_non_empty(payload.get("state"))
        parts = [t("approval.action.github_update_issue", default="cập nhật issue GitHub")]
        if repo:
            parts.append(repo)
        if number:
            parts.append(f"#{number}")
        if state:
            parts.append(t("approval.action.github_state", default=f"trạng thái {state}", state=state))
        return " ".join(parts)
    if gateway == "github.comment_issue":
        repo = _first_non_empty(payload.get("repo"))
        number = _first_non_empty(payload.get("number"))
        return t("approval.action.github_comment_issue", default=f"bình luận issue #{number} ở {repo}", number=number, repo=repo).strip()
    if gateway == "github.create_branch":
        repo = _first_non_empty(payload.get("repo"))
        branch = _first_non_empty(payload.get("branch"))
        return t("approval.action.github_create_branch", default=f"tạo branch {branch} ở {repo}", branch=branch, repo=repo).strip()
    if gateway == "github.update_file":
        repo = _first_non_empty(payload.get("repo"))
        path = _first_non_empty(payload.get("path"))
        branch = _first_non_empty(payload.get("branch"))
        return t("approval.action.github_update_file", default=f"cập nhật file {path} ở {repo} trên branch {branch}", path=path, repo=repo, branch=branch).strip()
    if gateway == "github.create_pull_request":
        repo = _first_non_empty(payload.get("repo"))
        title = _first_non_empty(payload.get("title"))
        head = _first_non_empty(payload.get("head"))
        base = _first_non_empty(payload.get("base"))
        return t("approval.action.github_create_pr", default=f"tạo pull request {title} từ {head} sang {base} ở {repo}", title=title, head=head, base=base, repo=repo).strip()
    if gateway == "github.comment_pull_request":
        repo = _first_non_empty(payload.get("repo"))
        number = _first_non_empty(payload.get("number"))
        return t("approval.action.github_comment_pr", default=f"bình luận pull request #{number} ở {repo}", number=number, repo=repo).strip()
    if gateway == "github.rerun_failed_workflow":
        repo = _first_non_empty(payload.get("repo"))
        run_id = _first_non_empty(payload.get("runId"), payload.get("run_id"))
        return t("approval.action.github_rerun_workflow", default=f"rerun workflow run {run_id} ở {repo}", run_id=run_id, repo=repo).strip()
    return gateway or t("approval.action.fallback", default="thao tác này")


@dataclass(frozen=True)
class PendingAction:
    id: int
    chat_id: str
    user_id: str
    request_id: str
    tool_name: str
    gateway_name: str
    args: dict[str, Any]
    summary: str
    reason: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    expires_at: str | None = None


class ApprovalRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def setup(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_pending_actions (
                      id BIGSERIAL PRIMARY KEY,
                      chat_id TEXT NOT NULL,
                      user_id TEXT NOT NULL DEFAULT '',
                      request_id TEXT NOT NULL,
                      tool_name TEXT NOT NULL DEFAULT '',
                      gateway_name TEXT NOT NULL DEFAULT '',
                      args JSONB NOT NULL DEFAULT '{}'::JSONB,
                      summary TEXT NOT NULL DEFAULT '',
                      reason TEXT NOT NULL DEFAULT '',
                      status TEXT NOT NULL DEFAULT 'pending',
                      error_text TEXT NOT NULL DEFAULT '',
                      result_text TEXT NOT NULL DEFAULT '',
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '15 minutes')
                    );
                    """
                )
                cur.execute("ALTER TABLE mia_pending_actions ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT '';")
                cur.execute("ALTER TABLE mia_pending_actions ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;")
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_pending_actions_owner_status ON mia_pending_actions (chat_id, user_id, status, created_at DESC);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_pending_actions_expires ON mia_pending_actions (status, expires_at);"
                )
            conn.commit()

    def create_pending_action(
        self,
        *,
        chat_id: str,
        user_id: str,
        request_id: str,
        tool_name: str,
        gateway_name: str,
        args: dict[str, Any] | None = None,
        reason: str = "",
        summary: str = "",
        expires_in_minutes: int = 15,
    ) -> dict[str, Any]:
        payload = {
            "chat_id": _normalize_text(chat_id),
            "user_id": _normalize_text(user_id),
            "request_id": _normalize_text(request_id),
            "tool_name": _normalize_text(tool_name),
            "gateway_name": _normalize_text(gateway_name),
            "args": _normalize_json(args or {}),
            "summary": _normalize_text(summary) or _summarize_gateway_action(gateway_name, args),
            "reason": _normalize_text(reason),
            "expires_in_minutes": max(1, int(expires_in_minutes or 15)),
        }
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_pending_actions (
                      chat_id, user_id, request_id, tool_name, gateway_name, args, summary, reason, status, created_at, updated_at, expires_at
                    )
                    VALUES (
                      %(chat_id)s, %(user_id)s, %(request_id)s, %(tool_name)s, %(gateway_name)s, %(args)s::jsonb,
                      %(summary)s, %(reason)s, 'pending', now(), now(), now() + (%(expires_in_minutes)s || ' minutes')::interval
                    )
                    RETURNING id, chat_id, user_id, request_id, tool_name, gateway_name, args, summary, reason, status, created_at, updated_at, expires_at;
                    """,
                    {
                        **payload,
                        "args": json.dumps(_normalize_json(payload["args"])),
                    },
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row or payload)

    def latest_pending_action(self, *, chat_id: str, user_id: str) -> dict[str, Any] | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, chat_id, user_id, request_id, tool_name, gateway_name, args, summary, reason, status,
                           created_at, updated_at, expires_at
                    FROM mia_pending_actions
                    WHERE chat_id = %s
                      AND user_id = %s
                      AND status = 'pending'
                      AND expires_at > now()
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1;
                    """,
                    (str(chat_id or "").strip(), str(user_id or "").strip()),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def get_pending_action(self, action_id: int) -> dict[str, Any] | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, chat_id, user_id, request_id, tool_name, gateway_name, args, summary, reason, status,
                           created_at, updated_at, expires_at
                    FROM mia_pending_actions
                    WHERE id = %s
                    LIMIT 1;
                    """,
                    (int(action_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def claim_pending_action(self, *, action_id: int, chat_id: str, user_id: str) -> dict[str, Any] | None:
        """Atomically reserve one unexpired action for its original user."""
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE mia_pending_actions
                    SET status = 'claimed', claimed_at = now(), updated_at = now()
                    WHERE id = %s
                      AND chat_id = %s
                      AND user_id = %s
                      AND status = 'pending'
                      AND expires_at > now()
                    RETURNING id, chat_id, user_id, request_id, tool_name, gateway_name, args,
                              summary, reason, status, created_at, updated_at, expires_at;
                    """,
                    (int(action_id), _normalize_text(chat_id), _normalize_text(user_id)),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def mark_pending_action_status(
        self,
        action_id: int,
        status: str,
        *,
        result_text: str = "",
        error_text: str = "",
    ) -> dict[str, Any] | None:
        clean_status = _normalize_text(status) or "pending"
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE mia_pending_actions
                    SET status = %s,
                        result_text = %s,
                        error_text = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING id, chat_id, user_id, request_id, tool_name, gateway_name, args, summary, reason,
                              status, result_text, error_text, created_at, updated_at, expires_at;
                    """,
                    (clean_status, _normalize_text(result_text), _normalize_text(error_text), int(action_id)),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def expire_stale_pending_actions(self, *, max_age_minutes: int = 30) -> int:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_pending_actions
                    SET status = 'expired',
                        updated_at = now()
                    WHERE status IN ('pending', 'claimed')
                      AND expires_at <= now()
                    RETURNING id;
                    """,
                    (),
                )
                rows = cur.fetchall()
            conn.commit()
        return len(rows or [])

    def pending_summary(self, *, days: int = 7) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
                      COUNT(*) FILTER (WHERE status = 'executed') AS executed_count,
                      COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
                      COUNT(*) FILTER (WHERE status = 'expired') AS expired_count,
                      COUNT(*) FILTER (WHERE status = 'pending' AND created_at >= now() - (%s || ' days')::interval) AS recent_pending_count,
                      COUNT(*) FILTER (WHERE status = 'executed' AND created_at >= now() - (%s || ' days')::interval) AS recent_executed_count,
                      COUNT(*) FILTER (WHERE status = 'failed' AND created_at >= now() - (%s || ' days')::interval) AS recent_failed_count
                    FROM mia_pending_actions;
                    """,
                    (max(1, int(days or 1)), max(1, int(days or 1)), max(1, int(days or 1))),
                )
                row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT gateway_name, COUNT(*) AS total
                    FROM mia_pending_actions
                    WHERE status = 'pending'
                      AND created_at >= now() - (%s || ' days')::interval
                    GROUP BY gateway_name
                    ORDER BY total DESC, gateway_name ASC
                    LIMIT 10;
                    """,
                    (max(1, int(days or 1)),),
                )
                rows = cur.fetchall()
        return {
            "days": max(1, int(days or 1)),
            "counts": {
                "pending": int(row.get("pending_count") or 0),
                "executed": int(row.get("executed_count") or 0),
                "failed": int(row.get("failed_count") or 0),
                "expired": int(row.get("expired_count") or 0),
                "recent_pending": int(row.get("recent_pending_count") or 0),
                "recent_executed": int(row.get("recent_executed_count") or 0),
                "recent_failed": int(row.get("recent_failed_count") or 0),
            },
            "by_gateway": [
                {"gateway_name": str(row.get("gateway_name") or ""), "total": int(row.get("total") or 0)}
                for row in rows
            ],
        }
