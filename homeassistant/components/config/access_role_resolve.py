"""WebSocket API to resolve visible entities for current user."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.access_role_resolver import (
    async_resolve_visible_area_ids,
    async_resolve_visible_device_ids,
    async_resolve_visible_entity_ids,
)


async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the access role resolve API."""
    websocket_api.async_register_command(hass, websocket_resolve_visible)
    return True


@websocket_api.websocket_command(
    {vol.Required("type"): "access_role/resolve_visible"}
)
@callback
def websocket_resolve_visible(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Resolve visible entities, areas, and devices for the current user."""
    user_id = connection.user.id

    entity_ids = async_resolve_visible_entity_ids(hass, user_id)
    area_ids = async_resolve_visible_area_ids(hass, user_id)
    device_ids = async_resolve_visible_device_ids(hass, user_id)

    connection.send_result(
        msg["id"],
        {
            # None means "show everything" (no roles assigned)
            "entity_ids": list(entity_ids) if entity_ids is not None else None,
            "area_ids": list(area_ids) if area_ids is not None else None,
            "device_ids": list(device_ids) if device_ids is not None else None,
        },
    )