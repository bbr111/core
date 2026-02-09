"""Access role registry for Home Assistant."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Literal, TypedDict

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.registry import BaseRegistry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import UNDEFINED, UndefinedType
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey
from homeassistant.util.event_type import EventType

STORAGE_KEY = "core.access_role_registry"
STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 1

DATA_REGISTRY: HassKey["AccessRoleRegistry"] = HassKey("access_role_registry")
EVENT_ACCESS_ROLE_REGISTRY_UPDATED: EventType["EventAccessRoleRegistryUpdatedData"] = (
    EventType("access_role_registry_updated")
)


class EventAccessRoleRegistryUpdatedData(TypedDict):
    """Event data for when the access role registry is updated."""

    action: Literal["create", "remove", "update"]
    access_role_id: str


class _AccessRoleStoreData(TypedDict):
    """Store data type for a single access role."""

    access_role_id: str
    name: str
    description: str | None
    icon: str | None
    color: str | None
    entity_ids: list[str]
    device_ids: list[str]
    area_ids: list[str]
    label_ids: list[str]
    user_ids: list[str]
    created_at: str
    modified_at: str


class AccessRoleRegistryStoreData(TypedDict):
    """Store data type for AccessRoleRegistry."""

    access_roles: list[_AccessRoleStoreData]


@dataclass(slots=True, frozen=True, kw_only=True)
class AccessRoleEntry:
    """Access role registry entry."""

    access_role_id: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    entity_ids: frozenset[str] = field(default_factory=frozenset)
    device_ids: frozenset[str] = field(default_factory=frozenset)
    area_ids: frozenset[str] = field(default_factory=frozenset)
    label_ids: frozenset[str] = field(default_factory=frozenset)
    user_ids: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime = field(default_factory=dt_util.utcnow)
    modified_at: datetime = field(default_factory=dt_util.utcnow)


class AccessRoleRegistry(BaseRegistry[AccessRoleRegistryStoreData]):
    """Class to hold a registry of access roles."""

    access_roles: dict[str, AccessRoleEntry]

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the access role registry."""
        self.hass = hass
        self.access_roles = {}
        self._store = Store[AccessRoleRegistryStoreData](
            hass,
            STORAGE_VERSION_MAJOR,
            STORAGE_KEY,
            atomic_writes=True,
            minor_version=STORAGE_VERSION_MINOR,
        )
        self._id_counter = 0

    @callback
    def async_get_access_role(
        self, access_role_id: str
    ) -> AccessRoleEntry | None:
        """Get access role by ID."""
        return self.access_roles.get(access_role_id)

    @callback
    def async_list_access_roles(self) -> Iterable[AccessRoleEntry]:
        """Get all access roles."""
        return self.access_roles.values()

    @callback
    def async_get_access_roles_for_user(
        self, user_id: str
    ) -> list[AccessRoleEntry]:
        """Get all access roles assigned to a user."""
        return [
            role
            for role in self.access_roles.values()
            if user_id in role.user_ids
        ]

    def _generate_id(self, name: str) -> str:
        """Generate a unique access role ID."""
        self._id_counter += 1
        slug = name.lower().replace(" ", "_")
        return f"{slug}_{self._id_counter}"

    @callback
    def async_create(
        self,
        name: str,
        *,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        entity_ids: set[str] | None = None,
        device_ids: set[str] | None = None,
        area_ids: set[str] | None = None,
        label_ids: set[str] | None = None,
        user_ids: set[str] | None = None,
    ) -> AccessRoleEntry:
        """Create a new access role."""
        self.hass.verify_event_loop_thread("access_role_registry.async_create")

        role_id = self._generate_id(name)

        access_role = AccessRoleEntry(
            access_role_id=role_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            entity_ids=frozenset(entity_ids or set()),
            device_ids=frozenset(device_ids or set()),
            area_ids=frozenset(area_ids or set()),
            label_ids=frozenset(label_ids or set()),
            user_ids=frozenset(user_ids or set()),
        )

        self.access_roles[role_id] = access_role
        self.async_schedule_save()
        self.hass.bus.async_fire_internal(
            EVENT_ACCESS_ROLE_REGISTRY_UPDATED,
            EventAccessRoleRegistryUpdatedData(
                action="create", access_role_id=role_id
            ),
        )
        return access_role

    @callback
    def async_update(
        self,
        access_role_id: str,
        *,
        name: str | UndefinedType = UNDEFINED,
        description: str | None | UndefinedType = UNDEFINED,
        icon: str | None | UndefinedType = UNDEFINED,
        color: str | None | UndefinedType = UNDEFINED,
        entity_ids: set[str] | UndefinedType = UNDEFINED,
        device_ids: set[str] | UndefinedType = UNDEFINED,
        area_ids: set[str] | UndefinedType = UNDEFINED,
        label_ids: set[str] | UndefinedType = UNDEFINED,
        user_ids: set[str] | UndefinedType = UNDEFINED,
    ) -> AccessRoleEntry:
        """Update an existing access role."""
        old = self.access_roles[access_role_id]

        changes: dict[str, Any] = {"modified_at": dt_util.utcnow()}

        if not isinstance(name, UndefinedType):
            changes["name"] = name
        if not isinstance(description, UndefinedType):
            changes["description"] = description
        if not isinstance(icon, UndefinedType):
            changes["icon"] = icon
        if not isinstance(color, UndefinedType):
            changes["color"] = color
        if not isinstance(entity_ids, UndefinedType):
            changes["entity_ids"] = frozenset(entity_ids)
        if not isinstance(device_ids, UndefinedType):
            changes["device_ids"] = frozenset(device_ids)
        if not isinstance(area_ids, UndefinedType):
            changes["area_ids"] = frozenset(area_ids)
        if not isinstance(label_ids, UndefinedType):
            changes["label_ids"] = frozenset(label_ids)
        if not isinstance(user_ids, UndefinedType):
            changes["user_ids"] = frozenset(user_ids)

        new = replace(old, **changes)
        self.access_roles[access_role_id] = new
        self.async_schedule_save()
        self.hass.bus.async_fire_internal(
            EVENT_ACCESS_ROLE_REGISTRY_UPDATED,
            EventAccessRoleRegistryUpdatedData(
                action="update", access_role_id=access_role_id
            ),
        )
        return new

    @callback
    def async_delete(self, access_role_id: str) -> None:
        """Delete an access role."""
        del self.access_roles[access_role_id]
        self.async_schedule_save()
        self.hass.bus.async_fire_internal(
            EVENT_ACCESS_ROLE_REGISTRY_UPDATED,
            EventAccessRoleRegistryUpdatedData(
                action="remove", access_role_id=access_role_id
            ),
        )

    async def async_load(self) -> None:
        """Load the access role registry."""
        data = await self._store.async_load()

        if data is None:
            self.access_roles = {}
            return

        for role_data in data["access_roles"]:
            self.access_roles[role_data["access_role_id"]] = AccessRoleEntry(
                access_role_id=role_data["access_role_id"],
                name=role_data["name"],
                description=role_data.get("description"),
                icon=role_data.get("icon"),
                color=role_data.get("color"),
                entity_ids=frozenset(role_data.get("entity_ids", [])),
                device_ids=frozenset(role_data.get("device_ids", [])),
                area_ids=frozenset(role_data.get("area_ids", [])),
                label_ids=frozenset(role_data.get("label_ids", [])),
                user_ids=frozenset(role_data.get("user_ids", [])),
                created_at=datetime.fromisoformat(role_data["created_at"]),
                modified_at=datetime.fromisoformat(role_data["modified_at"]),
            )

    @callback
    def _data_to_save(self) -> AccessRoleRegistryStoreData:
        """Return data to save."""
        return AccessRoleRegistryStoreData(
            access_roles=[
                _AccessRoleStoreData(
                    access_role_id=role.access_role_id,
                    name=role.name,
                    description=role.description,
                    icon=role.icon,
                    color=role.color,
                    entity_ids=list(role.entity_ids),
                    device_ids=list(role.device_ids),
                    area_ids=list(role.area_ids),
                    label_ids=list(role.label_ids),
                    user_ids=list(role.user_ids),
                    created_at=role.created_at.isoformat(),
                    modified_at=role.modified_at.isoformat(),
                )
                for role in self.access_roles.values()
            ]
        )


@callback
def async_get(hass: HomeAssistant) -> AccessRoleRegistry:
    """Get the access role registry."""
    return hass.data[DATA_REGISTRY]