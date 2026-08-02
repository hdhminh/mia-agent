from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.execution_client import N8nToolGatewayClient
from agent.models import MiaContext
from agent.skills.common import _run_gateway_tool, _with_instruction_fallback


def get_smarthome_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool("smarthome_help")
    def smarthome_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Home Assistant smart-home capabilities and setup expectations."""
        return _run_gateway_tool(tool_gateway, "smarthome.help", {}, runtime)

    @tool("smarthome_list_areas")
    def smarthome_list_areas_tool(
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List smart-home areas that Mia is allowed to control."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.list_areas",
            _with_instruction_fallback("smarthome", "liet ke khu vuc nha thong minh", {}, instruction),
            runtime,
        )

    @tool("smarthome_list_devices")
    def smarthome_list_devices_tool(
        area: str = "",
        query: str = "",
        limit: int = 20,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List allowed smart-home devices, optionally filtered by area or query."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.list_devices",
            _with_instruction_fallback(
                "smarthome",
                "liet ke thiet bi nha thong minh",
                {
                    "area": area.strip(),
                    "query": query.strip(),
                    "limit": max(1, min(limit, 50)),
                },
                instruction,
                area,
                query,
            ),
            runtime,
        )

    @tool("smarthome_room_status")
    def smarthome_room_status_tool(
        area: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Summarize current smart-home status for one room or area."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.room_status",
            _with_instruction_fallback(
                "smarthome",
                "xem trang thai phong",
                {"area": area.strip()},
                instruction,
                area,
            ),
            runtime,
        )

    @tool("smarthome_turn_on")
    def smarthome_turn_on_tool(
        target: str = "",
        area: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Turn on one allowed smart-home entity."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.turn_on",
            _with_instruction_fallback(
                "smarthome",
                "bat thiet bi",
                {"target": target.strip(), "area": area.strip()},
                instruction,
                target,
                area,
            ),
            runtime,
        )

    @tool("smarthome_turn_off")
    def smarthome_turn_off_tool(
        target: str = "",
        area: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Turn off one allowed smart-home entity."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.turn_off",
            _with_instruction_fallback(
                "smarthome",
                "tat thiet bi",
                {"target": target.strip(), "area": area.strip()},
                instruction,
                target,
                area,
            ),
            runtime,
        )

    @tool("smarthome_toggle")
    def smarthome_toggle_tool(
        target: str = "",
        area: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Toggle one allowed smart-home entity."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.toggle",
            _with_instruction_fallback(
                "smarthome",
                "dao trang thai thiet bi",
                {"target": target.strip(), "area": area.strip()},
                instruction,
                target,
                area,
            ),
            runtime,
        )

    @tool("smarthome_set_light")
    def smarthome_set_light_tool(
        target: str = "",
        area: str = "",
        brightness_pct: int = 0,
        color_temp_kelvin: int = 0,
        rgb_color: str = "",
        transition_seconds: int = 0,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Control a light with brightness or color settings."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.set_light",
            _with_instruction_fallback(
                "smarthome",
                "chinh den",
                {
                    "target": target.strip(),
                    "area": area.strip(),
                    "brightnessPct": max(0, min(brightness_pct, 100)),
                    "colorTempKelvin": max(0, color_temp_kelvin),
                    "rgbColor": rgb_color.strip(),
                    "transitionSeconds": max(0, transition_seconds),
                },
                instruction,
                target,
                area,
                brightness_pct,
                color_temp_kelvin,
                rgb_color,
            ),
            runtime,
        )

    @tool("smarthome_set_climate")
    def smarthome_set_climate_tool(
        target: str = "",
        area: str = "",
        hvac_mode: str = "",
        temperature: float = 0,
        fan_mode: str = "",
        swing_mode: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Control a climate entity such as an air-conditioner."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.set_climate",
            _with_instruction_fallback(
                "smarthome",
                "chinh dieu hoa",
                {
                    "target": target.strip(),
                    "area": area.strip(),
                    "hvacMode": hvac_mode.strip(),
                    "temperature": temperature,
                    "fanMode": fan_mode.strip(),
                    "swingMode": swing_mode.strip(),
                },
                instruction,
                target,
                area,
                hvac_mode,
                temperature,
                fan_mode,
                swing_mode,
            ),
            runtime,
        )

    @tool("smarthome_set_fan")
    def smarthome_set_fan_tool(
        target: str = "",
        area: str = "",
        percentage: int = 0,
        preset_mode: str = "",
        direction: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Control a fan-like entity, including percentage and preset mode."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.set_fan",
            _with_instruction_fallback(
                "smarthome",
                "chinh quat",
                {
                    "target": target.strip(),
                    "area": area.strip(),
                    "percentage": max(0, min(percentage, 100)),
                    "presetMode": preset_mode.strip(),
                    "direction": direction.strip(),
                },
                instruction,
                target,
                area,
                percentage,
                preset_mode,
                direction,
            ),
            runtime,
        )

    @tool("smarthome_set_media")
    def smarthome_set_media_tool(
        target: str = "",
        area: str = "",
        action: str = "",
        volume_level: float = 0,
        media_content_id: str = "",
        media_content_type: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Control a media player such as a Google Cast speaker."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.set_media",
            _with_instruction_fallback(
                "smarthome",
                "chinh loa",
                {
                    "target": target.strip(),
                    "area": area.strip(),
                    "action": action.strip(),
                    "volumeLevel": volume_level,
                    "mediaContentId": media_content_id.strip(),
                    "mediaContentType": media_content_type.strip(),
                },
                instruction,
                target,
                area,
                action,
                volume_level,
                media_content_id,
                media_content_type,
            ),
            runtime,
        )

    @tool("smarthome_announce")
    def smarthome_announce_tool(
        message: str = "",
        target: str = "",
        area: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Speak a Vietnamese announcement on a configured smart speaker target."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.announce",
            _with_instruction_fallback(
                "smarthome",
                "phat thong bao loa",
                {
                    "message": message.strip(),
                    "target": target.strip(),
                    "area": area.strip(),
                },
                instruction,
                message,
                target,
                area,
            ),
            runtime,
        )

    @tool("smarthome_run_scene")
    def smarthome_run_scene_tool(
        scene: str = "",
        area: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Activate one Home Assistant scene."""
        return _run_gateway_tool(
            tool_gateway,
            "smarthome.run_scene",
            _with_instruction_fallback(
                "smarthome",
                "chay scene",
                {"scene": scene.strip(), "area": area.strip()},
                instruction,
                scene,
                area,
            ),
            runtime,
        )

    return [
        smarthome_help_tool,
        smarthome_list_areas_tool,
        smarthome_list_devices_tool,
        smarthome_room_status_tool,
        smarthome_turn_on_tool,
        smarthome_turn_off_tool,
        smarthome_toggle_tool,
        smarthome_set_light_tool,
        smarthome_set_climate_tool,
        smarthome_set_fan_tool,
        smarthome_set_media_tool,
        smarthome_announce_tool,
        smarthome_run_scene_tool,
    ]
