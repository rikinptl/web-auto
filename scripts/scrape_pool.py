"""Shared lead pool for parallel niche scrapes — stop when global cap is hit."""

from __future__ import annotations

import asyncio

from maps_url import place_key, resolve_maps_url
from sheets import InventorySkipIndex, normalize_name, normalize_phone


class GlobalLeadPool:
    """Thread-safe pool across concurrent niche scrapers."""

    def __init__(self, cap: int, skip_index: InventorySkipIndex | None = None):
        self.cap = cap
        self.leads: list[dict] = []
        self.lock = asyncio.Lock()
        self.stop = asyncio.Event()
        self.skip_index = skip_index
        self._maps_keys: set[str] = set()
        self._name_phone: set[tuple[str, str]] = set()

    def should_stop(self) -> bool:
        return self.stop.is_set()

    def _is_duplicate(self, lead: dict) -> bool:
        if self.skip_index and self.skip_index.has_lead(lead):
            return True
        maps_key = place_key(resolve_maps_url(lead))
        if maps_key and maps_key in self._maps_keys:
            return True
        name = normalize_name(lead.get("name", ""))
        phone = normalize_phone(lead.get("phone", ""))
        return bool(name and (name, phone) in self._name_phone)

    def _remember(self, lead: dict) -> None:
        maps_key = place_key(resolve_maps_url(lead))
        if maps_key:
            self._maps_keys.add(maps_key)
        name = normalize_name(lead.get("name", ""))
        phone = normalize_phone(lead.get("phone", ""))
        if name:
            self._name_phone.add((name, phone))
        if self.skip_index:
            self.skip_index.register_lead(lead)

    async def try_add(self, lead: dict) -> bool:
        """Add lead if under cap. Returns False when scrapers should stop."""
        if self.stop.is_set():
            return False

        async with self.lock:
            if self.stop.is_set():
                return False
            if self._is_duplicate(lead):
                return False

            if len(self.leads) >= self.cap:
                self.stop.set()
                print(
                    f"GLOBAL CAP {self.cap} reached — signalling all scrapers to stop",
                    flush=True,
                )
                return False

            self.leads.append(lead)
            self._remember(lead)

            if len(self.leads) >= self.cap:
                self.stop.set()
                print(
                    f"GLOBAL CAP {self.cap} reached ({len(self.leads)} qualified) — stopping all scrapers",
                    flush=True,
                )
            return True

    async def count(self) -> int:
        async with self.lock:
            return len(self.leads)
