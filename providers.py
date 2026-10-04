"""Provider profiles: the per-provider facts this router needs.

The router was benchmarked against one provider profile at a time. Rather than hardcode that
choice, every provider-specific fact lives here behind one name, and ``config.py`` selects a
profile with the ``provider`` setting:

* which Hermes provider profile (and aliases) the middleware acts on;
* the built-in routing grid those models belong to;
* how the chosen reasoning effort reaches the wire.

Adding a provider is therefore an edit to this module and nothing else — the decision client,
the audit trail, the memo and the fail-open logic are provider-agnostic and shared.

The **default profile is Ollama:Cloud**, which is the profile this plugin shipped with; OpenRouter
is an opt-in addition selected with ``provider: openrouter``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .grid import Entry

#: How a provider's chat-completions transport expects the chosen effort on the wire.
#:
#: ``REASONING_EFFORT`` — a top-level ``reasoning_effort`` kwarg (Ollama:Cloud's profile consumes
#: ``reasoning_config`` and emits only this field).
#: ``EXTRA_BODY_REASONING`` — a ``reasoning: {effort: ...}`` object nested inside ``extra_body``
#: (OpenRouter's transport builds it there). Writing the top-level field beside it produces
#: ``HTTP 400: "reasoning_effort" and "reasoning.effort" are both provided with conflicting
#: values``; writing a top-level ``reasoning`` produces ``Completions.create() got an unexpected
#: keyword argument 'reasoning'``. Both were live-failure regressions, both are covered by tests.
REASONING_EFFORT = "reasoning_effort"
EXTRA_BODY_REASONING = "extra_body_reasoning"


@dataclass(frozen=True)
class ProviderProfile:
    """Everything provider-specific, in one place."""

    #: Canonical Hermes provider profile name.
    name: str
    #: Other names that also count as this provider (never including ``name`` itself).
    aliases: Tuple[str, ...]
    #: Human label for status output.
    label: str
    #: API modes this provider's routed path uses.
    api_modes: Tuple[str, ...]
    #: Where the effort goes on the wire (one of the module constants above).
    effort_wire: str
    #: The env var holding the decision endpoint credential.
    api_key_env: str
    #: The built-in grid, in the order offered to Jev.
    grid: Tuple[Entry, ...]
    #: Fallback model used when a decision is below the confidence threshold.
    fallback_model: str
    #: Effort family for a model id this table does not otherwise recognise.
    default_family: str

    @property
    def names(self) -> Tuple[str, ...]:
        """Every name that selects this profile."""
        return (self.name, *self.aliases)


#: The Ollama:Cloud profile — the benchmarked six-model grid this plugin shipped with, and the
#: default. The descriptions are the criteria strings sent to Jev verbatim, in English.
OLLAMA_CLOUD = ProviderProfile(
    name="ollama-cloud",
    aliases=("ollama_cloud",),
    label="Ollama:Cloud",
    api_modes=("chat_completions",),
    effort_wire=REASONING_EFFORT,
    api_key_env="OPENROUTER_API_KEY",
    fallback_model="deepseek-v4.1-flash",
    default_family="ollama-cloud",
    grid=(
        Entry(
            "deepseek-v4.1-flash",
            "the usual choice for general work: everyday writing, explanation, summarising, "
            "ordinary coding and tool use; 1M context; cheap for its size",
        ),
        Entry(
            "kimi-k3",
            "strongest at complex code and long agentic tasks: multi-file refactors, deep "
            "debugging, large repositories; slow and the most expensive",
        ),
        Entry(
            "glm-5.3",
            "strongest at rigorous reasoning: mathematics, logic, science, quantitative and "
            "financial analysis, where a wrong answer is costly",
        ),
        Entry(
            "glm-5.3-flash",
            "best reasoning-per-cost on large text: drafting, summarising, translating and "
            "structured extraction over long documents; fast",
        ),
        Entry(
            "minimax-m3",
            "fast tool calling: long sequences of API/CLI actions, repetitive automation, "
            "high throughput",
        ),
        Entry(
            "nemotron-3-nano:30b",
            "highest throughput and lowest cost: trivial single-step requests only; weak at "
            "reasoning and at long context",
        ),
    ),
)

#: The OpenRouter profile — opt-in with ``provider: openrouter``. ``openrouter/auto`` is the
#: everyday route and ``typesafe/jev-router`` the deep route.
OPENROUTER = ProviderProfile(
    name="openrouter",
    aliases=("open_router",),
    label="OpenRouter",
    api_modes=("chat_completions",),
    effort_wire=EXTRA_BODY_REASONING,
    api_key_env="OPENROUTER_API_KEY",
    fallback_model="openrouter/auto",
    default_family="openrouter",
    grid=(
        Entry(
            "openrouter/auto",
            "the usual choice for general work: everyday writing, explanation, summarising, "
            "ordinary coding and tool use; routed for you by OpenRouter; cheap for its size",
        ),
        Entry(
            "typesafe/jev-router",
            "deep and hard work: rigorous reasoning, mathematics, logic, science, quantitative "
            "and financial analysis, complex code and long agentic tasks where a wrong answer "
            "is costly; slow and the most expensive",
        ),
    ),
)

#: Every built-in profile, keyed by canonical name.
PROFILES: Dict[str, ProviderProfile] = {
    OLLAMA_CLOUD.name: OLLAMA_CLOUD,
    OPENROUTER.name: OPENROUTER,
}

#: The profile used when the ``provider`` setting is missing or unrecognised. Deliberately the
#: upstream default so an existing install is unchanged by this addition.
DEFAULT_PROVIDER = OLLAMA_CLOUD.name


def resolve_profile(name: str) -> ProviderProfile:
    """The profile for a configured name, or the default when it is not recognised."""
    wanted = (name or "").strip().lower().replace(" ", "-")
    if wanted in PROFILES:
        return PROFILES[wanted]
    for profile in PROFILES.values():
        if wanted in profile.names:
            return profile
    return PROFILES[DEFAULT_PROVIDER]


def profile_names() -> Tuple[str, ...]:
    """Every selectable provider name, for the config schema's ``choices``."""
    return tuple(PROFILES)
