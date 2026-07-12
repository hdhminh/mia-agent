#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
COMPOSE_FILE = ROOT / "infra" / "docker-compose.yml"
GATEWAY_WORKFLOW = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
SMARTHOME_WORKFLOW = (
    ROOT / "execution" / "integrations" / "homeassistant" / "workflow_sub_home_assistant_smart_home_master.json"
)


def run_step(label: str, args: list[str], allow_failure: bool = False) -> int:
    print(f"\n==> {label}")
    completed = subprocess.run(args, cwd=ROOT, check=False)
    if completed.returncode != 0 and not allow_failure:
        print(f"FAILED: {label}", file=sys.stderr)
        return completed.returncode
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate, sync, restart, and re-check the Mia smart-home stack."
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip syncing n8n workflows if you only changed .env values.",
    )
    parser.add_argument(
        "--skip-restart",
        action="store_true",
        help="Skip Docker restart if you only want validation and readiness output.",
    )
    parser.add_argument(
        "--readiness-only",
        action="store_true",
        help="Run only the final readiness report.",
    )
    args = parser.parse_args()

    if args.readiness_only:
        return run_step(
            "Smart-home readiness report",
            ["python", "scripts/maintenance/check_smarthome_readiness.py"],
            allow_failure=True,
        )

    if not ENV_FILE.exists():
        print(f"Missing env file: {ENV_FILE}", file=sys.stderr)
        return 2

    steps: list[tuple[str, list[str], bool]] = [
        (
            "Validate workflow JSON",
            ["python", "scripts/maintenance/validate_workflow_json.py"],
            False,
        ),
        (
            "Validate tool contracts",
            ["python", "scripts/maintenance/validate_tool_contracts.py"],
            False,
        ),
    ]

    if not args.skip_sync:
        steps.extend(
            [
                (
                    "Sync Mia Tool Gateway workflow",
                    ["python", "scripts/maintenance/sync_workflows.py", str(GATEWAY_WORKFLOW)],
                    False,
                ),
                (
                    "Sync Home Assistant smart-home workflow",
                    [
                        "python",
                        "scripts/maintenance/sync_workflows.py",
                        "--create-missing",
                        str(SMARTHOME_WORKFLOW),
                    ],
                    False,
                ),
            ]
        )

    if not args.skip_restart:
        steps.append(
            (
                "Restart smart-home related containers",
                [
                    "docker",
                    "compose",
                    "--env-file",
                    str(ENV_FILE),
                    "-f",
                    str(COMPOSE_FILE),
                    "up",
                    "-d",
                    "--build",
                    "--no-deps",
                    "n8n",
                    "mia-core",
                    "home-assistant",
                    "memory-embedder",
                ],
                False,
            )
        )

    steps.append(
        (
            "Smart-home readiness report",
            ["python", "scripts/maintenance/check_smarthome_readiness.py"],
            True,
        )
    )

    for label, command, allow_failure in steps:
        exit_code = run_step(label, command, allow_failure=allow_failure)
        if exit_code != 0 and not allow_failure:
            return exit_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
