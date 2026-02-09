"""WebSocket API for access role management."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.access_role_registry import (
    AccessRoleEntry,
    AccessRoleRegistry,
    async_get as async_get_access_role_registry,
)


async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the access role config API."""
    websocket_api.async_register_command(hass, websocket_list_access_roles)
    websocket_api.async_register_command(hass, websocket_create_access_role)
    websocket_api.async_register_command(hass, websocket_update_access_role)
    websocket_api.async_register_command(hass, websocket_delete_access_role)
    websocket_api.async_register_command(
        hass, websocket_list_access_roles_for_current_user
    )
    return True


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "config/access_role/list"}
)
@callback
def websocket_list_access_roles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List all access roles."""
    registry = async_get_access_role_registry(hass)
    connection.send_result(
        msg["id",
        [
            _entry_to_dict(entry)
            for entry in registry.async_list_access_roles()
        ],
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "config/access_role/create",
        vol.Required("name"): str,
        vol.Optional("description"): vol.Any(str, None),
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("color"): vol.Any(str, None),
        vol.Optional("entity_ids"): [str],
        vol.Optional("device_ids"): [str],
        vol.Optional("area_ids"): [str],
        vol.Optional("label_ids"): [str],
        vol.Optional("user_ids"): [str],
    }
)
@callback
def websocket_create_access_role(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new access role."""
    registry = async_get_access_role_registry(hass)

    msg_id = msg["id"]

    try:
        entry = registry.async_create(
            name=msg["name"],
            description=msg.get("description"),
            icon=msg.get("icon"),
            color=msg.get("color"),
            entity_ids=set(msg.get("entity_ids", [])),
            device_ids=set(msg.get("device_ids", [])),
            area_ids=set(msg.get("area_ids", [])),
            label_ids=set(msg.get("label_ids", [])),
            user_ids=set(msg.get("user_ids", [])),
        )
    except ValueError as err:
        connection.send_error(msg_id, "invalid_info", str(err))
        return

    connection.send_result(msg_id, _entry_to_dict(entry))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "config/access_role/update",
        vol.Required("access_role_id"): str,
        vol.Optional("name"): str,
        vol.Optional("description"): vol.Any(str, None),
        vol.Optional("icon"): vol.Any(str, None),
        vol.Optional("color"): vol.Any(str, None),
        vol.Optional("entity_ids"): [str],
        vol.Optional("device_ids"): [str],
        vol.Optional("area_ids"): [str],
        vol.Optional("label_ids"): [str],
        vol.Optional("user_ids"): [str],
    }
)
@callback
def websocket_update_access_role(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update an access role."""
    registry = async_get_access_role_registry(hass)

    msg_id = msg["id"]
    access_role_id = msg["access_role_id"]

    if registry.async_get_access_role(access_role_id) is None:
        connection.send_error(msg_id, "not_found", "Access role not found")
        return

    kwargs: dict[str, Any] = {}
    for key in ("name", "description", "icon", "color"):
        if key in msg:
            kwargs[key] = msg[key]

    for set_key in ("entity_ids", "device_ids", "area_ids", "label_ids", "user_ids"):
        if set_key in msg:
            kwargs[set_key] = set(msg[set_key])

    try:
        entry = registry.async_update(access_role_id, **kwargs)
    except ValueError as err:
        connection.send_error(msg_id, "invalid_info", str(err))
        return

    connection.send_result(msg_id, _entry_to_dict(entry))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "config/access_role/delete",
        vol.Required("access_role_id"): str,
    }
)
@callback
def websocket_delete_access_role(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete an access role."""
    registry = async_get_access_role_registry(hass)

    try:
        registry.async_delete(msg["access_role_id"])
    except KeyError:
        connection.send_error(msg["id"], "not_found", "Access role not found")
        return

    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "config/access_role/list_for_current_user"}
)
@callback
def websocket_list_access_roles_for_current_user(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List access roles for the currently authenticated user."""
    registry = async_get_access_role_registry(hass)
    user_id = connection.user.id
    roles = registry.async_get_access_roles_for_user(user_id)
    connection.send_result(
        msg["id"],
        [_entry_to_dict(entry) for entry in roles],
    )


def _entry_to_dict(entry: AccessRoleEntry) -> dict[str, Any]:
    """Convert an access role entry to a dictionary."""
    return {
        "access_role_id": entry.access_role_id,
        "name": entry.name,
        "description": entry.description,
        "icon": entry.icon,
        "color": entry.color,
        "entity_ids": list(entry.entity_ids),
        "device_ids": list(entry.device_ids),
        "area_ids": list(entry.area_ids),
        "label_ids": list(entry.label_ids),
        "user_ids": list(entry.user_ids),
        "created_at": entry.created_at.isoformat(),
        "modified_at": entry.modified_at.isoformat(),
    }