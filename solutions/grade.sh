#!/usr/bin/env bash
# Grade a practice attempt with the hidden acceptance tests.
#
# Usage: ~/Desktop/Stripe/keys/grade.sh <problem_id> <part|all> [workdir]
#   part     grade parts 1..part cumulatively (hidden files test_hidden_p<k>_*.py),
#            or "all" for every hidden test file.
#   workdir  defaults to ~/Desktop/Stripe/scratch/<problem_id>
#
# Uses <workdir>/.venv/bin/python when present, else $STRIPE_PREP_PY, else
# ~/Desktop/Stripe/tools/.venv/bin/python, else python3. Hidden tests are copied to a temp
# dir (nothing is written into the keys folder or the workdir) and run with the workdir
# (and workdir/src) on PYTHONPATH. GRADE_WORKDIR is exported for tests that need data files.
# The candidate's own visible test suite is run afterwards for information.
set -uo pipefail
if [ $# -lt 2 ]; then echo "usage: $0 <problem_id> <part|all> [workdir]" >&2; exit 2; fi
KEYS="$(cd "$(dirname "$0")" && pwd)"
ID="$1"; PART="$2"; WORK="${3:-$HOME/Desktop/Stripe/scratch/$ID}"
K="$KEYS/$ID"; HT="$K/hidden_tests"
[ -d "$K" ] || { echo "unknown problem id: $ID" >&2; exit 2; }
[ -d "$HT" ] || { echo "no hidden tests for $ID" >&2; exit 2; }
[ -d "$WORK" ] || { echo "workdir not found: $WORK" >&2; exit 2; }
WORK="$(cd "$WORK" && pwd)"
if [ -x "$WORK/.venv/bin/python" ]; then PY="$WORK/.venv/bin/python"
elif [ -n "${STRIPE_PREP_PY:-}" ]; then PY="$STRIPE_PREP_PY"
elif [ -x "$HOME/Desktop/Stripe/tools/.venv/bin/python" ]; then PY="$HOME/Desktop/Stripe/tools/.venv/bin/python"
else PY=python3; fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/grade_${ID}.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
shopt -s nullglob
# helper modules and data dirs always come along
for f in "$HT"/*; do
  b="$(basename "$f")"
  case "$b" in test_hidden_*|__pycache__|.pytest_cache) continue ;; esac
  cp -R "$f" "$TMP/"
done
n=0
if [ "$PART" = "all" ]; then
  for f in "$HT"/test_hidden_*.py; do cp "$f" "$TMP/"; n=$((n+1)); done
else
  case "$PART" in ''|*[!0-9]*) echo "part must be a number or 'all'" >&2; exit 2 ;; esac
  p=1
  while [ "$p" -le "$PART" ]; do
    for f in "$HT"/test_hidden_p${p}_*.py; do cp "$f" "$TMP/"; n=$((n+1)); done
    p=$((p+1))
  done
fi
[ "$n" -gt 0 ] || { echo "no hidden test files selected for part '$PART'" >&2; exit 2; }

PP="$WORK"; [ -d "$WORK/src" ] && PP="$WORK/src:$PP"
echo "== $ID: hidden acceptance tests (part $PART, $n file(s)) against $WORK"
( cd "$WORK" && GRADE_WORKDIR="$WORK" PYTHONPATH="$PP${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 \
    "$PY" -m pytest -q -p no:cacheprovider -c /dev/null --rootdir "$TMP" "$TMP" ${GRADE_PYTEST_ARGS:-} )
HIDDEN=$?
if [ "${GRADE_SKIP_VISIBLE:-0}" != 1 ]; then
  echo "== $ID: visible test suite in workdir (informational)"
  ( cd "$WORK" && PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider ${GRADE_VISIBLE_ARGS:-} 2>&1 | tail -n 3 )
fi
if [ $HIDDEN -eq 0 ]; then echo "RESULT: PASS (hidden, part $PART)"; else echo "RESULT: FAIL (hidden, part $PART)"; fi
exit $HIDDEN
