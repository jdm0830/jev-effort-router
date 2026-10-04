"""The status tool's provider-catalog warning, driven through the host's call shape."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from catalog import ModelCatalog

ROOT = Path(__file__).resolve().parents[1]

#: The fork's real cache filename and flat ``id -> metadata`` shape (see ``catalog._model_ids``).
CACHE_FILENAME = "cache/openrouter_model_metadata.json"


def _load_plugin():
    name = "jev_effort_router_catalog_status_test"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _context(tmp_path, cache_path):
    from stubs import StubContext, StubState

    ctx = StubContext(config={}, state=StubState(tmp_path))
    _load_plugin().register(ctx)
    router = ctx.middleware["llm_request"].__self__
    router._catalog = ModelCatalog(cache_path)
    return ctx


def _write(tmp_path, models):
    path = tmp_path / CACHE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({model: {"name": model} for model in models}), encoding="utf-8")
    return path


def test_status_flags_grid_entries_the_provider_lacks(tmp_path):
    cache = _write(tmp_path, ["openrouter/auto"])
    ctx = _context(tmp_path, cache)

    payload = json.loads(ctx.tools["jev_effort_router_status"]["handler"]({"recent": 1}))

    assert "openrouter/auto" not in payload.get("grid_unavailable", [])
    assert "typesafe/jev-router" in payload["grid_unavailable"]


def test_status_is_silent_when_the_grid_is_healthy(tmp_path):
    from grid import DEFAULT_GRID

    cache = _write(tmp_path, [entry.model_id for entry in DEFAULT_GRID])
    ctx = _context(tmp_path, cache)

    payload = json.loads(ctx.tools["jev_effort_router_status"]["handler"]({}))

    assert "grid_unavailable" not in payload


def test_status_reports_nothing_without_a_catalog(tmp_path):
    """No evidence must not read as "every model is missing"."""
    ctx = _context(tmp_path, tmp_path / "absent.json")

    payload = json.loads(ctx.tools["jev_effort_router_status"]["handler"]({}))

    assert "grid_unavailable" not in payload


def test_status_still_works_when_the_router_has_no_catalog_hook(tmp_path):
    """A router double without ``grid_report`` must not break the status tool."""
    from tools import _status
    from config import load_settings

    class Bare:
        def tail(self, settings, limit=10):
            return []

        def count(self, settings):
            return 0

    payload = json.loads(_status(Bare(), load_settings(lambda _key, default=None: default)))

    assert payload["enabled"] is True
