"""The grid, the keyed criteria and the choice→model mapping."""

from __future__ import annotations

from grid import DEFAULT_GRID, Entry, criteria, parse_entry, parse_grid, resolve


def test_default_grid_is_the_two_benchmarked_models():
    ids = [entry.model_id for entry in DEFAULT_GRID]
    assert ids == [
        "openrouter/auto",
        "typesafe/jev-router",
    ]


def test_criteria_are_keyed_by_position_with_a_readable_profile():
    mapping = criteria(DEFAULT_GRID)
    assert set(mapping) == {"1", "2"}
    assert mapping["1"].startswith("openrouter/auto: ")
    assert mapping["1"] == (
        "openrouter/auto: the usual choice for general work: everyday writing, "
        "explanation, summarising, ordinary coding and tool use; routed for you by OpenRouter; "
        "cheap for its size"
    )
    assert mapping["2"].startswith("typesafe/jev-router: ")


def test_no_profile_is_a_task_free_superlative():
    """Every criterion must name a task family, not just praise the model.

    This is the rule the GLM under-routing came from: "excellent value for money" and
    "excellent in real use for everyday tasks" attached no task to the praise, so they read as
    safe picks on every prompt and the first-listed model absorbed the GLMs' decisions. See the
    changelog measurement.
    """
    banned = ("excellent", "top-tier", "best-in-class", "state of the art", "powerful")
    for entry in DEFAULT_GRID:
        lowered = entry.description.lower()
        for word in banned:
            assert word not in lowered, f"{entry.model_id} praises without naming a task: {word}"


def test_resolve_by_positional_key():
    assert resolve({}, "2", DEFAULT_GRID).model_id == "typesafe/jev-router"


def test_resolve_tolerates_an_echoed_option_string():
    # A decision endpoint that echoes "2: typesafe/jev-router: ..." must not misroute.
    assert resolve({}, "2: typesafe/jev-router: deep and hard work", DEFAULT_GRID).model_id == (
        "typesafe/jev-router"
    )
    assert resolve({}, "typesafe/jev-router", DEFAULT_GRID).model_id == "typesafe/jev-router"


def test_resolve_rejects_an_off_grid_choice():
    assert resolve({}, "9", DEFAULT_GRID) is None
    assert resolve({}, "gpt-9-ultra", DEFAULT_GRID) is None
    assert resolve({}, "", DEFAULT_GRID) is None
    assert resolve({}, None, DEFAULT_GRID) is None


def test_parse_entry_accepts_string_and_mapping():
    assert parse_entry("a-model: does a thing") == Entry("a-model", "does a thing")
    assert parse_entry("bare-model") == Entry("bare-model", "")
    assert parse_entry({"model_id": "m1", "description": "d1"}) == Entry("m1", "d1")
    assert parse_entry("") is None
    assert parse_entry(None) is None


def test_parse_grid_falls_back_to_default_on_nonsense():
    assert parse_grid(None) == DEFAULT_GRID
    assert parse_grid([]) == DEFAULT_GRID
    assert parse_grid([""]) == DEFAULT_GRID
    assert parse_grid("   \n  ") == DEFAULT_GRID
    assert parse_grid(42) == DEFAULT_GRID


def test_parse_grid_honours_an_override_and_dedupes():
    grid = parse_grid(["alpha: first", "beta: second", "alpha: duplicate"])
    assert [entry.model_id for entry in grid] == ["alpha", "beta"]


def test_parse_grid_accepts_a_multiline_string():
    grid = parse_grid("alpha: first\nbeta: second")
    assert [entry.model_id for entry in grid] == ["alpha", "beta"]
