"""End-to-end template scenarios taken from user reports.

Each test compiles and renders small templates the way an application would,
through the public Template / TemplateLookup API.
"""

import os

import pytest

from mako import exceptions
from mako.lookup import TemplateLookup
from mako.template import Template


class Person:
    def __init__(self, name):
        self.name = name


def test_def_with_lambda_default_argument_renders():
    template = Template(
        '<%def name="names(people, key=lambda person: person.name)">'
        '${", ".join(key(p) for p in people)}'
        "</%def>"
        "${names(people)}"
    )
    people = [Person("Ann"), Person("Bob")]
    assert template.render(people=people) == "Ann, Bob"


def test_lookup_falls_through_to_next_directory_when_name_is_a_folder(tmp_path):
    first = tmp_path / "themes"
    second = tmp_path / "defaults"
    (first / "page.html").mkdir(parents=True)
    second.mkdir()
    (second / "page.html").write_text("default page")

    lookup = TemplateLookup(directories=[os.fspath(first), os.fspath(second)])

    assert lookup.get_template("page.html").render() == "default page"
    with pytest.raises(exceptions.TopLevelLookupException):
        lookup.get_template("missing.html")


COMMENT_ONLY_BRANCHES = {
    "if": (
        "% if show_footer:\n"
        "## footer markup is not ready yet\n"
        "% endif\n"
        "done"
    ),
    "elif": (
        "% if show_footer:\n"
        "<footer>full</footer>\n"
        "% elif compact:\n"
        "## compact footer is not designed yet\n"
        "% else:\n"
        "<p>plain</p>\n"
        "% endif\n"
        "done"
    ),
    "else": (
        "% if show_footer:\n"
        "<footer>full</footer>\n"
        "% else:\n"
        "## nothing to show without a footer\n"
        "% endif\n"
        "done"
    ),
}


def test_control_block_containing_only_a_comment_compiles():
    for variant, source in COMMENT_ONLY_BRANCHES.items():
        template = Template(source)
        rendered = template.render(show_footer=False, compact=True).strip()
        assert rendered == "done", variant
