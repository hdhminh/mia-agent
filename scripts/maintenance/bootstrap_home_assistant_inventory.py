#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_ALLOWED_DOMAINS = "light,switch,fan,climate,media_player,scene,script"


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def clean(value: Any) -> str:
    return str(value or "").strip()


def can_resolve_host(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except OSError:
        return False


def choose_base_url(explicit_base_url: str) -> str:
    candidate = clean(explicit_base_url) or "http://127.0.0.1:8123"
    dashboard_url = clean(os.getenv("MIA_HOME_DASHBOARD_URL"))
    fallbacks: list[str] = []
    if dashboard_url:
        fallbacks.append(dashboard_url)
    fallbacks.extend(
        [
            "http://127.0.0.1:8123",
            "http://localhost:8123",
        ]
    )
    if "host.docker.internal" not in candidate:
        return candidate
    host = "host.docker.internal"
    if can_resolve_host(host):
        return candidate
    for fallback in fallbacks:
        if fallback and fallback != candidate:
            return fallback
    return candidate


def normalize(value: Any) -> str:
    import unicodedata

    text = clean(value).lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    filtered = "".join(ch if ch.isalnum() or ch in {" ", "_", "-"} else " " for ch in text)
    return " ".join(filtered.split())


class HomeAssistantApi:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            headers=headers,
            data=data,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {method} {self.base_url}{path}\n{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot connect to {self.base_url}{path}\n{exc}") from exc

    def render_inventory(self, allowed_label: str, allowed_domains: list[str]) -> list[dict[str, Any]]:
        domain_list = ", ".join(f"'{domain}'" for domain in allowed_domains)
        template = "\n".join(
            [
                f"{{% set label_name = {json.dumps(allowed_label)} %}}",
                "{% set allowed = label_entities(label_name) if label_name else states | map(attribute='entity_id') | list %}",
                "{% set ns = namespace(rows=[]) %}",
                "{% for entity_id in allowed %}",
                "{% set domain = entity_id.split('.')[0] %}",
                f"{{% if domain in [{domain_list}] %}}",
                "{% set ns.rows = ns.rows + [{",
                "  'entity_id': entity_id,",
                "  'domain': domain,",
                "  'name': state_attr(entity_id, 'friendly_name') or entity_id,",
                "  'state': states(entity_id),",
                "  'area': area_name(entity_id) or '',",
                "  'device_class': state_attr(entity_id, 'device_class'),",
                "  'supported_color_modes': state_attr(entity_id, 'supported_color_modes'),",
                "  'hvac_modes': state_attr(entity_id, 'hvac_modes'),",
                "  'fan_modes': state_attr(entity_id, 'fan_modes'),",
                "  'preset_modes': state_attr(entity_id, 'preset_modes')",
                "}] %}",
                "{% endif %}",
                "{% endfor %}",
                "{{ {'entities': ns.rows} | to_json }}",
            ]
        )
        payload = self.request("POST", "/api/template", {"template": template})
        if isinstance(payload, dict) and "result" in payload:
            payload = payload["result"]
        if isinstance(payload, str):
            parsed = json.loads(payload)
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise RuntimeError("Unexpected Home Assistant template response.")
        entities = parsed.get("entities", [])
        if not isinstance(entities, list):
            raise RuntimeError("Template response did not contain an entity list.")
        return entities


def build_alias_map(entities: list[dict[str, Any]]) -> dict[str, str]:
    suggestions: dict[str, str] = {}
    seen: dict[str, int] = {}
    for item in entities:
        entity_id = clean(item.get("entity_id"))
        name = clean(item.get("name"))
        area = clean(item.get("area"))
        domain = clean(item.get("domain"))
        for candidate in {
            normalize(name),
            normalize(entity_id.split(".", 1)[-1].replace("_", " ")),
            normalize(f"{name} {area}"),
            normalize(f"{domain} {area}"),
        }:
            if not candidate:
                continue
            seen[candidate] = seen.get(candidate, 0) + 1
            if seen[candidate] == 1:
                suggestions[candidate] = entity_id
    return {key: value for key, value in suggestions.items() if seen.get(key) == 1}


def format_text_report(
    entities: list[dict[str, Any]],
    aliases: dict[str, str],
    allowed_label: str,
    default_area: str,
) -> str:
    areas = sorted({clean(item.get("area")) for item in entities if clean(item.get("area"))}, key=lambda value: normalize(value))
    lines = [
        "Home Assistant inventory for Mia",
        f"- allowed label: {allowed_label or '(all entities)'}",
        f"- default area: {default_area or '(not set)'}",
        f"- visible entities: {len(entities)}",
        f"- visible areas: {len(areas)}",
        "",
        "Areas:",
    ]
    lines.extend([f"- {area}" for area in areas] or ["- (no areas found)"])
    lines.append("")
    lines.append("Entities:")
    for item in sorted(entities, key=lambda row: (normalize(row.get("area")), normalize(row.get("domain")), normalize(row.get("name")))):
        area = clean(item.get("area")) or "-"
        lines.append(
            f"- {clean(item.get('name'))} | {clean(item.get('domain'))} | {clean(item.get('state'))} | {area} | {clean(item.get('entity_id'))}"
        )
    lines.append("")
    lines.append("Suggested MIA_HOME_ENTITY_ALIASES_JSON:")
    lines.append(json.dumps(aliases, ensure_ascii=False, indent=2, sort_keys=True))
    return "\n".join(lines)


def main() -> int:
    load_env_file(".env")

    parser = argparse.ArgumentParser(
        description="Fetch the Home Assistant inventory visible to Mia and suggest alias mappings."
    )
    parser.add_argument("--base-url", default=os.getenv("HOME_ASSISTANT_URL", "http://127.0.0.1:8123"))
    parser.add_argument("--token", default=os.getenv("HOME_ASSISTANT_TOKEN", ""))
    parser.add_argument("--allowed-label", default=os.getenv("MIA_HOME_ALLOWED_LABEL", "mia_allowed"))
    parser.add_argument("--allowed-domains", default=os.getenv("MIA_HOME_ALLOWED_DOMAINS", DEFAULT_ALLOWED_DOMAINS))
    parser.add_argument("--default-area", default=os.getenv("MIA_HOME_DEFAULT_AREA", ""))
    parser.add_argument("--format", choices=("text", "json", "env"), default="text")
    parser.add_argument("--output", default="", help="Optional file path to save the report.")
    args = parser.parse_args()

    if not args.token.strip():
        print(
            "Missing HOME_ASSISTANT_TOKEN. Create a Long-Lived Access Token in Home Assistant and either:\n"
            "1. put it into .env as HOME_ASSISTANT_TOKEN, or\n"
            "2. pass --token directly.",
            file=sys.stderr,
        )
        return 2

    allowed_domains = [part.strip() for part in clean(args.allowed_domains).split(",") if part.strip()]
    base_url = choose_base_url(args.base_url)
    api = HomeAssistantApi(base_url, args.token)
    entities = api.render_inventory(args.allowed_label.strip(), allowed_domains)
    aliases = build_alias_map(entities)

    if args.format == "json":
        payload = {
            "allowed_label": args.allowed_label.strip(),
            "default_area": args.default_area.strip(),
            "base_url": base_url,
            "allowed_domains": allowed_domains,
            "entity_count": len(entities),
            "entities": entities,
            "suggested_aliases": aliases,
        }
        output = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    elif args.format == "env":
        output = f"MIA_HOME_ENTITY_ALIASES_JSON={json.dumps(aliases, ensure_ascii=False, sort_keys=True)}"
    else:
        output = format_text_report(
            entities=entities,
            aliases=aliases,
            allowed_label=args.allowed_label.strip(),
            default_area=args.default_area.strip(),
        )
        output = f"Using Home Assistant URL: {base_url}\n\n{output}"

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
