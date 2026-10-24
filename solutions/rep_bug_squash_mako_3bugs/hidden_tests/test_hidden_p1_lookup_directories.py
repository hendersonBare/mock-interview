"""Acceptance checks: lookup only accepts regular files and keeps searching."""
import os
import sys

_WORK = os.environ.get("GRADE_WORKDIR")
if _WORK and _WORK not in sys.path:
    sys.path.insert(0, _WORK)

import pytest  # noqa: E402

from mako import exceptions  # noqa: E402
from mako.lookup import TemplateLookup  # noqa: E402


@pytest.fixture
def dirs(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    return first, second


def lookup(*paths, **kw):
    return TemplateLookup(directories=[os.fspath(p) for p in paths], **kw)


def test_folder_in_first_directory_falls_through_to_file(dirs):
    first, second = dirs
    (first / "page.html").mkdir()
    (second / "page.html").write_text("from second")
    assert lookup(first, second).get_template("page.html").render() == "from second"


def test_folder_named_like_template_with_leading_slash(dirs):
    first, second = dirs
    (first / "page.html").mkdir()
    (second / "page.html").write_text("from second")
    assert lookup(first, second).get_template("/page.html").render() == "from second"


def test_nested_folder_shadowing(dirs):
    first, second = dirs
    (first / "mail" / "receipt.txt").mkdir(parents=True)
    (second / "mail").mkdir()
    (second / "mail" / "receipt.txt").write_text("receipt")
    assert lookup(first, second).get_template("mail/receipt.txt").render() == "receipt"


def test_folder_only_raises_lookup_error(dirs):
    first, second = dirs
    (first / "page.html").mkdir()
    with pytest.raises(exceptions.TopLevelLookupException):
        lookup(first, second).get_template("page.html")


def test_missing_everywhere_raises_lookup_error(dirs):
    with pytest.raises(exceptions.TopLevelLookupException):
        lookup(*dirs).get_template("missing.html")


def test_has_template_is_false_for_folder(dirs):
    first, second = dirs
    (first / "page.html").mkdir()
    assert lookup(first, second).has_template("page.html") is False


def test_file_in_first_directory_wins(dirs):
    first, second = dirs
    (first / "page.html").write_text("from first")
    (second / "page.html").write_text("from second")
    assert lookup(first, second).get_template("page.html").render() == "from first"


def test_symlink_to_file_is_found(dirs, tmp_path):
    first, second = dirs
    real = tmp_path / "real.html"
    real.write_text("linked")
    (first / "page.html").symlink_to(real)
    assert lookup(first, second).get_template("page.html").render() == "linked"


def test_symlink_to_folder_is_skipped(dirs, tmp_path):
    first, second = dirs
    folder = tmp_path / "assets"
    folder.mkdir()
    (first / "page.html").symlink_to(folder, target_is_directory=True)
    (second / "page.html").write_text("from second")
    assert lookup(first, second).get_template("page.html").render() == "from second"


def test_broken_symlink_is_skipped(dirs, tmp_path):
    first, second = dirs
    (first / "page.html").symlink_to(tmp_path / "does-not-exist.html")
    (second / "page.html").write_text("from second")
    assert lookup(first, second).get_template("page.html").render() == "from second"
