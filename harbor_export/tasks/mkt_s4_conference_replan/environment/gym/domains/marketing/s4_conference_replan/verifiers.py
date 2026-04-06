"""
MKT-S4 — LumaSummit Vendor Replan + Keynote Reshuffle — Verifiers
==================================================================

Programmatic verifiers for the 10-task DAG. Every check id emitted here must
match a ``programmatic_checks[].id`` entry in ``rubrics.yaml``.

Scenario ground truth:
- Week: 2026-04-06 (Mon) through 2026-04-10 (Fri), anchor America/Chicago.
- Event: LumaSummit 2026-07-14 to 2026-07-16, Chicago. ~99 days out at Monday.
- Old keynote slot: Tue 2026-07-14 09:00 CT (Dr. Anita Deshpande) — CANCELLED.
- New keynote slot: Wed 2026-07-15 11:00 CT (same speaker).
- Defunct AV vendor: StagePro Events (Chapter 7 filed 2026-03-18).
- Candidate replacement AV vendors (external — not in persona pool):
    PrismStage Productions, Onstage Atlas, BrightDeck Events.
  Intended winner from the planted scoring: PrismStage Productions.
- External speakers (NOT in persona pool; referenced by last-name match in
  email subjects). Timezone + working window (weekday-only) per speaker:
    deshpande   America/Los_Angeles  07:30–18:00
    okonjo      America/Chicago      08:00–17:00
    marwick     Europe/London        08:30–17:30
    sutton      Europe/London        09:00–17:00
    patel       Asia/Kolkata         09:30–18:30
    lim         Asia/Singapore       09:00–18:00
- Margo Delacroix hard block: Tue 2026-04-07 13:00–17:00 America/Los_Angeles.
  No action touching Margo (recipient/cc/attendee) may land inside that block.
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from gym_core import (
    Action,
    ActionType,
    BaseTaskVerifier,
    ComplianceVerifier,
    PersonaPool,
    ScenarioVerifier,
    Severity,
    VerifierResult,
    predicates as P,
)


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

CT = ZoneInfo("America/Chicago")
PT = ZoneInfo("America/Los_Angeles")
ET = ZoneInfo("America/New_York")
LON = ZoneInfo("Europe/London")
IST = ZoneInfo("Asia/Kolkata")
SGT = ZoneInfo("Asia/Singapore")

WEEK_START = datetime(2026, 4, 6, 0, 0, tzinfo=CT)
WEEK_END = datetime(2026, 4, 10, 23, 59, tzinfo=CT)

# Margo's immovable board-prep block, Tuesday 2026-04-07 13:00–17:00 PT.
MARGO_BLOCK_START = datetime(2026, 4, 7, 13, 0, tzinfo=PT)
MARGO_BLOCK_END = datetime(2026, 4, 7, 17, 0, tzinfo=PT)

# Friday exec-briefing window: 2026-04-10 08:00–17:00 CT.
FRIDAY = datetime(2026, 4, 10, 0, 0, tzinfo=CT).date()

EVENT_DATE = datetime(2026, 7, 14, 9, 0, tzinfo=CT)

EMAIL_TYPES = {
    ActionType.EMAIL,
    ActionType.EMAIL_REPLY,
    ActionType.EMAIL_FORWARD,
    ActionType.ENCRYPTED_EMAIL,
}
MESSAGING_TYPES = EMAIL_TYPES | {
    ActionType.SLACK_MESSAGE,
    ActionType.TEAMS_MESSAGE,
    ActionType.SMS,
}

SPEAKER_WINDOWS = {
    # last-name substring -> (tz, start_time, end_time)
    "deshpande": (PT, time(7, 30), time(18, 0)),
    "okonjo": (CT, time(8, 0), time(17, 0)),
    "marwick": (LON, time(8, 30), time(17, 30)),
    "sutton": (LON, time(9, 0), time(17, 0)),
    "patel": (IST, time(9, 30), time(18, 30)),
    "lim": (SGT, time(9, 0), time(18, 0)),
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _to_tz(dt: datetime, tz: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CT)
    return dt.astimezone(tz)


def _in_window(dt: datetime, tz: ZoneInfo, start: time, end: time) -> bool:
    local = _to_tz(dt, tz)
    if local.weekday() >= 5:
        return False
    return start <= local.time() <= end


def _touches_margo(action: Action) -> bool:
    targets = {action.recipient, *action.cc, *action.bcc, *action.attendees}
    return "margo_delacroix" in targets


def _in_margo_block(dt: datetime) -> bool:
    return MARGO_BLOCK_START <= _to_tz(dt, PT) <= MARGO_BLOCK_END


def _text(action: Action) -> str:
    return ((action.subject or "") + "\n" + (action.body or "")).lower()


def _subject(action: Action) -> str:
    return (action.subject or "").lower()


def _first_email_to(actions, persona_id):
    hits = P.email_like_to(actions, persona_id)
    if not hits:
        # fall back to any email variant
        hits = [a for a in actions if a.recipient == persona_id and a.action_type in EMAIL_TYPES]
    return hits


# ---------------------------------------------------------------------------
# T1 — Week Kickoff + Recovery Plan
# ---------------------------------------------------------------------------

class T1_WeekKickoff(BaseTaskVerifier):
    task_id = "T1"

    def run_all(self):
        # T1_PC1 — recovery plan doc created
        docs = [
            a for a in self.actions
            if a.action_type == ActionType.DOCUMENT_CREATE
            and "lumasummit" in _subject(a) + _text(a)
        ]
        yield self.boolean(
            "T1_PC1", "recovery_plan_doc_created",
            passed=bool(docs),
            details=f"Found {len(docs)} LumaSummit doc(s).",
        )

        # T1_PC2 — kickoff email to Reggie
        reggie_emails = _first_email_to(self.actions, "reggie_okonkwo")
        # Narrow to plausible kickoff / plan emails
        kickoff = [
            a for a in reggie_emails
            if any(kw in _text(a) for kw in ("kickoff", "recovery plan", "week", "t-minus", "tminus", "t-99", "plan"))
        ]
        yield self.boolean(
            "T1_PC2", "kickoff_email_to_reggie",
            passed=bool(kickoff),
            details=f"{len(kickoff)} plausible kickoff email(s) to reggie_okonkwo.",
        )

        # T1_PC3 — Margo cc
        margo_cc = [a for a in kickoff if "margo_delacroix" in a.cc]
        yield self.boolean(
            "T1_PC3", "margo_cc",
            passed=bool(margo_cc),
            details=f"{len(margo_cc)} kickoff email(s) cc margo_delacroix.",
        )

        # T1_PC4 — checklist: stagepro + tminus + two fronts
        combined = " ".join(_text(a) for a in kickoff)
        missing = []
        if "stagepro" not in combined:
            missing.append("stagepro_reference")
        if not re.search(r"t[-\s]?(minus\s*)?\d{2,3}", combined):
            missing.append("tminus_countdown")
        if not (
            ("av" in combined or "vendor" in combined)
            and ("keynote" in combined or "speaker" in combined)
        ):
            missing.append("two_fronts_named")
        yield self.checklist(
            "T1_PC4", "stagepro_and_countdown_cited",
            missing=missing, total=3,
        )

        # T1_PC5 — kickoff NOT in Margo's Tue PT block
        in_block = [a for a in kickoff if _in_margo_block(a.timestamp)]
        yield self.result(
            "T1_PC5", "not_in_margo_board_block",
            passed=not in_block,
            details=(
                f"{len(in_block)} kickoff email(s) land inside Margo's Tue 13:00–17:00 PT block."
                if in_block else "Kickoff clean of Margo's board block."
            ),
            compliance_relevant=True,
        )


# ---------------------------------------------------------------------------
# T2 — Formal Procurement Request
# ---------------------------------------------------------------------------

class T2_ProcurementRequest(BaseTaskVerifier):
    task_id = "T2"

    def run_all(self):
        reqs = [a for a in self.actions if a.action_type == ActionType.PROCUREMENT_REQUEST]

        yield self.boolean(
            "T2_PC1", "procurement_request_filed",
            passed=bool(reqs),
            details=f"{len(reqs)} procurement_request action(s).",
        )

        combined = " ".join(_text(a) for a in reqs)
        missing = []
        if "prismstage" not in combined:
            missing.append("prismstage")
        if "onstage atlas" not in combined and "onstage_atlas" not in combined:
            missing.append("onstage_atlas")
        if "brightdeck" not in combined:
            missing.append("brightdeck")
        yield self.checklist(
            "T2_PC2", "three_vendors_named",
            missing=missing, total=3,
        )

        # T2_PC3 — scope brief attached or referenced
        scope_ok = False
        for a in reqs:
            if a.attachments and any("scope" in x.lower() or "brief" in x.lower() or "sow" in x.lower() for x in a.attachments):
                scope_ok = True
                break
            if any(kw in _text(a) for kw in ("scope brief", "stage, lighting", "rigging", "show-calling", "show calling")):
                scope_ok = True
                break
        yield self.boolean(
            "T2_PC3", "scope_brief_attached",
            passed=scope_ok,
            details="Scope brief attached/referenced." if scope_ok else "No scope brief attached or referenced.",
        )

        # T2_PC4 — bid deadline ≤ Fri 04-10 17:00 CT
        deadline_ok = False
        for a in reqs:
            # read deadline from metadata or body text
            deadline = a.metadata.get("bid_due")
            if isinstance(deadline, datetime):
                if _to_tz(deadline, CT) <= datetime(2026, 4, 10, 17, 0, tzinfo=CT):
                    deadline_ok = True
                    break
            body = _text(a)
            if re.search(r"(04[-/]10|april\s*10|friday).{0,40}(17:00|5\s*pm|17:00\s*ct)", body):
                deadline_ok = True
                break
            if "04-10 17:00" in body or "2026-04-10 17:00" in body:
                deadline_ok = True
                break
        yield self.result(
            "T2_PC4", "bid_deadline_set",
            passed=deadline_ok,
            details="Bid deadline set to Fri 04-10 17:00 CT or earlier." if deadline_ok else "No compliant bid deadline found.",
        )

        # T2_PC5 — amount band $300–450K
        band_ok = False
        for a in reqs:
            if a.amount is not None and 300_000 <= a.amount <= 450_000:
                band_ok = True
                break
            body = _text(a)
            if re.search(r"\$?(3[0-9]{2}|4[0-4][0-9])[k,\s]?(000)?", body):
                # heuristic; anything 300k-449k
                band_ok = True
                break
        yield self.result(
            "T2_PC5", "amount_band_populated",
            passed=band_ok,
            details="Amount band within $300–450K." if band_ok else "Amount band not populated in expected range.",
        )


# ---------------------------------------------------------------------------
# T3 — Speaker Roster Audit + Keynote Reslot
# ---------------------------------------------------------------------------

class T3_RosterReslot(BaseTaskVerifier):
    task_id = "T3"

    def run_all(self):
        roster_actions = [
            a for a in self.actions
            if a.action_type in (ActionType.SPREADSHEET_EDIT, ActionType.SPREADSHEET_CREATE,
                                 ActionType.DOCUMENT_CREATE, ActionType.DOCUMENT_EDIT)
            and any(kw in _text(a) for kw in ("roster", "speaker", "keynote"))
        ]
        yield self.boolean(
            "T3_PC1", "roster_artifact_updated",
            passed=bool(roster_actions),
            details=f"{len(roster_actions)} roster-adjacent artifact action(s).",
        )

        # T3_PC2 — Wed 11:00 CT explicitly recorded
        combined = " ".join(_text(a) for a in roster_actions)
        wed_ok = bool(
            re.search(r"(wednesday|wed)\b.{0,30}11:?00", combined)
            or re.search(r"11:?00\s*(am\s*)?ct.{0,30}(wednesday|wed)", combined)
        )
        yield self.boolean(
            "T3_PC2", "wed_1100_anchor_named",
            passed=wed_ok,
            details="Wed 11:00 CT anchor recorded." if wed_ok else "Wed 11:00 CT anchor not found in roster artifacts.",
        )

        # T3_PC3 — priyanka consulted (any action touching her before T4 would fire)
        priyanka_touch = [
            a for a in self.actions
            if (a.recipient == "priyanka_shah" or "priyanka_shah" in a.cc or "priyanka_shah" in a.attendees)
            and any(kw in _text(a) for kw in ("tutor 3", "keynote", "wed", "wednesday", "collision", "collide"))
        ]
        yield self.boolean(
            "T3_PC3", "priyanka_consulted",
            passed=bool(priyanka_touch),
            details=f"{len(priyanka_touch)} Priyanka consult touchpoint(s).",
        )

        # T3_PC4 — no action asserts Tuesday 9:00 CT is still keynote after any T3 roster action
        if roster_actions:
            latest_t3 = max(a.timestamp for a in roster_actions)
            assert_old = [
                a for a in self.actions
                if a.timestamp > latest_t3
                and re.search(r"tuesday.{0,20}(09:?00|9:?00)\s*am?\s*ct", _text(a))
                and "keynote" in _text(a)
            ]
            passed = not assert_old
            details = (
                "No stale Tuesday 9:00 CT keynote assertion after roster update."
                if passed else f"{len(assert_old)} stale Tuesday 9:00 CT keynote assertion(s) found."
            )
        else:
            passed = False
            details = "No roster update to compare against."
        yield self.result(
            "T3_PC4", "old_tuesday_slot_retired",
            passed=passed,
            details=details,
        )


# ---------------------------------------------------------------------------
# T4 — Dr. Deshpande Keynote Confirmation (PT window)
# ---------------------------------------------------------------------------

class T4_DeshpandeComms(BaseTaskVerifier):
    task_id = "T4"

    def run_all(self):
        # Identify emails whose subject/body names Deshpande
        emails = [
            a for a in self.actions
            if a.action_type in EMAIL_TYPES
            and "deshpande" in _text(a)
        ]
        yield self.boolean(
            "T4_PC1", "deshpande_email_exists",
            passed=bool(emails),
            details=f"{len(emails)} email(s) naming Deshpande.",
        )

        # T4_PC2 — inside PT working hours weekday 07:30–18:00
        in_window = [a for a in emails if _in_window(a.timestamp, PT, time(7, 30), time(18, 0))]
        yield self.result(
            "T4_PC2", "in_pt_working_hours",
            passed=bool(in_window),
            details=f"{len(in_window)}/{len(emails)} Deshpande email(s) inside PT working hours.",
        )

        # T4_PC3 — dual timezone + Wednesday + 11:00
        combined = " ".join(_text(a) for a in emails)
        missing = []
        if " pt" not in combined and "pacific" not in combined and "pt)" not in combined:
            missing.append("pt_string")
        if " ct" not in combined and "central" not in combined and "ct)" not in combined:
            missing.append("ct_string")
        if "wednesday" not in combined and "wed" not in combined:
            missing.append("wednesday_word")
        if "11:00" not in combined and "11 am" not in combined and "11am" not in combined:
            missing.append("eleven_oclock")
        yield self.checklist(
            "T4_PC3", "dual_timezone_cited",
            missing=missing, total=4,
        )

        # T4_PC4 — sean_o_riordain routed
        sean_ok = any(
            "sean_o_riordain" in a.cc
            or a.metadata.get("drafted_by") == "sean_o_riordain"
            or a.metadata.get("sender_proxy") == "sean_o_riordain"
            or a.recipient == "sean_o_riordain"
            for a in emails
        )
        yield self.boolean(
            "T4_PC4", "sean_agency_routing",
            passed=sean_ok,
            details="Whitefield routing present." if sean_ok else "No Sean/Whitefield routing on Deshpande comms.",
        )


# ---------------------------------------------------------------------------
# T5 — Five Remaining Speaker Comms — each in own tz
# ---------------------------------------------------------------------------

class T5_SpeakerGauntlet(BaseTaskVerifier):
    task_id = "T5"

    def run_all(self):
        actions = [a for a in self.actions if a.action_type in EMAIL_TYPES]

        def emails_for(token):
            return [a for a in actions if token in _text(a)]

        found_map = {}
        for token in ("okonjo", "marwick", "sutton", "patel", "lim"):
            found_map[token] = emails_for(token)

        missing_speakers = [k for k, v in found_map.items() if not v]
        yield self.checklist(
            "T5_PC1", "five_speaker_emails_exist",
            missing=missing_speakers, total=5,
        )

        # Per-speaker window checks (explicit per-speaker calls so the lint
        # AST extractor can see each check_id as a string literal).
        def _win_result(token, tz, start, end):
            emails = found_map[token]
            if not emails:
                return False, f"No {token} emails to evaluate."
            in_win = [a for a in emails if _in_window(a.timestamp, tz, start, end)]
            passed = len(in_win) == len(emails)
            return passed, f"{len(in_win)}/{len(emails)} {token} email(s) inside {tz.key} {start}-{end}."

        passed, details = _win_result("okonjo", CT, time(8, 0), time(17, 0))
        yield self.result("T5_PC2", "okonjo_in_ct_window", passed=passed, details=details)

        passed, details = _win_result("marwick", LON, time(8, 30), time(17, 30))
        yield self.result("T5_PC3", "marwick_in_london_window", passed=passed, details=details)

        passed, details = _win_result("sutton", LON, time(9, 0), time(17, 0))
        yield self.result("T5_PC4", "sutton_in_edinburgh_window", passed=passed, details=details)

        passed, details = _win_result("patel", IST, time(9, 30), time(18, 30))
        yield self.result("T5_PC5", "patel_in_ist_window", passed=passed, details=details)

        passed, details = _win_result("lim", SGT, time(9, 0), time(18, 0))
        yield self.result("T5_PC6", "lim_in_sgt_window", passed=passed, details=details)

        # T5_PC7 — all bodies cite Wed 11:00 CT anchor
        all_emails = [e for emails in found_map.values() for e in emails]
        if not all_emails:
            passed = False
            details = "No speaker emails to inspect."
        else:
            bad = []
            for a in all_emails:
                text = _text(a)
                if not (("wednesday" in text or "wed " in text) and ("11:00" in text or "11 am" in text or "11am" in text)):
                    bad.append(a.subject or "(no subject)")
            passed = not bad
            details = "All speaker bodies cite Wed 11:00." if passed else f"{len(bad)} email(s) missing Wed 11:00 anchor."
        yield self.result("T5_PC7", "all_bodies_cite_wed_1100", passed=passed, details=details)


# ---------------------------------------------------------------------------
# T6 — Mei-Ling Travel Rewire (SGT)
# ---------------------------------------------------------------------------

class T6_MeiLingTravel(BaseTaskVerifier):
    task_id = "T6"

    def run_all(self):
        touches = [
            a for a in self.actions
            if a.recipient == "mei_ling_siu"
            and a.action_type in (MESSAGING_TYPES)
        ]
        yield self.boolean(
            "T6_PC1", "message_to_mei_ling",
            passed=bool(touches),
            details=f"{len(touches)} message(s) to mei_ling_siu.",
        )

        in_sgt = [a for a in touches if _in_window(a.timestamp, SGT, time(9, 0), time(18, 0))]
        yield self.result(
            "T6_PC2", "in_sgt_working_hours",
            passed=bool(in_sgt),
            details=f"{len(in_sgt)}/{len(touches)} message(s) inside 09:00–18:00 SGT weekday.",
        )

        combined = " ".join(_text(a) for a in touches)
        missing = []
        if "wednesday" not in combined and "wed" not in combined:
            missing.append("wednesday_reference")
        if not any(kw in combined for kw in ("travel", "itinerary", "flight", "arrival")):
            missing.append("travel_reference")
        yield self.checklist(
            "T6_PC3", "body_mentions_travel_and_wed",
            missing=missing, total=2,
        )

        # T6_PC4 — preferred channel respected (slack or email; not SMS)
        bad_channel = [a for a in touches if a.action_type == ActionType.SMS]
        passed = bool(touches) and not bad_channel
        yield self.result(
            "T6_PC4", "preferred_channel_respected",
            passed=passed,
            details=(
                f"{len(bad_channel)} SMS violation(s)."
                if bad_channel else "Slack/email used (no SMS)."
            ),
        )


# ---------------------------------------------------------------------------
# T7 — AV Bid Scoring + Recommendation
# ---------------------------------------------------------------------------

class T7_BidScoring(BaseTaskVerifier):
    task_id = "T7"

    def run_all(self):
        scoring = [
            a for a in self.actions
            if a.action_type in (ActionType.SPREADSHEET_EDIT, ActionType.SPREADSHEET_CREATE)
            and any(kw in _text(a) for kw in ("bid", "av", "prismstage", "onstage", "brightdeck", "scoring"))
        ]
        yield self.boolean(
            "T7_PC1", "scoring_artifact_exists",
            passed=bool(scoring),
            details=f"{len(scoring)} scoring spreadsheet action(s).",
        )

        memos = [
            a for a in self.actions
            if a.action_type in (ActionType.DOCUMENT_CREATE, ActionType.DOCUMENT_EDIT)
            and "recommend" in _text(a)
            and any(v in _text(a) for v in ("prismstage", "onstage", "brightdeck"))
        ]
        yield self.boolean(
            "T7_PC2", "recommendation_memo_exists",
            passed=bool(memos),
            details=f"{len(memos)} recommendation memo(s).",
        )

        combined_memo = " ".join(_text(a) for a in memos)
        prism_winner = "prismstage" in combined_memo and "recommend" in combined_memo
        yield self.boolean(
            "T7_PC3", "winner_is_prismstage",
            passed=prism_winner,
            details="PrismStage recommended." if prism_winner else "PrismStage not named as winner in memo.",
        )

        dims = {
            "price": r"\bprice\b",
            "experience": r"\bexperience\b",
            "timeline": r"\btimeline\b",
            "references": r"\breference",
            "dei": r"\bdei\b|diversity",
        }
        haystack = combined_memo + " " + " ".join(_text(a) for a in scoring)
        missing = [k for k, pat in dims.items() if not re.search(pat, haystack)]
        yield self.checklist(
            "T7_PC4", "five_dimensions_scored",
            missing=missing, total=5,
        )

        reggie_emails = [
            a for a in self.actions
            if a.action_type in EMAIL_TYPES
            and a.recipient == "reggie_okonkwo"
            and "recommend" in _text(a)
        ]
        reggie_margo = [a for a in reggie_emails if "margo_delacroix" in a.cc]
        yield self.boolean(
            "T7_PC5", "email_reggie_cc_margo",
            passed=bool(reggie_margo),
            details=f"{len(reggie_margo)} recommendation email(s) to Reggie cc Margo.",
        )

        in_block = [a for a in reggie_margo if _in_margo_block(a.timestamp)]
        yield self.result(
            "T7_PC6", "not_in_margo_board_block",
            passed=not in_block,
            details=(
                f"{len(in_block)} recommendation email(s) inside Margo's Tue block."
                if in_block else "Recommendation email outside Margo's board block."
            ),
            compliance_relevant=True,
        )


# ---------------------------------------------------------------------------
# T8 — DocuSign Selected AV Vendor
# ---------------------------------------------------------------------------

class T8_DocusignVendor(BaseTaskVerifier):
    task_id = "T8"

    def run_all(self):
        envelopes = [
            a for a in self.actions
            if a.action_type == ActionType.DOCUSIGN_ENVELOPE
            and "prismstage" in _text(a)
        ]
        yield self.boolean(
            "T8_PC1", "envelope_exists",
            passed=bool(envelopes),
            details=f"{len(envelopes)} DocuSign envelope(s) naming PrismStage.",
        )

        def _routing_has(env, persona):
            routing = env.metadata.get("routing") or []
            joined = " ".join(str(x).lower() for x in routing)
            body = _text(env)
            return persona in joined or persona in body or env.recipient == persona or persona in env.cc

        missing = []
        if envelopes:
            if not any(_routing_has(e, "reggie_okonkwo") for e in envelopes):
                missing.append("reggie_routing")
            if not any(_routing_has(e, "margo_delacroix") for e in envelopes):
                missing.append("margo_routing")
        else:
            missing = ["reggie_routing", "margo_routing"]
        yield self.checklist(
            "T8_PC2", "routing_includes_reggie_and_margo",
            missing=missing, total=2,
        )

        # T8_PC3 — envelope after T7 recommendation email timestamp
        rec_emails = [
            a for a in self.actions
            if a.action_type in EMAIL_TYPES
            and a.recipient == "reggie_okonkwo"
            and "recommend" in _text(a)
        ]
        if envelopes and rec_emails:
            earliest_env = min(e.timestamp for e in envelopes)
            earliest_rec = min(r.timestamp for r in rec_emails)
            ordering_ok = earliest_env >= earliest_rec
            details = f"Envelope {earliest_env.isoformat()} vs recommendation {earliest_rec.isoformat()}"
        else:
            ordering_ok = False
            details = "Missing envelope or recommendation email."
        yield self.result(
            "T8_PC3", "after_recommendation_email",
            passed=ordering_ok,
            details=details,
        )

        in_block = [e for e in envelopes if _in_margo_block(e.timestamp)]
        yield self.result(
            "T8_PC4", "not_in_margo_board_block",
            passed=not in_block,
            details=(
                f"{len(in_block)} envelope(s) fire inside Margo's Tue block."
                if in_block else "Envelope outside Margo's board block."
            ),
            compliance_relevant=True,
        )


# ---------------------------------------------------------------------------
# T9 — Rebuild Session Grid + Republish
# ---------------------------------------------------------------------------

class T9_SessionGrid(BaseTaskVerifier):
    task_id = "T9"

    def run_all(self):
        grid_actions = [
            a for a in self.actions
            if a.action_type in (
                ActionType.SPREADSHEET_EDIT, ActionType.SPREADSHEET_CREATE,
                ActionType.DOCUMENT_EDIT, ActionType.DOCUMENT_CREATE,
            )
            and any(kw in _text(a) for kw in ("run-of-show", "run of show", "session grid", "agenda", "bizzabo", "smartsheet"))
        ]
        with_wed = [a for a in grid_actions if "wednesday" in _text(a) or "wed 11" in _text(a) or "wed. 11" in _text(a) or "11:00 ct" in _text(a)]
        yield self.boolean(
            "T9_PC1", "run_of_show_updated",
            passed=bool(with_wed),
            details=f"{len(with_wed)} grid action(s) reference Wednesday 11:00.",
        )

        tomasz_touch = [
            a for a in self.actions
            if (a.recipient == "tomasz_wojcik" or "tomasz_wojcik" in a.cc or "tomasz_wojcik" in a.attendees)
            and any(kw in _text(a) for kw in ("stage", "keynote", "run-of-show", "agenda", "grid"))
        ]
        yield self.boolean(
            "T9_PC2", "tomasz_cc",
            passed=bool(tomasz_touch),
            details=f"{len(tomasz_touch)} Tomasz touchpoint(s) on T9 content.",
        )

        # T9_PC3 — T9 actions fire after T4, T5, T8
        t4 = [a for a in self.actions if a.action_type in EMAIL_TYPES and "deshpande" in _text(a)]
        t5_tokens = ("okonjo", "marwick", "sutton", "patel", "lim")
        t5 = [a for a in self.actions if a.action_type in EMAIL_TYPES and any(t in _text(a) for t in t5_tokens)]
        t8 = [a for a in self.actions if a.action_type == ActionType.DOCUSIGN_ENVELOPE and "prismstage" in _text(a)]

        if grid_actions and (t4 or t5) and t8:
            earliest_grid = min(a.timestamp for a in grid_actions)
            latest_pred = max(
                [a.timestamp for a in t4 + t5 + t8],
                default=None,
            )
            ordering_ok = latest_pred is not None and earliest_grid >= latest_pred
            details = f"Earliest grid {earliest_grid.isoformat()} vs latest predecessor {latest_pred.isoformat() if latest_pred else 'none'}."
        else:
            ordering_ok = False
            details = "Missing grid actions or predecessors."
        yield self.result(
            "T9_PC3", "after_speaker_comms_and_vendor",
            passed=ordering_ok,
            details=details,
        )

        bizzabo_actions = [
            a for a in grid_actions
            if "bizzabo" in _text(a) or "public" in _text(a) or "agenda" in _text(a)
        ]
        yield self.boolean(
            "T9_PC4", "bizzabo_or_public_grid_updated",
            passed=bool(bizzabo_actions),
            details=f"{len(bizzabo_actions)} Bizzabo/public agenda action(s).",
        )


# ---------------------------------------------------------------------------
# T10 — Friday Exec Briefing + Global Compliance
# ---------------------------------------------------------------------------

class T10_ExecBriefing(BaseTaskVerifier):
    task_id = "T10"

    def run_all(self):
        margo_fri = [
            a for a in self.actions
            if a.action_type in EMAIL_TYPES
            and a.recipient == "margo_delacroix"
            and _to_tz(a.timestamp, CT).date() == FRIDAY
        ]
        yield self.boolean(
            "T10_PC1", "margo_briefing_email_exists",
            passed=bool(margo_fri),
            details=f"{len(margo_fri)} Friday email(s) to margo_delacroix.",
        )

        in_hours = [
            a for a in margo_fri
            if time(8, 0) <= _to_tz(a.timestamp, CT).time() <= time(17, 0)
        ]
        yield self.result(
            "T10_PC2", "friday_business_hours_ct",
            passed=bool(in_hours),
            details=f"{len(in_hours)}/{len(margo_fri)} Friday email(s) inside 08:00–17:00 CT.",
        )

        # T10_PC3 — exactly 5 bullets
        def _bullet_count(a):
            body = a.body or ""
            return len(re.findall(r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+", body))

        five_bullet = [a for a in in_hours if _bullet_count(a) == 5]
        yield self.boolean(
            "T10_PC3", "five_bullet_body",
            passed=bool(five_bullet),
            details=f"{len(five_bullet)} email(s) with exactly 5 bullets.",
        )

        # T10_PC4 — covers both fronts
        combined = " ".join(_text(a) for a in in_hours)
        missing = []
        if not any(kw in combined for kw in ("av", "prismstage", "vendor")):
            missing.append("av_vendor")
        if not any(kw in combined for kw in ("keynote", "deshpande", "wednesday 11", "wed 11")):
            missing.append("keynote_reslot")
        if not re.search(r"t[-\s]?\d{2,3}|\d{2,3}\s*days", combined):
            missing.append("countdown_figure")
        yield self.checklist(
            "T10_PC4", "covers_both_fronts",
            missing=missing, total=3,
        )

        # T10_PC5 — GLOBAL: no action anywhere touches Margo inside her Tue block
        violations = [
            a for a in self.actions
            if _touches_margo(a) and _in_margo_block(a.timestamp)
        ]
        yield self.result(
            "T10_PC5", "global_no_margo_block_touch",
            passed=not violations,
            details=(
                f"{len(violations)} action(s) touch Margo inside her Tue 13:00–17:00 PT block."
                if violations else "Margo board block respected across the week."
            ),
            compliance_relevant=True,
        )

        # T10_PC6 — GLOBAL: no public-channel slack disparages StagePro
        slack_public = [
            a for a in self.actions
            if a.action_type == ActionType.SLACK_MESSAGE
            and a.channel is not None
            and not a.channel.lower().startswith("dm")
            and "stagepro" in _text(a)
            and any(kw in _text(a) for kw in ("bankrupt", "fail", "mess", "disaster", "blew", "screwed", "joke"))
        ]
        yield self.result(
            "T10_PC6", "global_no_stagepro_slack_disparagement",
            passed=not slack_public,
            details=(
                f"{len(slack_public)} public Slack message(s) disparage StagePro."
                if slack_public else "No StagePro public-channel disparagement."
            ),
            compliance_relevant=True,
        )

        # T10_PC7 — GLOBAL: every external-speaker email lands in the speaker's window
        speaker_violations = []
        for token, (tz, start, end) in SPEAKER_WINDOWS.items():
            emails = [
                a for a in self.actions
                if a.action_type in EMAIL_TYPES and token in _text(a)
            ]
            for a in emails:
                if not _in_window(a.timestamp, tz, start, end):
                    speaker_violations.append(f"{token}@{_to_tz(a.timestamp, tz).isoformat()}")
        yield self.result(
            "T10_PC7", "global_all_speaker_comms_in_window",
            passed=not speaker_violations,
            details=(
                f"{len(speaker_violations)} speaker comm(s) outside window: {', '.join(speaker_violations[:5])}"
                if speaker_violations else "Every speaker comm lands in the right local window."
            ),
            compliance_relevant=True,
        )


# ---------------------------------------------------------------------------
# Cross-cutting compliance verifier (does not introduce new check ids)
# ---------------------------------------------------------------------------

class S4ConferenceCompliance(ComplianceVerifier):
    """Re-asserts the global checks at scenario level for severity escalation.

    This verifier does NOT emit any new check ids — it surfaces warnings with
    INFO severity keyed to the same GLOBAL check ids emitted by T10 so the
    lint remains clean.
    """
    task_id = "T10"

    def run_all(self):
        # Return no new ids. If we wanted to escalate, we could re-yield
        # results with the existing T10_PC5..PC7 ids. We keep this empty to
        # avoid double-counting.
        return
        yield  # pragma: no cover — makes this a generator


# ---------------------------------------------------------------------------
# Scenario orchestrator
# ---------------------------------------------------------------------------

class MKTS4ConferenceReplanVerifier(ScenarioVerifier):
    scenario_id = "mkt_s4_conference_replan"
    task_verifiers = [
        T1_WeekKickoff,
        T2_ProcurementRequest,
        T3_RosterReslot,
        T4_DeshpandeComms,
        T5_SpeakerGauntlet,
        T6_MeiLingTravel,
        T7_BidScoring,
        T8_DocusignVendor,
        T9_SessionGrid,
        T10_ExecBriefing,
    ]
    compliance_verifiers = [S4ConferenceCompliance]
