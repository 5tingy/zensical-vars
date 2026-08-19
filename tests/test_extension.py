"""Tests for the Markdown extension itself."""

from __future__ import annotations

import re

import markdown
import pytest

import zensical_vars

# The extension stack a Zensical or Material project typically runs.
THEME_STACK = [
    "pymdownx.superfences",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "attr_list",
    "md_in_html",
    "admonition",
    "tables",
    "toc",
]


def render(source: str, stack: list[str] | None = None, **config: object) -> str:
    md = markdown.Markdown(
        extensions=[*(stack or []), "zensical_vars"],
        extension_configs={"zensical_vars": config} if config else {},
    )
    return md.convert(source)


def block(body: str) -> str:
    return f"```zvars\n{body}\n```\n"


# -- substitution ---------------------------------------------------------


def test_reference_in_prose_renders_the_default():
    html = render(block("host: 192.168.1.1") + "\nReach it at <<host>>.")
    assert 'data-zv-var="host"' in html
    assert 'data-zv-default="192.168.1.1"' in html
    assert "192.168.1.1</span>" in html


def test_reference_survives_syntax_highlighting():
    html = render(
        block("host: 192.168.1.1") + "\n```bash\nssh me@<<host>>\n```",
        stack=["fenced_code", "codehilite"],
    )
    # The span must land inside the highlighted block, not next to it.
    highlighted = html[html.index("<pre") : html.index("</pre>")]
    assert 'data-zv-var="host"' in highlighted


@pytest.mark.parametrize("stack", [["fenced_code", "codehilite"], THEME_STACK])
def test_reference_works_across_fence_implementations(stack):
    page = block("host: 1.2.3.4") + "\n```python\nconnect('<<host>>')\n```"
    html = render(page, stack)
    assert html.count('data-zv-var="host"') == 1


def test_reference_in_inline_code():
    html = render(block("host: 1.2.3.4") + "\nRun `ssh <<host>>`.")
    assert "<code>ssh <span" in html


def test_reference_in_an_attribute_falls_back_to_plain_text():
    html = render(block("host: 1.2.3.4") + "\n[admin](http://<<host>>/)")
    assert 'href="http://1.2.3.4/"' in html
    assert "<span" not in html[html.index("<a ") : html.index("</a>")]


def test_multiple_references_share_one_field():
    html = render(block("host: 1.2.3.4") + "\n<<host>> and <<host>> again.")
    assert html.count('data-zv-var="host"') == 2


# -- passthrough ----------------------------------------------------------


def test_escaped_reference_is_literal():
    html = render(block("host: 1.2.3.4") + "\nA literal \\<<host>>.")
    assert "&lt;&lt;host&gt;&gt;" in html
    assert "zv-var" not in html.split("literal")[1]


def test_undeclared_reference_is_left_alone():
    html = render(block("host: 1.2.3.4") + "\nUnknown <<nope>>.")
    assert "&lt;&lt;nope&gt;&gt;" in html


def test_stream_operators_pass_through_untouched():
    html = render(block("host: 1.2.3.4") + "\nUse `std::cout << value >> other`.")
    assert "std::cout &lt;&lt; value &gt;&gt; other" in html


def test_page_without_a_block_is_untouched():
    html = render("Nothing here, just `a << b` and <<c>>.")
    assert "zv-var" not in html


# -- output hygiene -------------------------------------------------------


def test_no_styles_or_scripts_are_emitted():
    """Anything in the body leaks into the page title and search index."""
    html = render(block("host: 1.2.3.4") + "\n<<host>>")
    assert "<style" not in html
    assert "<script" not in html


def test_state_does_not_leak_between_documents():
    md = markdown.Markdown(extensions=["zensical_vars"])
    md.convert(block("host: 1.2.3.4") + "\n<<host>>")
    md.reset()
    assert "zv-var" not in md.convert("A later page with <<host>> in it.")


def test_state_is_isolated_without_an_explicit_reset():
    md = markdown.Markdown(extensions=["zensical_vars"])
    md.convert(block("host: 1.2.3.4") + "\n<<host>>")
    assert "zv-var" not in md.convert("A later page with <<host>> in it.")


# -- declaration shapes ---------------------------------------------------


def test_shorthand_mapping():
    html = render(block("host: 1.2.3.4\nuser: me") + "\n<<host>> <<user>>")
    assert html.count("data-zv-var=") == 2


def test_list_of_field_definitions():
    html = render(
        block("- name: host\n  label: Server\n  default: 1.2.3.4") + "\n<<host>>"
    )
    assert ">Server</label>" in html


def test_fields_key_with_panel_options():
    declaration = block("title: Custom heading\nfields:\n  host: 1.2.3.4")
    html = render(declaration + "\n<<host>>")
    assert "Custom heading" in html


def test_malformed_block_is_skipped_without_crashing():
    html = render("```zvars\n: : not yaml : :\n```\n\nAfter.")
    assert "After." in html


def test_invalid_field_name_is_skipped():
    html = render(block("- name: 9bad\n  default: x") + "\nText.")
    assert "zv-panel" not in html


# -- fields ---------------------------------------------------------------


def test_default_renders_as_placeholder_not_value():
    """So a reader types over it instead of deleting it first."""
    html = render(block("host: 1.2.3.4") + "\n<<host>>")
    field = re.search(r"<input[^>]*>", html).group(0)
    assert 'placeholder="1.2.3.4"' in field
    assert "value=" not in field
    assert 'data-zv-default="1.2.3.4"' in field


def test_options_render_a_select_with_the_default_selected():
    declaration = block("- name: shell\n  default: zsh\n  options: [bash, zsh]")
    html = render(declaration + "\n<<shell>>")
    assert "<select" in html
    assert 'value="zsh" selected' in html


def test_input_type_is_restricted_to_an_allowlist():
    html = render(block("- name: n\n  default: 1\n  type: exploit") + "\n<<n>>")
    assert 'type="text"' in html


def test_help_text_is_associated_with_its_input():
    html = render(block("- name: host\n  default: x\n  help: Some help") + "\n<<host>>")
    described = re.search(r'aria-describedby="([^"]+)"', html).group(1)
    assert f'id="{described}"' in html


# -- panel ----------------------------------------------------------------


def test_panel_is_a_theme_admonition():
    html = render(block("host: x") + "\n<<host>>")
    assert '<div class="admonition example zv-panel"' in html
    assert '<p class="admonition-title">' in html


def test_type_selects_the_admonition_kind():
    html = render(block("type: tip\nfields:\n  host: x") + "\n<<host>>")
    assert "admonition tip zv-panel" in html


def test_card_style_only_adds_a_class():
    plain = render(block("host: x") + "\n<<host>>")
    card = render(block("style: card\nfields:\n  host: x") + "\n<<host>>")
    assert plain.replace("example zv-panel", "example zv-panel zv-panel--card") == card


def test_collapsible_emits_details():
    html = render(block("collapsible: true\nfields:\n  host: x") + "\n<<host>>")
    assert html.startswith('<details class="example zv-panel" open')
    assert "<summary>" in html


def test_collapsible_can_start_closed():
    declaration = block("collapsible: true\nopen: false\nfields:\n  host: x")
    html = render(declaration + "\n<<host>>")
    assert " open " not in html


def test_panel_false_declares_without_rendering():
    html = render(block("panel: false\nfields:\n  host: 1.2.3.4") + "\n<<host>>")
    assert "zv-panel" not in html
    assert "1.2.3.4" in html


def test_form_is_accepted_as_an_alias_for_panel():
    html = render(block("form: false\nfields:\n  host: 1.2.3.4") + "\n<<host>>")
    assert "zv-panel" not in html


def test_note_becomes_a_tooltip_and_can_be_hidden():
    assert "zv-tip__bubble" in render(block("host: x") + "\n<<host>>")
    assert "zv-tip" not in render(block("host: x") + "\n<<host>>", note="")


def test_reset_button_starts_disabled():
    html = render(block("host: x") + "\n<<host>>")
    assert "data-zv-reset disabled" in html


# -- configuration --------------------------------------------------------


def test_config_defaults_can_be_set_globally():
    html = render(block("host: x") + "\n<<host>>", type="warning", collapsible=True)
    assert '<details class="warning zv-panel"' in html


def test_block_options_override_configuration():
    declaration = block("type: note\nfields:\n  host: x")
    html = render(declaration + "\n<<host>>", type="warning")
    assert "admonition note zv-panel" in html


def test_custom_delimiters():
    html = render(block("host: 1.2.3.4") + "\nReach {{host}}.", start="{{", end="}}")
    assert 'data-zv-var="host"' in html


def test_custom_block_name():
    html = render("```vars\nhost: 1.2.3.4\n```\n\n<<host>>", block="vars")
    assert 'data-zv-var="host"' in html


def test_storage_and_persistence_reach_the_markup():
    html = render(block("host: x") + "\n<<host>>", persist=False, storage_key="k")
    assert 'data-zv-persist="false"' in html
    assert 'data-zv-storage="k"' in html


# -- escaping -------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        'default: \'"><script>alert(1)</script>\'',
        "label: '<b>bold</b>'",
        "help: '\"quoted\"'",
    ],
)
def test_untrusted_field_values_are_escaped(field):
    html = render(block(f"- name: host\n  {field}") + "\n<<host>>")
    assert "<script>" not in html
    assert "<b>" not in html


def test_title_and_note_are_escaped():
    html = render(block("host: x") + "\n<<host>>", title="<b>x</b>", note='say "hi"')
    assert "<b>x</b>" not in html
    assert "&quot;hi&quot;" in html


# -- package ---------------------------------------------------------------


def test_assets_are_bundled_and_non_empty():
    for name in zensical_vars.ASSETS:
        assert zensical_vars.asset_path(name).read_text().strip()


def test_asset_path_rejects_unknown_names():
    with pytest.raises(ValueError):
        zensical_vars.asset_path("../secrets")
