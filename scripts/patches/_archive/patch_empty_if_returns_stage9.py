#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RETURN_CODE = r"""
const source = $json || {};

function decodeEntities(value = '') {
  return String(value)
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
}

function htmlToPlainText(value = '') {
  return decodeEntities(String(value || ''))
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<li>/gi, '- ')
    .replace(/<\/h\d>/gi, '\n')
    .replace(/<a[^>]*href="([^"]+)"[^>]*>(.*?)<\/a>/gi, '$2: $1')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/\n\s+/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const target =
  source.query ||
  source.docName ||
  source.sheetName ||
  source.fileName ||
  source.folderName ||
  source.targetName ||
  source.title ||
  source.summary ||
  source.rawText ||
  source.text ||
  '';

let text = htmlToPlainText(source.response || source.text || source.error || '');
if (!text) {
  text = target
    ? `Mia chưa xử lý được yêu cầu với "${target}". Bạn kiểm tra lại thông tin đầu vào giúp Mia nhé.`
    : 'Mia chưa đủ thông tin để xử lý yêu cầu này.';
}

return [{
  json: {
    ok: false,
    tool: source.tool || source.workflowKey || '',
    chatId: source.chatId || '',
    text,
    links: [],
    result: {},
    meta: {
      target: String(target || '').trim(),
      reason: source.hasTarget === false || source.isReady === false ? 'missing_required_input' : 'not_found_or_not_applicable'
    }
  }
}];
"""


def ensure_return_node(workflow: dict, position: list[int]) -> str:
    name = "Return Empty Branch"
    for node in workflow.get("nodes", []):
        if node.get("name") == name:
            node.setdefault("parameters", {})["jsCode"] = RETURN_CODE.strip() + "\n"
            return name

    workflow.setdefault("nodes", []).append(
        {
            "parameters": {"jsCode": RETURN_CODE.strip() + "\n"},
            "id": "return-empty-branch",
            "name": name,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": position,
        }
    )
    return name


def patch_workflow(path: Path) -> bool:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    nodes = workflow.get("nodes", [])
    connections = workflow.setdefault("connections", {})
    if_nodes = [node for node in nodes if node.get("type") == "n8n-nodes-base.if"]
    if not if_nodes:
        return False

    empty_outputs: list[tuple[str, int]] = []
    max_x = max((node.get("position", [0, 0])[0] for node in nodes), default=0)
    max_y = max((node.get("position", [0, 0])[1] for node in nodes), default=0)

    for node in if_nodes:
        source = node.get("name", "")
        source_main = connections.setdefault(source, {}).setdefault("main", [])
        for index in (0, 1):
            while len(source_main) <= index:
                source_main.append([])
            if not source_main[index]:
                empty_outputs.append((source, index))

    if not empty_outputs:
        return False

    return_name = ensure_return_node(workflow, [max_x + 240, max_y + 160])
    edge = {"node": return_name, "type": "main", "index": 0}
    for source, index in empty_outputs:
        source_main = connections[source]["main"]
        if edge not in source_main[index]:
            source_main[index].append(edge)

    path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"patched {path.relative_to(ROOT)}: {len(empty_outputs)} empty IF outputs")
    return True


def main() -> None:
    count = 0
    for path in sorted((ROOT / "google").glob("**/workflow_*.json")):
        if patch_workflow(path):
            count += 1
    print(f"patched workflows: {count}")


if __name__ == "__main__":
    main()
