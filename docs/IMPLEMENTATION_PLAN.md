# Mia Agent Platform Upgrade

Branch: `feat/mia-agent-platform-upgrade`

This upgrade hardens the current runtime, makes tool registration declarative,
adds resumable skills, expands integrations, and introduces repeatable CI and
operational checks. All changes are delivered on one branch and one pull
request, with logically separated commits.

## Workstreams

1. Repair media/web gateway routing and normalize tool contracts.
2. Make API and gateway authentication fail closed.
3. Make approvals user-scoped, atomic, cancellable, and idempotent.
4. Add SSRF, upload, resource, and rate-limit protections.
5. Add dependency controls, CI, secret scanning, and workflow validation.
6. Introduce declarative ToolSpec definitions and capability discovery.
7. Refactor routing modules and add a resumable skill engine.
8. Add Tasks, Contacts, GitHub write, Scheduler, and MCP adapter foundations.
9. Improve memory lifecycle, observability, cost controls, and documentation.

## Definition of done

- Existing tools have matching Python, gateway, workflow, and documentation
  contracts.
- Protected endpoints reject missing or invalid credentials.
- External writes require user-scoped approval and cannot execute twice.
- Web and media inputs have bounded resource usage.
- CI validates Python, workflows, contracts, secrets, and Docker builds.
- ToolSpec is the source of truth for capability metadata.
- Skills can pause, resume, recover, and avoid replaying completed writes.
- New integration foundations are registered with explicit risk policies.
- Tests, migration notes, and operating documentation are included.
