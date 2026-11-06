"""Tests for the public API of c4_from_yaml."""

from __future__ import annotations

import dataclasses

import pytest

from c4_from_yaml import (
    C4Error,
    Component,
    Container,
    Issue,
    Model,
    Person,
    Relation,
    System,
    __version__,
    load_model,
    render,
    validate_model,
)


def yml(*lines: str) -> str:
    """Join lines into a text with LF endings and one trailing newline."""
    return "\n".join(lines) + "\n"


def people_yaml(count: int) -> str:
    return "people:\n" + "".join(f"  - {{id: p{i}, name: P}}\n" for i in range(count))


CONTEXT_TEXT = "people:\n  - {id: u, name: User, description: Buys}\nsystems:\n  - {id: shop, name: Shop, description: Sells}\nrelations:\n  - {source: u, target: shop, label: Uses}\n"  # noqa: E501
CONTEXT_EXPECTED = 'C4Context\n    Person(u, "User", "Buys")\n    System(shop, "Shop", "Sells")\n    Rel(u, shop, "Uses")\n'  # noqa: E501

SHOP = yml(
    "systems:",
    "  - {id: shop, name: Shop, description: Sells}",
    "containers:",
    "  - {id: web, name: Web, description: UI, system: shop, technology: React}",
    "  - {id: db, name: DB, description: Data, system: shop, technology: Postgres}",
    "components:",
    "  - {id: api, name: API, description: Rest, container: web, technology: Python}",
    "relations:",
    "  - {source: api, target: db, label: Reads}",
    "  - {source: web, target: db, label: Writes}",
)

FULL = yml(
    "people:",
    "  - {id: u, name: User}",
    "  - {id: lonely, name: Lonely}",
    "systems:",
    "  - {id: shop, name: Shop}",
    "  - {id: pay, name: Pay, external: true}",
    "containers:",
    "  - {id: web, name: Web, system: shop, technology: React}",
    "  - {id: db, name: DB, system: shop}",
    "components:",
    "  - {id: api, name: API, container: web}",
    "  - {id: repo, name: Repo, container: db}",
    "relations:",
    "  - {source: u, target: web, label: Browses}",
    "  - {source: api, target: pay, label: Charges, technology: HTTPS}",
    "  - {source: u, target: shop, label: Uses}",
    "  - {source: api, target: web}",
    "  - {source: lonely, target: pay, label: Pings}",
)


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_context_acceptance() -> None:
    assert render(load_model(CONTEXT_TEXT), "context") == CONTEXT_EXPECTED


def test_container_acceptance() -> None:
    out = render(load_model(SHOP), "container", focus="shop")
    assert '    System_Boundary(shop, "Shop") {' in out
    rels = [line for line in out.splitlines() if "Rel(" in line]
    assert rels == ['    Rel(web, db, "Reads")']
    assert out == yml(
        "C4Container",
        '    System_Boundary(shop, "Shop") {',
        '        Container(web, "Web", "React", "UI")',
        '        Container(db, "DB", "Postgres", "Data")',
        "    }",
        '    Rel(web, db, "Reads")',
    )


def test_component_view_shows_sibling_container() -> None:
    out = render(load_model(SHOP), "component", focus="web")
    assert out == yml(
        "C4Component",
        '    Container(db, "DB", "Postgres", "Data")',
        '    Container_Boundary(web, "Web") {',
        '        Component(api, "API", "Python", "Rest")',
        "    }",
        '    Rel(api, db, "Reads")',
    )


def test_context_view_lifts_and_deduplicates() -> None:
    out = render(load_model(FULL), "context")
    assert out == yml(
        "C4Context",
        '    Person(u, "User", "")',
        '    Person(lonely, "Lonely", "")',
        '    System(shop, "Shop", "")',
        '    System_Ext(pay, "Pay", "")',
        '    Rel(u, shop, "Browses")',
        '    Rel(shop, pay, "Charges", "HTTPS")',
        '    Rel(lonely, pay, "Pings")',
    )


def test_container_view_shows_only_connected_elements() -> None:
    out = render(load_model(FULL), "container", focus="shop")
    assert out == yml(
        "C4Container",
        '    Person(u, "User", "")',
        '    System_Ext(pay, "Pay", "")',
        '    System_Boundary(shop, "Shop") {',
        '        Container(web, "Web", "React", "")',
        '        Container(db, "DB", "", "")',
        "    }",
        '    Rel(u, web, "Browses")',
        '    Rel(web, pay, "Charges", "HTTPS")',
    )
    assert "lonely" not in out


def test_component_view_with_external_system() -> None:
    out = render(load_model(FULL), "component", focus="web")
    assert out == yml(
        "C4Component",
        '    System_Ext(pay, "Pay", "")',
        '    Container_Boundary(web, "Web") {',
        '        Component(api, "API", "", "")',
        "    }",
        '    Rel(api, pay, "Charges", "HTTPS")',
    )


def test_component_view_without_relations() -> None:
    out = render(load_model(FULL), "component", focus="db")
    assert out == yml(
        "C4Component",
        '    Container_Boundary(db, "DB") {',
        '        Component(repo, "Repo", "", "")',
        "    }",
    )


def test_label_escaping() -> None:
    name = 'A "b"\r\n\tc'
    model = Model(people=(Person(id="u", name=name, description=""),))
    out = render(model, "context")
    assert out == yml("C4Context", '    Person(u, "A \'b\' c", "")')


def test_title_is_cleaned() -> None:
    assert render(Model(), "context", title="T") == "C4Context\n    title T\n"
    assert render(Model(), "context", title="A\nB") == "C4Context\n    title A B\n"


def test_empty_model() -> None:
    assert render(Model(), "context") == "C4Context\n"


def test_unlabelled_relation_and_unicode_names() -> None:
    model = Model(
        people=(Person("a", "Caf\u00e9 \u6771\u4eac"), Person("b", "B")),
        relations=(Relation("a", "b"),),
    )
    out = render(model, "context")
    assert out == yml(
        "C4Context",
        '    Person(a, "Caf\u00e9 \u6771\u4eac", "")',
        '    Person(b, "B", "")',
        '    Rel(a, b, "")',
    )


@pytest.mark.parametrize(
    ("view", "focus"),
    [
        ("container", None),
        ("component", None),
        ("container", "ghost"),
        ("container", "web"),
        ("component", "shop"),
        ("component", "ghost"),
        ("deployment", None),
    ],
)
def test_view_errors(view: str, focus: str | None) -> None:
    with pytest.raises(C4Error) as info:
        render(load_model(SHOP), view, focus=focus)  # type: ignore[arg-type]
    assert info.value.code == "view"


def test_container_view_of_empty_model_needs_known_focus() -> None:
    with pytest.raises(C4Error) as info:
        render(Model(), "container", focus="shop")
    assert info.value.code == "view"


def test_render_rejects_invalid_model() -> None:
    model = Model(people=(Person("u", "U"),), relations=(Relation("u", "ghost"),))
    with pytest.raises(C4Error) as info:
        render(model, "context")
    assert info.value.code == "structure"
    assert info.value.path == "relations[0].target"


@pytest.mark.parametrize("bad_id", ["u\n", "a b", "1a", "a)", ""])
def test_render_rejects_unsafe_ids(bad_id: str) -> None:
    with pytest.raises(C4Error) as info:
        render(Model(people=(Person(bad_id, "U"),)), "context")
    assert info.value.code == "structure"
    assert info.value.path == "people[0].id"


@pytest.mark.parametrize(
    "text",
    [
        "a: &x 1\nb: *x\n",
        "b: *x\n",
        yml("base: &b {id: u}", "people:", "  - <<: *b"),
        yml("a: &a [x]", "b: &b [*a, *a]"),
        yml("people:", "  - &p {id: u, name: U}"),
    ],
)
def test_anchors_and_aliases_are_forbidden(text: str) -> None:
    with pytest.raises(C4Error) as info:
        load_model(text)
    assert info.value.code == "alias_forbidden"


@pytest.mark.parametrize(
    "text",
    [
        "!!python/object:os.system {}",
        "a: [",
        "a: 1\n---\nb: 2\n",
        "a: \x00",
        "a: \ud800",
    ],
)
def test_yaml_syntax_errors(text: str) -> None:
    with pytest.raises(C4Error) as info:
        load_model(text)
    assert info.value.code == "yaml_syntax"


def test_size_limit_counts_utf8_bytes() -> None:
    with pytest.raises(C4Error) as info:
        load_model("x" * 11, max_bytes=10)
    assert info.value.code == "too_large"
    with pytest.raises(C4Error) as info2:
        load_model("\u00e9" * 5 + "a", max_bytes=10)
    assert info2.value.code == "too_large"
    with pytest.raises(C4Error) as info3:
        load_model("a" * 10, max_bytes=10)
    assert info3.value.code == "structure"


def test_quoted_text_with_indicators_loads_unchanged() -> None:
    flow = load_model('people:\n  - {id: u, name: "R&D *team*"}\n')
    assert flow.people[0].name == "R&D *team*"
    block = load_model(yml("people:", "  - id: u", "    name: R&D *team*"))
    assert block.people[0].name == "R&D *team*"


def test_depth_limit() -> None:
    ok = yml("people:", "  - {id: u, name: U}")
    assert load_model(ok, max_depth=3).people[0].id == "u"
    with pytest.raises(C4Error) as info:
        load_model(ok, max_depth=2)
    assert info.value.code == "too_large"
    with pytest.raises(C4Error) as info2:
        load_model("[" * 4 + "]" * 4, max_depth=3)
    assert info2.value.code == "too_large"
    with pytest.raises(C4Error) as info3:
        load_model(yml("people:", "  - {id: u, name: [x]}"), max_depth=3)
    assert info3.value.code == "too_large"


def test_extreme_nesting_is_rejected_without_recursion_error() -> None:
    with pytest.raises(C4Error) as info:
        load_model("[" * 5000 + "]" * 5000)
    assert info.value.code == "too_large"
    with pytest.raises(C4Error) as info2:
        load_model("[" * 2000 + "]" * 2000, max_depth=100_000)
    assert info2.value.code == "too_large"


def test_element_limit() -> None:
    assert len(load_model(people_yaml(3), max_elements=3).people) == 3
    with pytest.raises(C4Error) as info:
        load_model(people_yaml(4), max_elements=3)
    assert info.value.code == "too_large"
    mixed = yml("people:", "  - {id: a, name: A}", "  - {id: b, name: B}") + yml(
        "systems:",
        "  - {id: c, name: C}",
        "  - {id: d, name: D}",
    )
    with pytest.raises(C4Error) as info2:
        load_model(mixed, max_elements=3)
    assert info2.value.code == "too_large"


@pytest.mark.parametrize(
    ("text", "path"),
    [
        (yml("- a"), ""),
        (yml("bogus: 1"), "bogus"),
        (yml("people: 1"), "people"),
        (yml("people:", "  - x"), "people[0]"),
        (yml("people:", "  - {id: u}"), "people[0].name"),
        (yml("people:", "  - {id: u, name: U, color: red}"), "people[0].color"),
        (yml("people:", "  - {id: 1x, name: U}"), "people[0].id"),
        (yml("people:", '  - {id: "a b", name: U}'), "people[0].id"),
        (yml("people:", "  - {id: u, name: 5}"), "people[0].name"),
        (yml("systems:", "  - {id: s, name: S, external: maybe}"), "systems[0].external"),
        (yml("containers:", "  - {id: c, name: C}"), "containers[0].system"),
        (yml("components:", "  - {id: c, name: C, container: bad id}"), "components[0].container"),
        (yml("relations:", "  - {source: a}"), "relations[0].target"),
        (yml("relations:", "  - {source: a, target: b, technology: 5}"), "relations[0].technology"),
        (yml("relations:", "  - {source: a, target: b, label: [x]}"), "relations[0].label"),
    ],
)
def test_structure_errors_carry_the_path(text: str, path: str) -> None:
    with pytest.raises(C4Error) as info:
        load_model(text)
    assert info.value.code == "structure"
    assert info.value.path == path


def test_error_messages_quote_at_most_200_characters() -> None:
    with pytest.raises(C4Error) as info:
        load_model(yml("people:", "  - {id: u, name: U, " + "k" * 500 + ": 1}"))
    assert "k" * 201 not in str(info.value)
    assert len(str(info.value)) < 300
    assert len(info.value.path) < 300
    with pytest.raises(C4Error) as info2:
        load_model(yml("people:", "  - {id: " + "1" * 500 + ", name: U}"))
    assert "1" * 201 not in str(info2.value)


def test_empty_documents_load_as_empty_model() -> None:
    assert load_model("") == Model()
    assert load_model("# nothing\n") == Model()
    assert load_model("people:\n") == Model()


def test_non_text_input_is_rejected() -> None:
    with pytest.raises(C4Error) as info:
        load_model(b"people: []")  # type: ignore[arg-type]
    assert info.value.code == "structure"


def test_model_is_immutable() -> None:
    model = load_model(CONTEXT_TEXT)
    with pytest.raises(dataclasses.FrozenInstanceError):
        model.people = ()  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        model.people[0].name = "x"  # type: ignore[misc]
    issue = Issue("p", "unknown_ref", "m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        issue.path = "q"  # type: ignore[misc]


def test_loaded_fields() -> None:
    model = load_model(FULL)
    assert model.systems[1] == System("pay", "Pay", "", True)
    assert model.containers[0] == Container("web", "Web", "", "shop", "React")
    assert model.components[0] == Component("api", "API", "", "web", "")
    assert model.relations[1] == Relation("api", "pay", "Charges", "HTTPS")
    assert model.relations[3].technology is None


def test_validate_unknown_ref_path() -> None:
    text = yml(
        "people:",
        "  - {id: u, name: U}",
        "systems:",
        "  - {id: s, name: S}",
        "relations:",
        "  - {source: u, target: s}",
        "  - {source: s, target: u}",
        "  - {source: u, target: u}",
        "  - {source: u, target: ghost}",
    )
    issues = validate_model(load_model(text))
    assert len(issues) == 1
    assert issues[0].path == "relations[3].target"
    assert issues[0].code == "unknown_ref"
    assert "ghost" in issues[0].message


def test_validate_unknown_source() -> None:
    model = Model(people=(Person("u", "U"),), relations=(Relation("ghost", "u"),))
    issues = validate_model(model)
    assert [(i.path, i.code) for i in issues] == [("relations[0].source", "unknown_ref")]


def test_validate_valid_model_has_no_issues() -> None:
    assert validate_model(load_model(FULL)) == []
    assert validate_model(Model()) == []


def test_validate_duplicate_ids_one_issue_per_repeated_id() -> None:
    text = yml(
        "people:",
        "  - {id: u, name: U}",
        "  - {id: u, name: U2}",
        "systems:",
        "  - {id: x, name: X}",
        "  - {id: x, name: X2}",
        "  - {id: u, name: S}",
    )
    issues = validate_model(load_model(text))
    assert [i.code for i in issues] == ["duplicate_id", "duplicate_id"]
    assert [i.path for i in issues] == ["people[1].id", "systems[1].id"]


def test_validate_wrong_parent_and_unknown_parent() -> None:
    text = yml(
        "people:",
        "  - {id: u, name: U}",
        "systems:",
        "  - {id: s, name: S}",
        "containers:",
        "  - {id: c1, name: C1, system: u}",
        "  - {id: c2, name: C2, system: nope}",
        "components:",
        "  - {id: k1, name: K1, container: s}",
        "  - {id: k2, name: K2, container: nope}",
    )
    issues = validate_model(load_model(text))
    assert [(i.path, i.code) for i in issues] == [
        ("containers[0].system", "wrong_parent"),
        ("containers[1].system", "unknown_ref"),
        ("components[0].container", "wrong_parent"),
        ("components[1].container", "unknown_ref"),
    ]


def test_validate_external_with_children() -> None:
    text = yml(
        "systems:",
        "  - {id: s, name: S, external: true}",
        "  - {id: t, name: T, external: true}",
        "containers:",
        "  - {id: c1, name: C1, system: s}",
        "  - {id: c2, name: C2, system: s}",
    )
    issues = validate_model(load_model(text))
    assert [(i.path, i.code) for i in issues] == [("systems[0].external", "external_with_children")]
