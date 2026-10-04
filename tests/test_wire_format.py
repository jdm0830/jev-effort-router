"""Wire-format regressions for the OpenRouter route — the two live failures that killed turns.

Both bugs came from the fork's switch to OpenRouter, whose ``chat_completions`` transport builds
the reasoning config as a *nested* object inside ``extra_body`` (``extra_body["reasoning"]``) and
never as a top-level kwarg. The upstream code did the opposite:

1. it wrote a top-level ``reasoning_effort`` beside the transport's nested ``reasoning.effort``,
   so OpenRouter rejected the request with ``HTTP 400: "reasoning_effort" and "reasoning.effort"
   are both provided with conflicting values``;
2. it wrote ``reasoning`` at the top level, which is not a wire kwarg at all —
   ``Completions.create() got an unexpected keyword argument 'reasoning'``.

The fix merges the chosen effort into ``extra_body["reasoning"]["effort"]`` and drops any stale
top-level ``reasoning``/``reasoning_effort`` key. These tests pin that contract.
"""

from __future__ import annotations

from stubs import StubResponse, StubState, StubTransport, decision_payload, openrouter_request
from config import load_settings
from router import Router


def build(tmp_path, transport, config=None):
    settings = load_settings(lambda key, default=None: (config or {}).get(key, default))
    router = Router(
        lambda: settings,
        get_state=lambda: StubState(tmp_path),
        client_factory=lambda _settings: _ClientWith(transport, settings),
        catalog=_NoCatalog(),
    )
    return router, settings


class _NoCatalog:
    """No provider catalog evidence: routing tests never depend on it."""

    def is_known(self, model_id, provider_prefixes=()):
        return None


def _ClientWith(transport, settings):
    from client import JevClient

    return JevClient(settings, transport=transport)


def route(router, request=None, **overrides):
    kwargs = dict(
        turn_id="turn-1",
        session_id="session-1",
        platform="cli",
        model="openrouter/auto",
        provider="openrouter",
        api_mode="chat_completions",
        api_call_count=0,
        api_request_id="turn-1:api:0",
    )
    kwargs.update(overrides)
    request = request if request is not None else openrouter_request()
    return router.on_llm_request(request, dict(request), **kwargs)


def test_no_top_level_reasoning_effort_on_openrouter(tmp_path):
    """Regression: a top-level ``reasoning_effort`` conflicted with the transport's nested effort.

    OpenRouter answers two competing effort fields with
    ``HTTP 400: "reasoning_effort" and "reasoning.effort" are both provided with conflicting
    values``, so the routed request must not carry the top-level key at all.
    """
    transport = StubTransport([StubResponse(decision_payload("2", 0.9, "high", 0.8))])
    router, _ = build(tmp_path, transport)

    result = route(router)

    assert result is not None
    assert "reasoning_effort" not in result["request"]


def test_no_top_level_reasoning_key_on_openrouter(tmp_path):
    """Regression: a top-level ``reasoning`` kwarg raised
    ``Completions.create() got an unexpected keyword argument 'reasoning'``.

    The effort must instead live under ``extra_body["reasoning"]["effort"]``.
    """
    transport = StubTransport([StubResponse(decision_payload("2", 0.9, "high", 0.8))])
    router, _ = build(tmp_path, transport)

    result = route(router)

    assert "reasoning" not in result["request"]
    assert result["request"]["extra_body"]["reasoning"]["effort"] == "high"


def test_pre_existing_extra_body_is_preserved_and_effort_lands_there(tmp_path):
    """An ``extra_body`` the transport already built survives, with the effort merged in.

    The transport writes ``extra_body["reasoning"]`` (and may carry other keys); the router must
    keep the mapping and its other keys, not clobber it.
    """
    transport = StubTransport([StubResponse(decision_payload("2", 0.9, "high", 0.8))])
    router, _ = build(tmp_path, transport)
    request = openrouter_request(
        extra_body={"reasoning": {"enabled": True}, "provider": {"order": ["Anthropic"]}}
    )

    result = route(router, request)

    extra_body = result["request"]["extra_body"]
    assert extra_body["reasoning"]["effort"] == "high"
    # An explicit effort implies reasoning is on, so a stale disable is cleared.
    assert "enabled" not in extra_body["reasoning"]
    assert extra_body["provider"] == {"order": ["Anthropic"]}


def test_decision_without_effort_cleans_stale_keys(tmp_path):
    """No chosen effort => no effort on the wire, and stale nested/top-level keys are dropped."""
    transport = StubTransport(
        [StubResponse(decision_payload("1", 0.9, "medium", 0.9, include_effort=False))]
    )
    router, _ = build(tmp_path, transport)
    request = openrouter_request(
        extra_body={"reasoning": {"effort": "low", "enabled": True}}
    )
    # A stale top-level effort from an earlier provider must not survive either.
    request["reasoning_effort"] = "low"

    result = route(router, request)

    routed = result["request"]
    assert "reasoning_effort" not in routed
    # The stale nested effort is stripped; the unrelated ``enabled`` flag stays.
    assert "effort" not in routed["extra_body"]["reasoning"]
    assert routed["extra_body"]["reasoning"]["enabled"] is True
