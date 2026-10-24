"""Acceptance checks: control blocks whose body holds only comments compile."""
import os
import sys

_WORK = os.environ.get("GRADE_WORKDIR")
if _WORK and _WORK not in sys.path:
    sys.path.insert(0, _WORK)

import pytest  # noqa: E402

from mako.template import Template  # noqa: E402

CASES = {
    "elif_comment_then_else": (
        "% if a:\nA\n% elif b:\n## later\n% else:\nC\n% endif\n",
        {"a": False, "b": True},
        "",
    ),
    "elif_comment_then_elif": (
        "% if a:\nA\n% elif b:\n## later\n% elif c:\nC\n% endif\n",
        {"a": False, "b": False, "c": True},
        "C",
    ),
    "two_comment_lines_in_middle": (
        "% if a:\nA\n% elif b:\n## one\n## two\n% else:\nC\n% endif\n",
        {"a": False, "b": False},
        "C",
    ),
    "all_branches_comments": (
        "% if a:\n## x\n% elif b:\n## y\n% else:\n## z\n% endif\n",
        {"a": False, "b": False},
        "",
    ),
    "middle_comment_in_for_body": (
        "% for i in items:\n% if i == 1:\none\n% elif i == 2:\n## two later\n% else:\nmany\n% endif\n% endfor\n",
        {"items": [1, 2, 3]},
        "one\nmany",
    ),
    "if_comment_only": ("% if a:\n## x\n% endif\nend\n", {"a": True}, "end"),
    "else_comment_only": ("% if a:\nA\n% else:\n## x\n% endif\nend\n", {"a": False}, "end"),
    "truly_empty_middle": ("% if a:\nA\n% elif b:\n% else:\nC\n% endif\n", {"a": False, "b": True}, ""),
    "text_middle": ("% if a:\nA\n% elif b:\nB\n% else:\nC\n% endif\n", {"a": False, "b": True}, "B"),
    "doc_block_middle": (
        "% if a:\nA\n% elif b:\n<%doc>\n  multi-line\n  note\n</%doc>\n% else:\nC\n% endif\n",
        {"a": False, "b": True},
        "",
    ),
    "for_else_comment": ("% for i in items:\n${i}\n% else:\n## none\n% endfor\nend\n", {"items": []}, "end"),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_comment_only_branches_compile_and_render(name):
    source, args, expected = CASES[name]
    assert Template(source).render(**args).strip() == expected
