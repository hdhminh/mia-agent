from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agent.automation import AutomationRepository
from agent.models import MiaChatRequest, MiaContext


logger = logging.getLogger(__name__)


class AutomationRunner:
    """Small durable scheduler backed by row leases in Postgres."""

    def __init__(
        self,
        *,
        repository: AutomationRepository,
        service: Any,
        poll_seconds: int = 30,
        quiet_hours: str = "",
    ) -> None:
        self.repository = repository
        self.service = service
        self.poll_seconds = max(5, int(poll_seconds))
        self.quiet_hours = str(quiet_hours or "").strip()
        self._stop = asyncio.Event()

    def _in_quiet_hours(self, now_local_hour: int) -> bool:
        if not self.quiet_hours:
            return False
        parts = self.quiet_hours.replace(" ", "").split("-")
        if len(parts) != 2:
            return False
        try:
            start, end = int(parts[0]), int(parts[1])
        except (TypeError, ValueError):
            return False
        if start == end:
            return False
        if start < end:
            return start <= now_local_hour < end
        return now_local_hour >= start or now_local_hour < end

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
            skill_name = str(automation.get("skill_name") or "").strip()
            tz_name = str(getattr(getattr(self.service, "settings", None), "timezone", None) or "UTC")
            now_local = datetime.now(ZoneInfo(tz_name))
            if skill_name == "remind_me" and self._in_quiet_hours(now_local.hour):
                error_text = "reminder skipped during quiet hours"
                return
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
            elif skill_name == "remind_me":
                await self._deliver_reminder(automation, response.final_text)
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

    async def _deliver_reminder(self, automation: dict[str, Any], text: str) -> None:
        tool_gateway = getattr(self.service, "tool_gateway", None)
        if tool_gateway is None or not str(text or "").strip():
            return
        chat_id = str(automation.get("chat_id") or "").strip()
        context = MiaContext(
            chat_id=chat_id,
            user_id=str(automation.get("user_id") or chat_id),
            timezone=str(getattr(getattr(self.service, "settings", None), "timezone", None) or "UTC"),
            request_id=f"reminder:{automation.get('id')}",
        )
        try:
            result = await asyncio.to_thread(
                tool_gateway.run_tool,
                "notify.telegram",
                {"text": str(text)[:4000], "chatId": chat_id},
                context,
            )
            if not result.ok:
                logger.warning("Reminder delivery failed for automation %s", automation.get("id"))
        except Exception:
            logger.exception("Reminder delivery error for automation %s", automation.get("id"))

    def stop(self) -> None:
        self._stop.set()
