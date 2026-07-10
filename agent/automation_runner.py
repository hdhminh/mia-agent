from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent.automation import AutomationRepository
from agent.models import MiaChatRequest


logger = logging.getLogger(__name__)


class AutomationRunner:
    """Small durable scheduler backed by row leases in Postgres."""

    def __init__(self, *, repository: AutomationRepository, service: Any, poll_seconds: int = 30) -> None:
        self.repository = repository
        self.service = service
        self.poll_seconds = max(5, int(poll_seconds))
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                for automation in await asyncio.to_thread(self.repository.claim_due):
                    await self._execute(automation)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Automation scheduler poll failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_seconds)
            except TimeoutError:
                pass

    async def _execute(self, automation: dict[str, Any]) -> None:
        error_text = ""
        try:
            request = MiaChatRequest(
                chat_id=str(automation["chat_id"]),
                user_id=str(automation["user_id"]),
                text=str(automation.get("input_text") or automation.get("skill_name") or automation.get("name")),
                metadata={
                    "automation_id": automation["id"],
                    "skill_name": automation["skill_name"],
                    "scheduled": True,
                },
            )
            response = await asyncio.to_thread(self.service.chat, request)
            if not response.ok:
                error_text = response.final_text
        except Exception as exc:
            logger.exception("Automation %s failed", automation.get("id"))
            error_text = str(exc)
        finally:
            await asyncio.to_thread(
                self.repository.finish_run,
                automation_id=int(automation["id"]),
                schedule=str(automation["schedule"]),
                error_text=error_text,
            )

    def stop(self) -> None:
        self._stop.set()
