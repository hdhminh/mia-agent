#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


RETURN_CODE = r"""
const source = $json || {};
const tool = source.tool || source.workflowKey || '';
const target =
  source.docName ||
  source.sheetName ||
  source.query ||
  source.fileName ||
  source.rawText ||
  source.text ||
  '';

let text = source.response || source.text || '';
if (!text) {
  text = target
    ? `Mia chưa tìm thấy tài liệu phù hợp với "${target}".`
    : 'Mia cần tên tài liệu hoặc bảng tính để đọc.';
}

return [{
  json: {
    ok: false,
    tool,
    chatId: source.chatId || '',
    text: String(text).trim(),
    links: [],
    result: {},
    meta: {
      target: String(target || '').trim(),
      reason: source.hasTarget === false ? 'missing_target' : 'not_found'
    }
  }
}];
"""


def ensure_return_node(workflow: dict, name: str, position: list[int]) -> None:
    for node in workflow.get("nodes", []):
        if node.get("name") == name:
            node.setdefault("parameters", {})["jsCode"] = RETURN_CODE.strip() + "\n"
            return

    workflow.setdefault("nodes", []).append(
        {
            "parameters": {"jsCode": RETURN_CODE.strip() + "\n"},
            "id": name.lower().replace(" ", "-"),
            "name": name,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": position,
        }
    )


def connect(workflow: dict, source: str, output_index: int, target: str) -> None:
    connections = workflow.setdefault("connections", {})
    source_main = connections.setdefault(source, {}).setdefault("main", [])
    while len(source_main) <= output_index:
        source_main.append([])
    edge = {"node": target, "type": "main", "index": 0}
    if edge not in source_main[output_index]:
        source_main[output_index].append(edge)


def patch(rel: str, return_name: str, false_sources: list[str], position: list[int]) -> None:
    path = ROOT / rel
    workflow = json.loads(path.read_text(encoding="utf-8"))
    ensure_return_node(workflow, return_name, position)
    for source in false_sources:
        connect(workflow, source, 1, return_name)
    path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"patched {rel}")


def main() -> None:
    patch(
        "google/docs/workflow_sub_google_docs_read_doc.json",
        "Return Doc Read Empty",
        ["Co Tai Lieu Can Doc?", "Tim Thay Doc?"],
        [688, 336],
    )
    patch(
        "google/sheets/workflow_sub_google_sheets_read_sheet.json",
        "Return Sheet Read Empty",
        ["Co Sheet Can Doc?", "Tim Thay Sheet?"],
        [688, 80],
    )


if __name__ == "__main__":
    main()
