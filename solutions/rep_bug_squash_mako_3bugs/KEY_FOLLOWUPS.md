# KEY_FOLLOWUPS: rep_bug_squash_mako_3bugs

## A: "What should a source generator do with an AST node it does not know?"

Two defensible choices; say which and why.

- **Fail loudly (preferred for a code generator).** Override `generic_visit` in
  `SourceGenerator` to raise `NotImplementedError(f"cannot regenerate {type(node).__name__}")`.
  Silent skipping is what made A dangerous: the output was still valid Python, just with
  different meaning, and nothing failed until render time. A loud error would have pointed at
  `arg` immediately. The cost is that a new Python release that adds node types (e.g. 3.12
  `TypeAlias`, 3.14 template strings) breaks templates that use them until a visitor is added.
  That is usually the right trade for a code generator.
- **Skip, but only for pure container nodes.** Keep the recursive fallback for nodes whose
  children carry all the text (e.g. `Expr`, `Module`), and raise for nodes with non-AST fields
  (`arg`, `alias`, `keyword` carry strings). A cheap guard is to raise in `generic_visit` when
  `node._fields` contains a non-AST, non-list value.
- Python's own `ast.unparse` (3.9+) covers every node. Replacing Mako's generator with it is a
  bigger change, but worth mentioning.
- Testing idea: a round-trip property test, `ast.dump(ast.parse(regen(src))) ==
  ast.dump(ast.parse(src))` over a corpus of expressions (or hypothesis-generated ones), catches
  every missing visitor.

## A: "Why did `*args, **kw` still work?"

`signature()` writes `node.vararg.arg` and `node.kwarg.arg` as strings instead of visiting the
`arg` nodes. Only positional parameters go through `self.visit(arg)`. Keyword-only and
positional-only parameters are not emitted by `signature()` at all, even upstream
(`lambda *, k: k` regenerates without `k`): a real upstream gap worth mentioning.

## B: "How would you reject template names that escape the search directories?"

`get_template("../../etc/passwd")` normalizes to a path outside the directory, because
`posixpath.normpath(posixpath.join(dir_, u))` happily walks up. Fix:

```python
root = os.path.realpath(dir_)
candidate = os.path.realpath(os.path.join(root, u))
if os.path.commonpath([root, candidate]) != root:
    continue            # or raise TopLevelLookupException
if os.path.isfile(candidate):
    return self._load(candidate, uri)
```

- Use `realpath` on both sides so symlinks cannot be used to escape (decide explicitly whether
  symlinks that point outside the root are allowed; some deployments rely on them).
- `commonpath` instead of `startswith`, because `/srv/tmpl-evil` starts with `/srv/tmpl`.
- Reject before touching the filesystem with `open`, and return the same not-found error for
  "outside" and "missing", so the lookup does not reveal which files exist.
- Mention the TOCTOU window between `isfile` and `open`. It is acceptable for templates, but the
  robust way is to open the file and handle `IsADirectoryError`/`FileNotFoundError`
  (`except OSError`) by continuing the loop.

## B: "isfile vs exists vs trying to open?"

`exists` is true for directories, sockets and FIFOs. `isfile` is true only for regular files
and follows symlinks. "Easier to ask forgiveness" (open and catch `OSError`) avoids a race but
needs care so a permission error is not silently treated as "not here". For a lookup that
falls through several directories, `isfile` plus a clear error on a failed open is the
readable choice.

## C: "Why does Python need `pass` at all, and could the generator avoid the special cases?"

A compound statement header (`if`, `elif`, `else`, `for`, `try`, `with`) must be followed by an
indented suite with at least one statement. Comments are not statements. Simpler, more robust
options than the four-case condition:

- Always emit `pass` after every control-line header. It is harmless when more statements
  follow, and it removes the whole class of problems, at the cost of slightly noisier generated
  code.
- Or decide per branch by asking "did this branch emit any statement?": track it in the printer
  and insert `pass` when the suite is closed.

## C: "What about `<%doc>` blocks?"

`<%doc>...</%doc>` is also a `Comment` node, but the newline after `</%doc>` is a `Text` node, so
the branch emits `__M_writer('\n')` and never needed a `pass`. `##` lines consume their own
newline, which is why only they produce truly code-free branches.
