from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.execution_client import N8nToolGatewayClient
from agent.models import MiaContext
from agent.skills.common import _run_gateway_tool, _with_instruction_fallback


def get_google_maps_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool("maps_help")
    def maps_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Google Maps capabilities, supported actions, and billing guardrails."""
        return _run_gateway_tool(tool_gateway, "maps.help", {}, runtime)

    @tool("maps_geocode")
    def maps_geocode_tool(
        address: str = "",
        region: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Resolve an address or place name into coordinates and normalized address data."""
        return _run_gateway_tool(
            tool_gateway,
            "maps.geocode",
            _with_instruction_fallback(
                "maps",
                "tim toa do dia diem",
                {
                    "address": address.strip(),
                    "region": region.strip(),
                    "language": language.strip(),
                },
                instruction,
                address,
                region,
                language,
            ),
            runtime,
        )

    @tool("maps_reverse_geocode")
    def maps_reverse_geocode_tool(
        lat_lng: str = "",
        latitude: str = "",
        longitude: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Resolve coordinates into a nearby address or place description."""
        return _run_gateway_tool(
            tool_gateway,
            "maps.reverse_geocode",
            _with_instruction_fallback(
                "maps",
                "tim dia chi theo toa do",
                {
                    "latLng": lat_lng.strip(),
                    "latitude": latitude.strip(),
                    "longitude": longitude.strip(),
                    "language": language.strip(),
                },
                instruction,
                lat_lng,
                latitude,
                longitude,
                language,
            ),
            runtime,
        )

    @tool("maps_search_place")
    def maps_search_place_tool(
        query: str = "",
        location_bias: str = "",
        region: str = "",
        language: str = "",
        max_results: int = 5,
        open_now: bool = False,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Maps places by text query with optional location bias."""
        return _run_gateway_tool(
            tool_gateway,
            "maps.search_place",
            _with_instruction_fallback(
                "maps",
                "tim dia diem",
                {
                    "query": query.strip(),
                    "locationBias": location_bias.strip(),
                    "region": region.strip(),
                    "language": language.strip(),
                    "maxResults": max(1, min(max_results, 10)),
                    "openNow": bool(open_now),
                },
                instruction,
                query,
                location_bias,
                region,
                language,
            ),
            runtime,
        )

    @tool("maps_place_details")
    def maps_place_details_tool(
        place_id: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Fetch detailed information for a Google Maps place id."""
        return _run_gateway_tool(
            tool_gateway,
            "maps.place_details",
            _with_instruction_fallback(
                "maps",
                "xem chi tiet dia diem",
                {
                    "placeId": place_id.strip(),
                    "language": language.strip(),
                },
                instruction,
                place_id,
                language,
            ),
            runtime,
        )

    @tool("maps_compute_route")
    def maps_compute_route_tool(
        origin: str = "",
        destination: str = "",
        travel_mode: str = "DRIVE",
        departure_time: str = "",
        language: str = "",
        region: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Compute a route between two points using Google Routes API."""
        return _run_gateway_tool(
            tool_gateway,
            "maps.compute_route",
            _with_instruction_fallback(
                "maps",
                "chi duong",
                {
                    "origin": origin.strip(),
                    "destination": destination.strip(),
                    "travelMode": travel_mode.strip().upper() or "DRIVE",
                    "departureTime": departure_time.strip(),
                    "language": language.strip(),
                    "region": region.strip(),
                },
                instruction,
                origin,
                destination,
                travel_mode,
                departure_time,
                language,
                region,
            ),
            runtime,
        )

    return [
        maps_help_tool,
        maps_geocode_tool,
        maps_reverse_geocode_tool,
        maps_search_place_tool,
        maps_place_details_tool,
        maps_compute_route_tool,
    ]
