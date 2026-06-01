#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


PATH = Path("/home/huynhminh/Projects/n8n/workflow_mia_tool_gateway.json")

ROUTE_CODE = """const source = $('Prepare Tool Request').item.json || $json || {};
const workflowMap = {
  weather: 'm1ip8fFcTkdBwtWh',
  gold: 'KRRETdOwKih9MNPh',
  news: 'dX9MXm49hdVAproP',
  search: '72gE9VPYxBgxFn6h',
  calendar: 'hEGn8N6rE17tMw5T',
  gmail: 's5LDuZZpOCAYiQsf',
  drive: 'abTxYqrVCN4Qzz5U',
  docs: 'kO3D2tjgJmy3CvSg',
  sheets: '0cwoCCOYhAldS4Qj',
  shortlink: 'D1cdbPhZef9glsNh'
};

const workflowId = workflowMap[source.workflowKey || ''];
if (!workflowId) {
  return [{
    json: {
      ok: false,
      error: `Unsupported workflow key: ${source.workflowKey || '(empty)'}`,
      tool: source.tool || '',
      workflowKey: source.workflowKey || '',
      requestId: source.requestId || ''
    }
  }];
}

return [{ json: { ...source, workflowId } }];"""


def main() -> None:
    workflow = json.loads(PATH.read_text())

    workflow["nodes"] = [
        node
        for node in workflow["nodes"]
        if node["name"]
        not in {
            "Call Gold Workflow",
            "Call News Workflow",
            "Call Search Workflow",
            "Call Calendar Workflow",
            "Call Gmail Workflow",
            "Call Drive Workflow",
            "Call Docs Workflow",
            "Call Sheets Workflow",
            "Call Shortlink Workflow",
            "Unsupported Tool",
        }
    ]

    for node in workflow["nodes"]:
        if node["name"] == "Route Tool":
            node["type"] = "n8n-nodes-base.code"
            node["typeVersion"] = 2
            node["parameters"] = {"jsCode": ROUTE_CODE}
        elif node["name"] == "Call Weather Workflow":
            node["name"] = "Call Routed Workflow"
            node["parameters"] = {
                "workflowId": {
                    "__rl": True,
                    "value": "={{ $json.workflowId }}",
                    "mode": "id",
                },
                "options": {},
            }

    workflow["connections"] = {
        "Webhook Tool Request": {
            "main": [[{"node": "Prepare Tool Request", "type": "main", "index": 0}]]
        },
        "Prepare Tool Request": {
            "main": [[{"node": "Can Continue?", "type": "main", "index": 0}]]
        },
        "Can Continue?": {
            "main": [
                [{"node": "Route Tool", "type": "main", "index": 0}],
                [{"node": "Return Error", "type": "main", "index": 0}],
            ]
        },
        "Route Tool": {
            "main": [[{"node": "Call Routed Workflow", "type": "main", "index": 0}]]
        },
        "Call Routed Workflow": {
            "main": [[{"node": "Normalize Tool Result", "type": "main", "index": 0}]]
        },
        "Normalize Tool Result": {"main": [[]]},
        "Return Error": {"main": [[]]},
    }

    PATH.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
    print(f"patched {PATH}")


if __name__ == "__main__":
    main()
