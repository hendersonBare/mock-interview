# Reported problems

Three reports from teams that use this copy of Mako. They came in separately
and touch different features. Each one has a minimal reproduction that uses
only the public API; run the snippets from the repository root with
`python snippet.py` (with the venv active).

## Report 1

**A def with a `lambda` default compiles, then blows up when it is called**

We have a helper def that takes an optional sort key. The template compiles
without complaint, but rendering fails as soon as the default key is used.

```python
from mako.template import Template


class Person:
    def __init__(self, name):
        self.name = name


t = Template(
    '<%def name="names(people, key=lambda person: person.name)">'
    '${", ".join(key(p) for p in people)}'
    "</%def>"
    "${names(people)}"
)
print(t.render(people=[Person("Ann"), Person("Bob")]))
```

Expected: `Ann, Bob`

Actual:
`TypeError: ...<lambda>() takes 0 positional arguments but 1 was given`

Passing the key explicitly (`${names(people, key=lambda p: p.name)}` inside
the template) works, and so does a default that is not a lambda, such as
`sep=", "`. Only the default lambda seems to lose track of its argument.

## Report 2

**Template lookup crashes when an earlier search directory has a folder with the template's name**

We give `TemplateLookup` two directories: a theme directory first, then the
built-in defaults. One theme happens to contain a *folder* called
`page.html` (an asset bundle). Instead of using `page.html` from the defaults
directory, the lookup crashes.

```python
import os
import tempfile

from mako.lookup import TemplateLookup

root = tempfile.mkdtemp()
themes = os.path.join(root, "themes")
defaults = os.path.join(root, "defaults")
os.makedirs(os.path.join(themes, "page.html"))
os.makedirs(defaults)
with open(os.path.join(defaults, "page.html"), "w") as fh:
    fh.write("default page")

lookup = TemplateLookup(directories=[themes, defaults])
print(lookup.get_template("page.html").render())
```

Expected: `default page`

Actual: `IsADirectoryError: [Errno 21] Is a directory: '.../themes/page.html'`

A name that exists in neither directory should keep raising Mako's own
`TopLevelLookupException`, as it does today.

## Report 3

**`SyntaxError` from a template whose `% elif` branch only holds a comment**

While a page is being redesigned we leave placeholder comments in some
branches. One of our templates no longer compiles:

```python
from mako.template import Template

t = Template(
    "% if show_footer:\n"
    "<footer>full</footer>\n"
    "% elif compact:\n"
    "## compact footer is not designed yet\n"
    "% else:\n"
    "<p>plain</p>\n"
    "% endif\n"
)
print(t.render(show_footer=False, compact=True))
```

Expected: an empty page (the `compact` branch has nothing to output yet).

Actual: compiling the template raises
`IndentationError: expected an indented block after 'elif' statement ...`
(Python's `SyntaxError` family), pointing into Mako's generated module.

Branches that contain text compile fine, and so does a branch that is
completely empty (no comment at all).
