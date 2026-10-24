"""Acceptance checks: lambda parameters survive Python-to-source regeneration."""
import os
import sys

_WORK = os.environ.get("GRADE_WORKDIR")
if _WORK and _WORK not in sys.path:
    sys.path.insert(0, _WORK)

import ast  # noqa: E402

import pytest  # noqa: E402

import mako  # noqa: E402
from mako import pyparser  # noqa: E402
from mako.template import Template  # noqa: E402


class Person:
    def __init__(self, name):
        self.name = name


PEOPLE = [Person("Bob"), Person("Ann")]


def regenerate(code):
    return pyparser.ExpressionGenerator(pyparser.parse(code)).value()


def test_candidate_tree_is_imported():
    if _WORK:
        assert os.path.realpath(mako.__file__).startswith(os.path.realpath(_WORK))


@pytest.mark.parametrize(
    "code",
    [
        "lambda item: item.name",
        "lambda x, y: (x + y)",
        "lambda a, b=10: (a + b)",
        "lambda *args, **kw: (args, kw)",
        "lambda item: (lambda inner: inner + item)",
    ],
)
def test_lambda_round_trip_keeps_parameters(code):
    regenerated = regenerate(code)
    assert ast.dump(ast.parse(regenerated)) == ast.dump(ast.parse(code))


def test_def_default_lambda_single_parameter():
    t = Template(
        '<%def name="names(people, key=lambda person: person.name)">'
        '${",".join(key(p) for p in people)}</%def>${names(people)}'
    )
    assert t.render(people=PEOPLE) == "Bob,Ann"


def test_def_default_lambda_used_as_sort_key():
    t = Template(
        '<%def name="names(people, key=lambda p: p.name)">'
        '${",".join(p.name for p in sorted(people, key=key))}</%def>${names(people)}'
    )
    assert t.render(people=PEOPLE) == "Ann,Bob"


def test_def_default_lambda_two_parameters_and_default():
    t = Template(
        '<%def name="calc(x, op=lambda a, b=10: a + b)">${op(x)}|${op(x, 1)}</%def>'
        "${calc(2)}"
    )
    assert t.render() == "12|3"


def test_def_signature_regeneration_contains_parameter():
    t = Template('<%def name="f(key=lambda item: item.name)">x</%def>')
    assert "lambda item: item.name" in t.code


def test_plain_defaults_still_render():
    t = Template('<%def name="greet(name, punct=\'!\')">hi ${name}${punct}</%def>${greet("ann")}')
    assert t.render() == "hi ann!"
