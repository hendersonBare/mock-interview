# KEY_BUGS: rep_bug_squash_mako_3bugs (sqlalchemy/mako rel_1_3_12, commit d4d1639)

Three fixed plants in unrelated subsystems (no pool, no reroll). Line numbers refer to the
practice repo. Each bug has two failing visible tests: one new scenario test in
`test/test_template_scenarios.py` and one upstream regression test that already guarded that
behaviour (agreed with the user: faithful plants, 6 failing tests instead of 3).

| id | subsystem | file:line | failing visible tests |
|---|---|---|---|
| A `a_lambda_params` | Python-to-source regeneration | `mako/_ast_util.py:527` (missing method, between `visit_NameConstant` and `visit_Str`) | `test/test_ast.py::AstParseTest::test_expr_generate`, `test/test_template_scenarios.py::test_def_with_lambda_default_argument_renders` |
| B `b_lookup_directories` | template lookup | `mako/lookup.py:250` | `test/test_lookup.py::LookupTest::test_directory_lookup`, `test/test_template_scenarios.py::test_lookup_falls_through_to_next_directory_when_name_is_a_folder` |
| C `c_comment_only_branch` | control-block code generation | `mako/codegen.py:858` | `test/test_template.py::ControlTest::test_commented_blank_control_4`, `test/test_template_scenarios.py::test_control_block_containing_only_a_comment_compiles` |

Suggested order under time pressure: B (one frame from the symptom, 5 min), A (10-15 min), C
(the slowest, because the generated module has to be read).

---

## A: `ast.arg` has no visitor, so lambda parameters vanish

- **Planted diff** (`patches/a_lambda_params.patch`):
  ```diff
       def visit_NameConstant(self, node):
           self.write(str(node.value))

  -    def visit_arg(self, node):
  -        self.write(node.arg)
  -
       def visit_Str(self, node):
  ```
- **Minimal fix:** put the three lines back.
- **Root cause (ast node dispatch):** `SourceGenerator` is a `NodeVisitor`. `visit()` looks up
  `"visit_" + type(node).__name__` and, if there is no such method, falls back to
  `generic_visit()`, which only recurses into child AST nodes. An `ast.arg` has a string field
  `arg` and no AST children, so the fallback writes nothing. `signature()` (line 248) calls
  `self.visit(arg)` for every positional parameter, so `lambda item: item.name` regenerates as
  `lambda : item.name`. `*args`/`**kw` still work because `signature()` writes
  `node.vararg.arg` directly instead of visiting.
- **Why it compiles but fails at render:** Mako regenerates `<%def>` argument defaults with
  `pyparser.ExpressionGenerator` (`mako/ast.py:186`, `FunctionDecl.get_argument_expressions`).
  The generated module contains `def render_names(context,people,key=lambda : person.name):`.
  That is valid Python: a zero-argument lambda whose body refers to a global `person`. The call
  `key(p)` then raises `TypeError: <lambda>() takes 0 positional arguments but 1 was given`.
- **Localization path:**
  1. `pytest -q test/test_template_scenarios.py::test_def_with_lambda_default_argument_renders`
     gives the TypeError. The upstream `test_expr_generate` failure shows
     `'repr(lambda , : (x + y))' != 'repr(lambda x, y: (x + y))'`, which already points at
     regeneration.
  2. Look at the generated code: `print(Template(src).code)` shows `key=lambda : person.name`.
  3. Compare the AST with the regenerated text:
     `ast.dump(ast.parse("lambda item: item.name", mode="eval").body)` shows
     `arguments(args=[arg(arg='item')])`, while
     `pyparser.ExpressionGenerator(pyparser.parse("lambda item: item.name")).value()` returns
     `'lambda : item.name'`.
  4. Follow `visit_Lambda` -> `signature` -> `self.visit(arg)`. `grep -n "def visit_" mako/_ast_util.py`
     shows a visitor for nearly every node class but none for `arg`.
- **Regression tests:** `hidden_tests/test_hidden_p1_lambda_defaults.py`. The parametrized
  `ast.dump` round trip covers 1 arg, 2 args, a default, nested lambdas and `*args/**kw` (the
  last one is a neighbour that passes on both builds). Also def default as a key, as a sort key,
  two params plus a default, and `"lambda item: item.name" in Template(...).code`, with plain
  defaults as a neighbour.

## B: lookup accepts any existing path, including directories

- **Planted diff** (`patches/b_lookup_directories.patch`):
  ```diff
  -                if os.path.isfile(srcfile):
  +                if os.path.exists(srcfile):
                       return self._load(srcfile, uri)
  ```
- **Minimal fix:** `exists` back to `isfile`.
- **Root cause (filesystem checks):** `os.path.exists` is true for directories, so the first
  search directory containing a *folder* with the template's name wins. `_load()` builds a
  `Template(filename=...)`, and `open()` on a directory raises `IsADirectoryError`, which escapes
  from `get_template`. The loop never reaches the later directory that has the real file, and a
  folder-only hit no longer turns into `TopLevelLookupException` through the `for ... else`.
  `isfile` follows symlinks: a link to a file is accepted, links to folders and broken links are
  skipped.
- **Localization path:** the traceback goes `get_template` -> `_load` -> `Template.__init__` ->
  `util.read_file` -> `open`. Walk up two frames (`pytest -x --pdb`, then `u`) to the loop in
  `TemplateLookup.get_template` and `p srcfile, os.path.isdir(srcfile)`. The upstream test
  `test_directory_lookup` has a docstring that states the contract ("hitting an existent
  directory still raises LookupError").
- **Regression tests:** `hidden_tests/test_hidden_p1_lookup_directories.py`: folder shadowing a
  later file (plain, leading slash, nested path), folder-only raises
  `TopLevelLookupException`, `has_template` is False for a folder, symlink to a folder skipped.
  Neighbours that pass on both builds: missing everywhere, file in the first directory wins,
  symlink to a file found, broken symlink skipped.

## C: a branch that holds only a comment gets no `pass`

- **Planted diff** (`patches/c_comment_only_branch.patch`), in
  `_GenerateRenderMethod.visitControlLine`:
  ```diff
               if (
                   not children
  -                or all(
  -                    isinstance(c, (parsetree.Comment, parsetree.ControlLine))
  -                    for c in children
  -                )
  +                or all(isinstance(c, parsetree.ControlLine) for c in children)
                   and all(
                       (node.is_ternary(c.keyword) or c.isend)
  ```
- **Minimal fix:** put `parsetree.Comment` back into the `isinstance` tuple.
- **Root cause (when generated code needs `pass`):** each `% if/elif/else` line becomes a Python
  compound statement header in the generated module. `## comment` lines produce no Python code
  (`Comment` nodes are skipped by the code generator), so a branch whose template body is only
  comments has an empty Python suite, and Python needs a `pass` there. `visitControlLine` inserts
  `pass` when (1) the branch has no children, or (2) all children are comments/control lines and
  every control-line child is a ternary or the end tag, or (3) the first non-comment child is a
  control line (`_search_for_control_line`). The lexer gives a *middle* ternary branch only the
  nodes up to the next ternary, so `% elif b:` + `## later` + `% else:` has children `[Comment]`.
  Rule (3) finds no control line there, so only rule (2) can insert the `pass`, and with
  `Comment` removed from the tuple it no longer does. The module then contains
  `elif b:` directly followed by `else:` and fails with
  `IndentationError: expected an indented block after 'elif' statement` (an `IndentationError`
  is a `SyntaxError`). First and last branches still get their `pass` through rule (3) (their
  children end with a control line), which is why `% if x:` / `## c` / `% endif` and the `else`
  variant still compile. Text bodies emit `__M_writer(...)`, and truly empty branches hit rule (1).
- **Localization path:**
  1. The new test fails only on the `elif` variant (the assert message names the variant).
     The upstream `test_commented_blank_control_4` (`if/##/elif/##/else/##`) fails the same way,
     while `_1`, `_2` and `_3` pass. The difference is the comment-only *middle* branch.
  2. Compile the three body variants side by side: comment-only vs text vs empty middle branch.
     Only the comment-only one fails.
  3. Read the generated module. `Template(src).code` is not available when compilation fails,
     so use the code generator directly:
     ```python
     from mako import codegen, lexer
     node = lexer.Lexer(src).parse()
     print(codegen.compile(node, uri="x", filename=None, default_filters=["str"],
           buffer_filters=[], imports=None, future_imports=None, source_encoding=None,
           generate_magic_comment=False, strict_undefined=False, enable_loop=True,
           reserved_names=frozenset()))
     ```
     It shows `elif b:` immediately followed by `else:`, with no `pass`.
  4. `grep -n '"pass"' mako/codegen.py` leads to `visitControlLine`. Print `children` for the
     elif node: `[Comment]`. Evaluate the condition by hand.
- **Regression tests:** `hidden_tests/test_hidden_p1_comment_branches.py`: comment-only middle
  branch before `else` and before `elif`, two comment lines, all branches comments, inside a
  `% for`. Neighbours that pass on both builds: if/else comment-only, truly empty middle, text
  middle, a multi-line `<%doc>` middle (the newline after `</%doc>` is text, so it never needed a
  `pass`), `for/else` with a comment-only else.

---

## Visible test summary (practice repo)

517 selected (3 Pygments-version tests deselected in `setup.cfg`), 6 failing, 511 passing,
0 skipped. After `reference.patch`: 517 passed. Hidden: 32 cases in 3 files; 19 fail on the
practice repo, all 32 pass after the fix.
