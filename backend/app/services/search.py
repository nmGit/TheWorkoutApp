"""Fuzzy-ish name search, shared by every exercise-template search path (there's exactly one
right now -- ``GET /api/exercise-templates?q=`` -- used identically by the exercise library,
the exercise picker, and the "add exercise" flows in both the template editor and an active
workout; see docs/source/review.rst for why those were unified onto one implementation).

A plain substring match (the previous implementation,
``ExerciseTemplate.name.ilike(f"%{q}%")``) required the query to appear verbatim and in the
same word order -- "press bench" never matched "Bench Press", and a single mistyped letter
anywhere dropped the whole result. This instead:

- matches the query's words against the name's words independent of order ("press bench"
  does match "Bench Press"), each query word only needing to be a substring of some word in
  the name (so a partial word like "bar" still matches "Barbell"); and
- tolerates a typo in a word -- a bounded edit distance, allowing an adjacent-letter
  transposition as a single edit like a substitution or insert/delete -- when nothing above
  matched cleanly, so "bemch press" and "suqat" still find "Bench Press" and "Squat".

Results are scored, not just filtered, so the best matches can be shown first. The tiers are
deliberately non-overlapping (every fuzzy/typo match scores below every clean-word match,
which scores below any substring match) so a search can never rank a coincidental fuzzy hit
above an exercise that actually contains the words typed.
"""

import re

_WORD_RE = re.compile(r"[a-z0-9]+")

# Non-overlapping score bands -- sorting only ever compares these to each other (and to 0.0
# for "no match"), never reads them as an absolute measure of fit.
EXACT = 4.0
PREFIX = 3.5
SUBSTRING = 3.0
ALL_WORDS_CONTAINED = 2.5
TOKEN_TYPO_BASE = 1.0  # below ALL_WORDS_CONTAINED even at TOKEN_TYPO_BASE + TOKEN_TYPO_SCALE
TOKEN_TYPO_SCALE = 0.9

# A query word shorter than this must match exactly or as a substring, never fuzzily --
# typo tolerance on 1-2 letters matches almost anything by coincidence.
MIN_FUZZY_TOKEN_LEN = 3


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _max_typos(word: str) -> int:
    """How many character edits still count as "a typo" for a word this long -- short words
    tolerate fewer, so a fuzzy match stays meaningful rather than matching almost anything."""
    return max(1, len(word) // 5)


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance, allowing an adjacent-letter transposition (the common "typed two
    letters in the wrong order" typo, e.g. "suqat") to count as a single edit too, the same as
    a substitution or an insert/delete."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


def _closest_word(token: str, name_words: list[str]) -> tuple[int, str] | None:
    """The name word closest to `token`, as (edit distance, word) -- or None if every word is
    too different in length to possibly be within `token`'s typo budget (a cheap lower bound
    that skips the DP above entirely for words nowhere close)."""
    budget = _max_typos(token)
    best: tuple[int, str] | None = None
    for w in name_words:
        if abs(len(w) - len(token)) > budget:
            continue
        d = _edit_distance(token, w)
        if best is None or d < best[0]:
            best = (d, w)
    return best


def search_score(query: str, name: str) -> float:
    """How well `name` matches `query`; 0.0 means it doesn't match at all. A score is only
    meaningful compared against another call's result (for sorting) or against 0.0 (for
    filtering) -- never read as an absolute measure of fit."""
    q = query.strip().lower()
    if not q:
        return 1.0
    n = name.lower()
    if q == n:
        return EXACT
    if n.startswith(q):
        return PREFIX
    if q in n:
        return SUBSTRING

    tokens = q.split()
    name_words = _words(n)
    if name_words and all(any(t in w for w in name_words) for t in tokens):
        return ALL_WORDS_CONTAINED
    if not name_words:
        return 0.0

    # Every query word must have *some* close match in the name -- one unmatched word (not
    # just the overall "average") disqualifies it, so "press bench" doesn't fuzzily match a
    # name that only happens to contain "press".
    closeness = []
    for t in tokens:
        if len(t) < MIN_FUZZY_TOKEN_LEN:
            return 0.0
        found = _closest_word(t, name_words)
        if found is None or found[0] > _max_typos(t):
            return 0.0
        closeness.append(1 - found[0] / len(t))
    return TOKEN_TYPO_BASE + TOKEN_TYPO_SCALE * (sum(closeness) / len(closeness))


def fuzzy_rank(items, query: str, name_of=lambda item: item.name):
    """`items` ranked by how well `name_of(item)` matches `query`, best first, ties broken
    alphabetically. Items that don't match at all are dropped. A blank `query` returns
    `items` unchanged, in whatever order they were already in."""
    if not query or not query.strip():
        return list(items)
    scored = ((search_score(query, name_of(item)), item) for item in items)
    matched = [(score, item) for score, item in scored if score > 0]
    matched.sort(key=lambda pair: (-pair[0], name_of(pair[1]).lower()))
    return [item for _, item in matched]
