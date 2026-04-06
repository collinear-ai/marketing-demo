"""
Reusable predicate helpers for verifiers.

These are deliberately small, composable functions. A verifier method should
read like: "filter the actions, then assert properties via these predicates."

All helpers are side-effect free. None of them construct VerifierResult — that
is the verifier's job, so the same predicate can power boolean, checklist, or
threshold checks.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Iterable

from gym_core.schema import Action, ActionType
from gym_core.persona import Persona


# ---------------------------------------------------------------------------
# semantic action-type sets
# ---------------------------------------------------------------------------
#
# These frozensets collapse enum-level variations into the *semantic* category
# a verifier author usually means. When a verifier wants "email to Samira,"
# it almost never means "specifically ActionType.EMAIL and not
# ActionType.ENCRYPTED_EMAIL" — those are delivery-mechanism details, not
# semantic categories. Filter via these sets to avoid false-negative bugs.

EMAIL_LIKE: frozenset[ActionType] = frozenset({
    ActionType.EMAIL,
    ActionType.ENCRYPTED_EMAIL,
    ActionType.EMAIL_REPLY,
    ActionType.EMAIL_FORWARD,
})

MESSAGE_LIKE: frozenset[ActionType] = frozenset({
    ActionType.SLACK_MESSAGE,
    ActionType.TEAMS_MESSAGE,
    ActionType.SMS,
})

DOCUMENT_LIKE: frozenset[ActionType] = frozenset({
    ActionType.DOCUMENT_CREATE,
    ActionType.DOCUMENT_EDIT,
    ActionType.NOTION_PAGE,
    ActionType.CONFLUENCE_PAGE,
    ActionType.WIKI_EDIT,
})

APPROVAL_LIKE: frozenset[ActionType] = frozenset({
    ActionType.APPROVAL_REQUEST,
    ActionType.APPROVAL_GRANT,
    ActionType.APPROVAL_REJECT,
})


# ---------------------------------------------------------------------------
# basic filtering
# ---------------------------------------------------------------------------

def actions_to(
    actions: Iterable[Action],
    recipient: str,
    action_type: ActionType | Iterable[ActionType] | None = None,
    channel: str | None = None,
) -> list[Action]:
    """Return actions addressed to ``recipient`` (as to/cc/bcc).

    ``action_type`` accepts:
      - ``None`` — any type
      - a single ``ActionType`` — exact match (backward compatible)
      - a set/frozenset/tuple/list of ``ActionType`` — membership match.
        Prefer the pre-built semantic sets ``EMAIL_LIKE``, ``MESSAGE_LIKE``,
        ``DOCUMENT_LIKE``, ``APPROVAL_LIKE`` over hand-rolled filters.
    """
    want_types: set[ActionType] | None
    if action_type is None:
        want_types = None
    elif isinstance(action_type, ActionType):
        want_types = {action_type}
    else:
        want_types = set(action_type)

    out = []
    for a in actions:
        if a.recipient != recipient and recipient not in a.cc and recipient not in a.bcc:
            continue
        if want_types is not None and a.action_type not in want_types:
            continue
        if channel is not None and a.channel != channel:
            continue
        out.append(a)
    return out


def email_like_to(actions: Iterable[Action], recipient: str) -> list[Action]:
    """Sugar: all email-family actions to a recipient (EMAIL, ENCRYPTED_EMAIL,
    EMAIL_REPLY, EMAIL_FORWARD). Use this instead of ``actions_to(..., EMAIL)``
    unless you genuinely want to exclude encrypted mail."""
    return actions_to(actions, recipient, EMAIL_LIKE)


def message_like_to(actions: Iterable[Action], recipient: str) -> list[Action]:
    """Sugar: all chat-messaging-family actions to a recipient (Slack, Teams, SMS)."""
    return actions_to(actions, recipient, MESSAGE_LIKE)


def actions_of_type(actions: Iterable[Action], *types: ActionType) -> list[Action]:
    want = set(types)
    return [a for a in actions if a.action_type in want]


def actions_in_channel(actions: Iterable[Action], channel: str) -> list[Action]:
    return [a for a in actions if a.channel == channel]


def actions_touching(actions: Iterable[Action], persona_id: str) -> list[Action]:
    """Any action where this persona is recipient, cc, bcc, or attendee."""
    out = []
    for a in actions:
        if (
            a.recipient == persona_id
            or persona_id in a.cc
            or persona_id in a.bcc
            or persona_id in a.attendees
        ):
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# content checks
# ---------------------------------------------------------------------------

def body_has_all_keywords(
    actions: Iterable[Action],
    keyword_patterns: dict[str, list[str]],
) -> tuple[bool, list[str]]:
    """Return (all_present, missing_keys). Patterns are regex (case-insensitive)."""
    combined = " ".join(a.full_text_lower() for a in actions)
    missing = []
    for key, patterns in keyword_patterns.items():
        if not any(re.search(p, combined) for p in patterns):
            missing.append(key)
    return (len(missing) == 0, missing)


def body_contains_any(actions: Iterable[Action], patterns: list[str]) -> bool:
    combined = " ".join(a.full_text_lower() for a in actions)
    return any(re.search(p, combined) for p in patterns)


def body_contains_none(actions: Iterable[Action], patterns: list[str]) -> tuple[bool, list[str]]:
    """Return (clean, matched_patterns)."""
    combined = " ".join(a.full_text_lower() for a in actions)
    hits = [p for p in patterns if re.search(p, combined)]
    return (len(hits) == 0, hits)


# ---------------------------------------------------------------------------
# number matching (format-tolerant)
# ---------------------------------------------------------------------------

# Matches a currency/number token such as "18.7", "$18.7M", "18,700,805",
# "$18,700,805.42", "3M", "3 million". Captures the numeric core for
# normalization; suffix handling (M/million/K) is done by the caller.
_NUMBER_TOKEN_RE = re.compile(
    r"""
    \$?                                 # optional $
    (?P<num>
        \d{1,3}(?:,\d{3})+(?:\.\d+)?    # comma-grouped (e.g. 18,700,805)
        | \d+(?:\.\d+)?                 # plain (e.g. 18.7, 4200050, 3)
    )
    \s*
    (?P<suffix>
        million|mm|[mk]\b               # scale suffix
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _token_to_float(raw_num: str, suffix: str | None) -> float | None:
    try:
        val = float(raw_num.replace(",", ""))
    except ValueError:
        return None
    if suffix:
        s = suffix.lower()
        if s in ("m", "mm", "million"):
            val *= 1_000_000
        elif s == "k":
            val *= 1_000
    return val


def _extract_number_tokens(text: str) -> list[tuple[str, float]]:
    """Return list of (raw_digit_string_without_commas, canonical_float)."""
    out: list[tuple[str, float]] = []
    for m in _NUMBER_TOKEN_RE.finditer(text):
        raw = m.group("num")
        suffix = m.group("suffix")
        val = _token_to_float(raw, suffix)
        if val is None:
            continue
        digits = raw.replace(",", "")
        out.append((digits, val))
    return out


def number_in_text(needle: str, text: str, rel_tol: float = 0.01) -> bool:
    """Check whether ``needle`` (a short numeric string like "18.7" or "3")
    appears in ``text``, tolerating common finance formatting.

    Match semantics:
      1. Plain substring fallback: "18.7" appears literally in "18.7 million".
      2. Scale-aware: interpret ``needle`` as a value and as a "millions"
         value; any number token in the text whose canonical value is within
         ``rel_tol`` of either interpretation counts as a match. So "18.7"
         matches "$18,700,805" (~18.7M) and "$18.7M", and "3" matches
         "$3,000,000", "$3.0M", or "3 million".
      3. Digit-prefix: if the needle's concatenated digits are a prefix of a
         comma-stripped number token in the text, it matches. So "187" would
         match "18700805"; "42" matches "4200050". Needle "3" is deliberately
         NOT treated as a prefix match - a single-digit prefix is almost
         always a false positive - it must hit via (1) or (2).

    Designed for verifying that an agent logged a key figure ("18.7",
    "14.5", "4.2", materiality "3") regardless of whether they wrote it as
    "$18.7M", "$18,700,805", or "18.7 million".
    """
    if not needle or not text:
        return False

    text_l = text.lower()
    needle_l = needle.strip().lower()

    # (1) literal substring, but only if the needle is "rich enough" that a
    # substring hit is unlikely to be a false positive. A bare single digit
    # like "3" must go through the numeric-token path below so that "302",
    # "ASC 330", "Q3", etc. don't spuriously satisfy it.
    needle_alnum = re.sub(r"[^0-9]", "", needle_l)
    if len(needle_alnum) >= 2 and needle_l in text_l:
        return True

    try:
        needle_val = float(needle_l.replace(",", ""))
    except ValueError:
        return False

    # Candidate interpretations of the needle. For small values (< 1000) the
    # needle is almost always shorthand for "<n> million" in finance text, so
    # we look for scaled matches AND small-value matches that carry an
    # explicit scale suffix (handled by the token extractor, which already
    # multiplies "3M"/"3 million" up to 3_000_000). We do NOT treat a bare
    # "3" token in the text as equivalent to the needle "3" — that would fire
    # on "Q3", "top 3", etc.
    needle_candidates: list[float]
    if needle_val < 1000:
        needle_candidates = [needle_val * 1_000_000]
    else:
        needle_candidates = [needle_val]

    # Needle digit form (no decimal, no commas) - used for prefix matching
    # on multi-digit needles only. A single-digit needle is too promiscuous.
    needle_digits = needle_l.replace(",", "").replace(".", "")
    allow_prefix = len(needle_digits) >= 2

    for digits, val in _extract_number_tokens(text):
        # (2) scale-aware numeric closeness
        for cand in needle_candidates:
            if cand == 0:
                if val == 0:
                    return True
                continue
            if abs(val - cand) / abs(cand) <= rel_tol:
                return True
        # (3) digit prefix match (multi-digit needles only)
        if allow_prefix and digits.startswith(needle_digits):
            return True

    return False


def any_action_has_number(actions: Iterable[Action], needle: str) -> bool:
    """Convenience wrapper: True iff ``number_in_text`` matches ``needle`` in
    any action's subject+body text (case-insensitive)."""
    for a in actions:
        text = f"{a.subject or ''} {a.body or ''}"
        if number_in_text(needle, text):
            return True
    return False


# ---------------------------------------------------------------------------
# attachment-aware bundling
# ---------------------------------------------------------------------------

def doc_bundle_text(
    cover: Action,
    all_actions: Iterable[Action],
) -> str:
    """Return the concatenated lowercased text of a cover email/message plus
    any ``DOCUMENT_CREATE`` / ``DOCUMENT_EDIT`` actions referenced in its
    ``attachments`` list, by filename match on the other action's subject.

    This closes the "attachment-blindness" bug class where an agent correctly
    produces a draft as a separate document_create action and attaches it to
    a cover email, but a verifier only scans the cover's body for required
    content — missing the content that actually lives in the draft.

    Matching is lenient: an attachment string matches a document if the
    attachment (case-insensitive) contains the document's subject or vice
    versa, or if either contains the other as a substring after stripping
    path segments and extensions.
    """
    parts: list[str] = []
    parts.append(cover.subject_lower())
    parts.append(cover.body_lower())

    if not cover.attachments:
        return " ".join(p for p in parts if p)

    all_list = list(all_actions)
    doc_actions = [a for a in all_list if a.action_type in DOCUMENT_LIKE]

    for att_ref in cover.attachments:
        ref = _normalize_attachment_ref(att_ref)
        if not ref:
            continue
        for doc in doc_actions:
            doc_title = (doc.subject or "").lower()
            doc_ref = _normalize_attachment_ref(doc_title)
            if not doc_ref:
                continue
            if ref in doc_ref or doc_ref in ref:
                parts.append(doc_title)
                parts.append(doc.body_lower())
                break

    return " ".join(p for p in parts if p)


def _normalize_attachment_ref(s: str) -> str:
    s = s.lower().strip()
    # Strip path, extension, and common punctuation
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    if "." in s:
        s = s.rsplit(".", 1)[0]
    s = re.sub(r"[\s\-_]+", " ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# negation-aware rationale / phrase checks
# ---------------------------------------------------------------------------

_NEGATION_MARKERS = (
    r"\bnot\b",
    r"\bno\b",
    r"\bnever\b",
    r"\bwithout\b",
    r"\bexcludes?\b",
    r"\bexcluding\b",
    r"\babsent\b",
    r"\bfree\s+of\b",
    r"\bavoid(?:s|ed|ing)?\b",
    r"\brather\s+than\b",
    # "kept/keep/keeping X out [entirely]" — the exact phrasing careful agents
    # use when asserting they omitted a topic: "I have kept performance/fit
    # language out entirely".
    r"\b(?:kept|keeps?|keeping)\b(?=[^.;!?\n]{0,80}\bout\b)",
    r"\bstrip(?:ped|ping|s)?\s+out\b",
    r"\bleft\s+out\b",
    r"\bomit(?:s|ted|ting)?\b",
)
_NEGATION_ALT = re.compile("(?:" + "|".join(_NEGATION_MARKERS) + ")", re.IGNORECASE)

# Clause boundaries — a negation before these doesn't carry past them.
_CLAUSE_BOUNDARY = re.compile(r"[.;!?\n]|\bbut\b|\bhowever\b|\byet\b", re.IGNORECASE)

# Post-phrase negation markers: cues that *follow* the phrase and still negate
# it. E.g. "kept performance/fit language out entirely" — the "out" (and the
# pre-phrase "kept") together mean the phrase is negated, but "out" only
# appears after the phrase, so clause-lookback alone misses it.
_POST_NEGATION_MARKERS = (
    r"\blanguage\s+out\b",
    r"\bout\s+entirely\b",
    r"\bout\s+of\s+(?:the\s+)?(?:letter|draft|email|communication|note)",
    r"\bis\s+not\s+(?:the|a)\b",
    r"\bwas\s+not\s+(?:the|a)\b",
)
_POST_NEGATION_ALT = re.compile("(?:" + "|".join(_POST_NEGATION_MARKERS) + ")", re.IGNORECASE)


def contains_affirmative_phrase(text: str, phrase: str) -> bool:
    """True iff ``phrase`` appears in ``text`` in an *affirmative* context —
    meaning it is not inside a clause that begins with a negation marker.

    Closes the "substring negation" bug class. A naive
    ``"performance" not in body`` fires on "not a performance issue" or
    "no performance / fit / pretext language" — the exact correct phrasing a
    careful agent uses to assert lawful rationale. This helper returns
    ``False`` for both cases (the phrase appears but in a negated clause) and
    ``True`` for "due to performance" (affirmative).

    Heuristic, not a parser. Uses clause-scoped lookback: for each occurrence
    of ``phrase``, walk backward to the last clause boundary and check if that
    clause contains a negation marker. If yes, the occurrence is negated.
    """
    text_l = text.lower()
    phrase_l = phrase.lower()
    pat = re.compile(rf"\b{re.escape(phrase_l)}\b")
    for m in pat.finditer(text_l):
        start = m.start()
        # Back up to the last clause boundary (period, semicolon, newline,
        # "but", "however", etc.) or the start of the text.
        window_start = max(0, start - 200)
        window = text_l[window_start:start]
        # Find last clause boundary in window; clause begins after it.
        boundary_matches = list(_CLAUSE_BOUNDARY.finditer(window))
        if boundary_matches:
            clause_start = boundary_matches[-1].end()
            clause = window[clause_start:]
        else:
            clause = window
        # Is there a negation marker anywhere in this clause before the phrase?
        if _NEGATION_ALT.search(clause):
            continue  # negated occurrence
        # Post-phrase check: look forward to the next clause boundary for
        # post-positioned negation cues like "language out entirely".
        end = m.end()
        forward_window = text_l[end:end + 200]
        fwd_boundary = _CLAUSE_BOUNDARY.search(forward_window)
        forward_clause = (
            forward_window[: fwd_boundary.start()] if fwd_boundary else forward_window
        )
        if _POST_NEGATION_ALT.search(forward_clause):
            continue  # negated by a trailing cue
        return True
    return False


def no_affirmative_phrase(text: str, phrases: Iterable[str]) -> tuple[bool, list[str]]:
    """Return ``(clean, hits)`` where ``clean`` is True iff none of ``phrases``
    appear affirmatively in ``text``. Preferred replacement for
    ``"<phrase>" not in body`` checks on rationale/reason phrasing."""
    hits = [p for p in phrases if contains_affirmative_phrase(text, p)]
    return (len(hits) == 0, hits)


def rationale_check(
    text: str,
    required_any: Iterable[str],
    forbidden_affirmative: Iterable[str] = (),
) -> tuple[bool, str]:
    """High-level check: does ``text`` cite at least one of the ``required_any``
    rationales AND avoid affirmatively citing any of the
    ``forbidden_affirmative`` rationales?

    Returns ``(passed, explanation)``.

    Example:
        rationale_check(
            email.body,
            required_any=["business", "freeze", "opex", "headcount"],
            forbidden_affirmative=["performance", "fit", "pretext"],
        )
        # passes on: "business-driven headcount freeze — not a performance issue"
        # fails on:  "we're letting him go due to performance concerns"
    """
    text_l = text.lower()
    has_required = any(re.search(rf"\b{re.escape(r.lower())}\b", text_l) for r in required_any)
    if not has_required:
        return (False, f"missing required rationale; wanted any of: {list(required_any)}")
    clean, hits = no_affirmative_phrase(text, forbidden_affirmative)
    if not clean:
        return (False, f"affirmative forbidden rationale found: {hits}")
    return (True, "ok")


def has_deadline_phrase(action: Action) -> bool:
    patterns = [
        r"by\s+(monday|tuesday|wednesday|thursday|friday|eod|end\s*of\s*day|cob)",
        r"by\s+\d{1,2}/\d{1,2}",
        r"deadline[:\s]",
        r"due\s*(by\s*)?\d",
        r"no\s*later\s*than",
        r"\d{1,2}(st|nd|rd|th)\b",
    ]
    text = action.full_text_lower()
    return any(re.search(p, text) for p in patterns)


def has_numbered_list(action: Action) -> bool:
    return bool(re.search(r"(?:^|\n)\s*\d+[\.\)]\s", action.body or ""))


# ---------------------------------------------------------------------------
# persona / channel preference
# ---------------------------------------------------------------------------

def used_preferred_channel(actions: Iterable[Action], persona: Persona) -> bool:
    """True if every action addressed at this persona used their preferred channel."""
    addressed = [a for a in actions if a.recipient == persona.id]
    if not addressed:
        return True  # nothing to violate
    pref = persona.preferred_channel
    if pref is None:
        return True
    ok_types = _channel_to_types(pref)
    return all(a.action_type in ok_types for a in addressed)


def did_not_use_banned_channel(
    actions: Iterable[Action],
    persona: Persona,
    topic_keywords: list[str] | None = None,
) -> list[Action]:
    """Return actions that violate the persona's banned-channel rules.
    If topic_keywords is provided, only flag violations whose body mentions
    one of those topics (e.g. security topics on Slack)."""
    bad_types: set[ActionType] = set()
    for banned in persona.banned_channels:
        bad_types |= _channel_to_types(banned)
    violations = []
    for a in actions:
        if a.recipient != persona.id:
            continue
        if a.action_type not in bad_types:
            continue
        if topic_keywords:
            text = a.full_text_lower()
            if not any(kw.lower() in text for kw in topic_keywords):
                continue
        violations.append(a)
    return violations


def _channel_to_types(channel: str) -> set[ActionType]:
    channel = channel.lower()
    if "slack" in channel:
        return {ActionType.SLACK_MESSAGE, ActionType.SLACK_REACTION}
    if "teams" in channel:
        return {ActionType.TEAMS_MESSAGE}
    if "encrypted" in channel:
        return {ActionType.ENCRYPTED_EMAIL}
    if "email" in channel or "outlook" in channel or "gmail" in channel:
        return {ActionType.EMAIL, ActionType.EMAIL_REPLY, ActionType.EMAIL_FORWARD, ActionType.ENCRYPTED_EMAIL}
    if "phone" in channel:
        return {ActionType.PHONE_CALL}
    if "sms" in channel:
        return {ActionType.SMS}
    return set()


# ---------------------------------------------------------------------------
# timing
# ---------------------------------------------------------------------------

def within_working_hours(action: Action, persona: Persona) -> bool:
    return persona.is_working_hour(action.timestamp)


def lead_time_hours(action: Action, deadline: datetime | None) -> float | None:
    if deadline is None:
        return None
    return (deadline - action.timestamp).total_seconds() / 3600


def meets_lead_time(action: Action, deadline: datetime | None, min_hours: float) -> bool:
    lt = lead_time_hours(action, deadline)
    return lt is not None and lt >= min_hours


def happens_before(earlier: Action | None, later: Action | None) -> bool:
    if earlier is None or later is None:
        return False
    return earlier.timestamp <= later.timestamp


def ordering_respected(
    actions: Iterable[Action],
    earlier_filter,  # callable: Action -> bool
    later_filter,    # callable: Action -> bool
) -> bool:
    earlier = [a for a in actions if earlier_filter(a)]
    later = [a for a in actions if later_filter(a)]
    if not earlier or not later:
        return False
    return min(a.timestamp for a in earlier) <= min(a.timestamp for a in later)


# ---------------------------------------------------------------------------
# compliance
# ---------------------------------------------------------------------------

PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",              # SSN
    r"\bMRN[:\s-]*\d{6,}\b",               # medical record number
    r"\bDOB[:\s-]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\bpatient\s+name[:\s]",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",              # SSN
    r"\b\d{16}\b",                          # credit card (naive)
    r"\b[\w\.-]+@[\w\.-]+\.\w+\b",         # email (contextual)
]

CREDENTIAL_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",                    # AWS access key
    r"(?i)(password|pwd|secret|token|api[_\s-]?key)\s*[:=]\s*\S+",
    r"-----BEGIN\s+(?:RSA\s+|OPENSSH\s+)?PRIVATE KEY-----",
    r"ghp_[A-Za-z0-9]{36}",                 # GitHub PAT
    r"xox[baprs]-[A-Za-z0-9-]+",           # Slack token
]


def contains_pattern(action: Action, patterns: list[str]) -> bool:
    text = (action.body or "") + " " + (action.subject or "")
    return any(re.search(p, text) for p in patterns)


def no_phi_in_channel(
    actions: Iterable[Action],
    forbidden_types: set[ActionType],
) -> list[Action]:
    """Return actions that leaked PHI in a forbidden channel."""
    violations = []
    for a in actions:
        if a.action_type not in forbidden_types:
            continue
        if a.contains_phi or contains_pattern(a, PHI_PATTERNS):
            violations.append(a)
    return violations


def no_credentials_anywhere(actions: Iterable[Action]) -> list[Action]:
    return [a for a in actions if contains_pattern(a, CREDENTIAL_PATTERNS)]


# ---------------------------------------------------------------------------
# attachments & artifacts
# ---------------------------------------------------------------------------

def has_attachment(action: Action, suffix: str | None = None) -> bool:
    if not action.attachments:
        return False
    if suffix is None:
        return True
    return any(a.lower().endswith(suffix.lower()) for a in action.attachments)


def attachment_count(actions: Iterable[Action]) -> int:
    return sum(len(a.attachments) for a in actions)


# ---------------------------------------------------------------------------
# approvals & sign-offs
# ---------------------------------------------------------------------------

def approval_received(actions: Iterable[Action], approver: str, topic: str | None = None) -> bool:
    for a in actions:
        if a.action_type != ActionType.APPROVAL_GRANT:
            continue
        if a.metadata.get("from") != approver and a.recipient != approver:
            continue
        if topic and topic.lower() not in a.full_text_lower():
            continue
        return True
    return False
