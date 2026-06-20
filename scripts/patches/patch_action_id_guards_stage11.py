#!/usr/bin/env python3
"""Require concrete IDs for high-risk Google write/delete/share actions.

Read/search workflows may resolve by name, but mutating workflows should not
act on the first search result. This stage keeps those workflows callable while
returning plain guidance when the caller only provides a name/query.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


TARGETS = {
    "google/calendar/workflow_sub_google_calendar_delete_event.json": {
        "prepare": "Chuan Bi Xoa Lich",
        "id_fields": ("eventId",),
        "gate": "hasDeleteQuery",
        "text": "Mia chưa xoá lịch vì hành động này cần eventId cụ thể. Bạn hãy tìm lịch trước, chọn đúng sự kiện, rồi gửi lại kèm eventId nhé.",
    },
    "google/docs/workflow_sub_google_docs_append_doc.json": {
        "prepare": "Prepare Action",
        "id_fields": ("docId", "documentId", "fileId", "targetId"),
        "gate": "hasTarget",
        "text": "Mia chưa ghi thêm vào Google Doc vì hành động này cần docId/documentId cụ thể. Bạn hãy tìm hoặc đọc tài liệu trước để lấy đúng ID rồi gửi lại nội dung cần thêm nhé.",
    },
    "google/docs/workflow_sub_google_docs_delete_doc.json": {
        "prepare": "Prepare Action",
        "id_fields": ("docId", "documentId", "fileId", "targetId"),
        "gate": "hasTarget",
        "text": "Mia chưa xoá Google Doc vì hành động này cần docId/documentId cụ thể. Bạn hãy tìm tài liệu trước, kiểm tra đúng file, rồi gửi lại kèm ID nhé.",
    },
    "google/drive/workflow_sub_google_drive_copy_file.json": {
        "prepare": "Prepare Action",
        "id_fields": ("fileId", "targetId"),
        "gate": "hasTarget",
        "text": "Mia chưa copy file vì hành động này cần fileId cụ thể. Bạn hãy tìm file trước, chọn đúng file, rồi gửi lại kèm fileId và tên bản sao nếu cần.",
    },
    "google/drive/workflow_sub_google_drive_delete_file.json": {
        "prepare": "Prepare Action",
        "id_fields": ("fileId", "targetId"),
        "gate": "hasTarget",
        "text": "Mia chưa xoá file vì hành động này cần fileId cụ thể. Bạn hãy tìm file trước, kiểm tra đúng file, rồi gửi lại kèm fileId nhé.",
    },
    "google/drive/workflow_sub_google_drive_delete_folder.json": {
        "prepare": "Prepare Action",
        "id_fields": ("folderId", "targetId", "fileId"),
        "gate": "hasTarget",
        "text": "Mia chưa xoá folder vì hành động này cần folderId cụ thể. Bạn hãy tìm folder trước, kiểm tra đúng folder, rồi gửi lại kèm folderId nhé.",
    },
    "google/drive/workflow_sub_google_drive_move_file.json": {
        "prepare": "Prepare Action",
        "id_fields": ("fileId", "targetId"),
        "also_require_any": ("targetFolderId", "folderId"),
        "gate": "hasTarget",
        "text": "Mia chưa di chuyển file vì hành động này cần fileId và targetFolderId cụ thể. Bạn hãy tìm file/folder trước rồi gửi lại đúng hai ID nhé.",
    },
    "google/drive/workflow_sub_google_drive_rename_file.json": {
        "prepare": "Prepare Action",
        "id_fields": ("fileId", "targetId"),
        "also_require_any": ("newName",),
        "gate": "hasTarget",
        "text": "Mia chưa đổi tên file vì hành động này cần fileId cụ thể và tên mới. Bạn hãy tìm file trước, chọn đúng file, rồi gửi lại kèm fileId nhé.",
    },
    "google/drive/workflow_sub_google_drive_share_file.json": {
        "prepare": "Prepare Action",
        "id_fields": ("fileId", "targetId"),
        "also_require_any": ("email",),
        "gate": "hasTarget",
        "text": "Mia chưa share file vì hành động này cần fileId cụ thể và email nhận quyền. Bạn hãy tìm file trước, kiểm tra đúng file, rồi gửi lại kèm fileId nhé.",
    },
    "google/sheets/workflow_sub_google_sheets_append_row.json": {
        "prepare": "Prepare Action",
        "id_fields": ("spreadsheetId", "sheetId", "fileId", "targetId"),
        "also_require_any": ("values", "rowData"),
        "gate": "hasTarget",
        "text": "Mia chưa thêm dòng vào Google Sheet vì hành động này cần spreadsheetId cụ thể. Bạn hãy tìm sheet trước, chọn đúng bảng, rồi gửi lại kèm ID và dữ liệu dòng nhé.",
    },
    "google/sheets/workflow_sub_google_sheets_delete_sheet.json": {
        "prepare": "Prepare Action",
        "id_fields": ("spreadsheetId", "sheetId", "fileId", "targetId"),
        "gate": "hasTarget",
        "text": "Mia chưa xoá Google Sheet vì hành động này cần spreadsheetId cụ thể. Bạn hãy tìm sheet trước, kiểm tra đúng bảng, rồi gửi lại kèm ID nhé.",
    },
    "google/sheets/workflow_sub_google_sheets_update_cell.json": {
        "prepare": "Prepare Action",
        "id_fields": ("spreadsheetId", "sheetId", "fileId", "targetId"),
        "also_require_any": ("cell",),
        "gate": "hasTarget",
        "text": "Mia chưa cập nhật Google Sheet vì hành động này cần spreadsheetId cụ thể, ô cần sửa và giá trị mới. Bạn hãy tìm sheet trước rồi gửi lại kèm ID nhé.",
    },
}


GUARD_MARKER = "// Stage 11 exact-id safety guard"


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_guard(config: dict[str, object]) -> str:
    id_fields = ", ".join(js_string(field) for field in config["id_fields"])
    also = ", ".join(js_string(field) for field in config.get("also_require_any", ()))
    gate = str(config["gate"])
    text = js_string(str(config["text"]))

    return f"""

{GUARD_MARKER}
const __stage11Pick = (...values) => {{
  for (const value of values) {{
    if (Array.isArray(value) && value.length) return value;
    if (value === undefined || value === null) continue;
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
    if (typeof value === 'boolean') return value;
  }}
  return '';
}};
const __stage11Source = source || {{}};
const __stage11Args = args || __stage11Source.args || __stage11Source.payload?.args || {{}};
const __stage11Payload = typeof payload !== 'undefined' ? payload : (__stage11Source.payload || {{}});
const __stage11IdFields = [{id_fields}];
const __stage11AlsoFields = [{also}];
const __stage11HasId = Boolean(__stage11Pick(...__stage11IdFields.map((field) =>
  __stage11Source[field] || __stage11Args[field] || __stage11Payload[field]
)));
const __stage11HasAlso = __stage11AlsoFields.length === 0 || Boolean(__stage11Pick(...__stage11AlsoFields.map((field) =>
  __stage11Source[field] || __stage11Args[field] || __stage11Payload[field]
)));
const __stage11Allowed = __stage11HasId && __stage11HasAlso;
const __stage11Response = __stage11Allowed ? '' : {text};
"""


def patch_return(js: str, config: dict[str, object]) -> str:
    gate = str(config["gate"])

    if "Stage 11 exact-id safety guard" in js:
      return js

    guard = build_guard(config)

    # Most prepare nodes end with a single return of one JSON object. We patch
    # only the final readiness fields so parsed names can still be returned as
    # context for the user-facing guidance.
    if f"{gate}," in js:
        js = js.replace(
            f"{gate},",
            f"{gate}: Boolean({gate} && __stage11Allowed),",
            1,
        )
    elif f"{gate}: Boolean(" in js:
        marker = f"{gate}: Boolean("
        start = js.index(marker) + len(marker)
        close = js.index("),", start)
        original = js[start:close]
        js = js[:start] + f"__stage11Allowed && ({original})" + js[close:]

    # Keep each workflow's existing wording as the allowed path, but override it
    # with a plain safety message when only a name/query was supplied.
    js = js.replace("response:", "response: __stage11Response ? __stage11Response :", 1)

    return js.replace("return [{", guard + "\nreturn [{", 1)


def patch_file(rel: str, config: dict[str, object]) -> bool:
    path = ROOT / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False

    for node in data.get("nodes", []):
        if node.get("name") != config["prepare"]:
            continue
        params = node.setdefault("parameters", {})
        js = params.get("jsCode", "")
        patched = patch_return(js, config)
        if patched != js:
            params["jsCode"] = patched
            changed = True

    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    changed = []
    for rel, config in TARGETS.items():
        if patch_file(rel, config):
            changed.append(rel)

    print(f"patched {len(changed)} workflow(s)")
    for rel in changed:
        print(f"- {rel}")


if __name__ == "__main__":
    main()
