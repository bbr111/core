"""Resolve access roles to visible entities for a user."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.access_role_registry import (
    AccessRoleEntry,
    AccessRoleRegistry,
    async_get as async_get_access_role_registry,
)


@callback
def async_resolve_visible_entity_ids(
    hass: HomeAssistant,
    user_id: str,
) -> set[str] | None:
    """Resolve all visible entity IDs for a user based on access roles.

    Returns None if the user has no access roles assigned (= show everything).
    Returns a set of entity IDs if roles are assigned (= show only these).
    """
    access_role_registry = async_get_access_role_registry(hass)
    roles = access_role_registry.async_get_access_roles_for_user(user_id)

    if not roles:
        # No roles assigned means no filtering (admin/owner behavior)
        return None

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)

    visible_entity_ids: set[str] = set()

    for role in roles:
        # Direct entity IDs
        visible_entity_ids.update(role.entity_ids)

        # Entities from devices
        for device_id in role.device_ids:
            entities = er.async_entries_for_device(
                entity_registry, device_id, include_disabled_entities=False
            )
            visible_entity_ids.update(e.entity_id for e in entities)

        # Entities from areas
        for area_id in role.area_ids:
            # Entities directly assigned to area
            entities = er.async_entries_for_area(entity_registry, area_id)
            visible_entity_ids.update(e.entity_id for e in entities)

            # Entities from devices in this area
            devices = dr.async_entries_for_area(device_registry, area_id)
            for device in devices:
                entities = er.async_entries_for_device(
                    entity_registry,
                    device.id,
                    include_disabled_entities=False,
                )
                visible_entity_ids.update(e.entity_id for e in entities)

        # Entities from labels
        for label_id in role.label_ids:
            entities = er.async_entries_for_label(entity_registry, label_id)
            visible_entity_ids.update(e.entity_id for e in entities)

    return visible_entity_ids


@callback
def async_resolve_visible_area_ids(
    hass: HomeAssistant,
    user_id: str,
) -> set[str] | None:
    """Resolve all visible area IDs for a user based on access roles.

    Returns None if the user has no access roles assigned.
    """
    access_role_registry = async_get_access_role_registry(hass)
    roles = access_role_registry.async_get_access_roles_for_user(user_id)

    if not roles:
        return None

    visible_area_ids: set[str] = set()

    for role in roles:
        visible_area_ids.update(role.area_ids)

    return visible_area_ids


@callback
def async_resolve_visible_device_ids(
    hass: HomeAssistant,
    user_id: str,
) -> set[str] | None:
    """Resolve all visible device IDs for a user based on access roles.

    Returns None if the user has no access roles assigned.
    """
    access_role_registry = async_get_access_role_registry(hass)
    roles = access_role_registry.async_get_access_roles_for_user(user_id)

    if not roles:
        return None

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    visible_device_ids: set[str] = set()

    for role in roles:
        visible_device_ids.update(role.device_ids)

        # Devices from areas
        for area_id in role.area_ids:
            devices = dr.async_entries_for_area(device_registry, area_id)
            visible_device_ids.update(d.id for d in devices)

        # Devices from entities
        for entity_id in role.entity_ids:
            entity_entry = entity_registry.async_get(entity_id)
            if entity_entry and entity_entry.device_id:
                visible_device_ids.add(entity_entry.device_id)

    return visible_device_ids
