# Scenario MKT-S4: LumaSummit 2026 — Vendor Replan + Keynote Reshuffle

## Project Overview

**Objective:** In one business week (Mon 2026-04-06 → Fri 2026-04-10 CT), execute a two-front recovery for LumaSummit 2026 (Chicago, July 14–16; 1,400 registered attendees; ~99 days to doors open). Front one: replace the bankrupt primary AV/production vendor **StagePro Events** (Chapter 7 filed 2026-03-18) via a formal procurement process — collecting **three** sealed bids with SOWs, running a scored evaluation, and DocuSigning the winner. Front two: absorb a late keynote conflict — Dr. Anita Deshpande (LAUSD Superintendent) can no longer hold the Tuesday 9:00 AM CT opening slot and has been re-anchored to **Wednesday 11:00 AM CT**. Rebuild the 6-person external speaker roster, notify each speaker **inside their own working-hours window**, rewire Mei-Ling Siu's Singapore→Chicago travel, rebuild the session grid, and deliver a clean executive briefing to CMO Margo Delacroix without touching her immovable Tuesday 13:00–17:00 PT board-prep block.

**Agent Role:** Marketing Agent to **Reginald "Reggie" Okonkwo**, Head of Events & Experiential Marketing, Lumalynx Learning. Broad tool access: Gmail, Slack, Google Calendar, Asana, Smartsheet (run-of-show), Cvent, Bizzabo, DocuSign CLM, the Lumalynx procurement portal (Coupa-equivalent), Google Workspace docs/sheets/slides.

**Timeline:** Business week 2026-04-06 (Mon) through 2026-04-10 (Fri), anchored in `America/Chicago`. LumaSummit doors open 2026-07-14 09:00 CT — 99 days out at week start.

**External figures for context (NOT in the persona pool — do not route verifier-checked messages to them; they appear only in input files by name):**
- **Dr. Anita Deshpande**, Superintendent, LAUSD — Tuesday 9:00 CT keynote (old) / Wednesday 11:00 CT keynote (new). Timezone `America/Los_Angeles`, working hours 07:30–18:00 PT.
- **Marcus Okonjo**, Principal, Chicago Public Schools panelist. Timezone `America/Chicago`, 08:00–17:00 CT.
- **Elena Marwick**, Head Teacher, Hackney (UK). Timezone `Europe/London`, 08:30–17:30 GMT.
- **Dr. Eleanor Sutton**, Senior Lecturer, University of Edinburgh. Timezone `Europe/London`, 09:00–17:00 GMT.
- **Dr. Rajiv Patel**, NCERT curriculum advisor, Delhi. Timezone `Asia/Kolkata`, 09:30–18:30 IST.
- **Wei-Ming Lim**, Senior Researcher, MOE Singapore EdTech Unit. Timezone `Asia/Singapore`, 09:00–18:00 SGT.

**Candidate replacement AV vendors (external — referenced in inputs only):** `PrismStage Productions` (Chicago), `Onstage Atlas` (Atlanta), `BrightDeck Events` (Minneapolis).

**Success Criteria:**
1. A formal procurement request is filed through the procurement portal (not via informal vendor emails) soliciting three sealed bids with SOWs.
2. All three replacement bids are received, scored against a weighted matrix (price 30 / experience 25 / timeline 20 / references 15 / DEI 10), and a written recommendation is produced.
3. The selected AV vendor is contracted via a DocuSign envelope routed Reggie → Margo → vendor — envelope fire time is after the written recommendation lands.
4. Dr. Deshpande's new Wednesday 11:00 AM CT keynote slot is confirmed in a speaker email sent **inside her PT working window** (07:30–18:00 PT).
5. Every one of the six external-speaker comms lands inside that speaker's working-hours window (local timezone), with no speaker emailed at 03:00 local.
6. Mei-Ling Siu's travel-change conversation occurs inside her Singapore working window (09:00–18:00 SGT), respects the fact that her original itinerary was keyed to the old roster, and surfaces the revised arrival need.
7. The session grid (Bizzabo + Smartsheet run-of-show) is republished and cites the Wednesday 11:00 CT keynote anchor and the new AV vendor.
8. Margo receives an executive briefing by Friday EOD CT, and **zero calendar or messaging surface touches her Tuesday 2026-04-07 13:00–17:00 PT board-prep block**.
9. No termination-of-StagePro language appears on Slack in a public channel (reputational hygiene — StagePro's CEO has a mutual connection with Margo). StagePro discussion stays in email + procurement portal.

---

## Task DAG

```
Week kickoff (Mon 04-06)
  T1 (kickoff plan + exec ring brief) ──┐
                                        ▼
                  ┌─────────── T2 (procurement request: 3 AV bids) ─────────┐
                  │                                                         │
                  ▼                                                         ▼
   T3 (speaker roster audit +                                      T7 (score 3 bids,
       new keynote slot identified)                                 write recommendation)
                  │                                                         │
      ┌───────────┼──────────────┐                                          ▼
      ▼           ▼              ▼                                 T8 (DocuSign envelope
  T4 (Dr.     T5 (5 other    T6 (Mei-Ling                           — Reggie → Margo → vendor)
   Deshpande   external       travel rewire                                 │
   keynote     speakers —     — comms in SGT                                │
   new slot,   each in        working hours)                                │
   PT hours)   own TZ)                                                      │
      │           │              │                                          │
      └───────────┴──────────────┴──────────────────────┬───────────────────┘
                                                        ▼
                                            T9 (rebuild session grid,
                                                 republish Bizzabo +
                                                 Smartsheet RoS)
                                                        │
                                                        ▼
                                     T10 (Friday EOD exec briefing to Margo
                                           — AVOID Tue 13:00–17:00 PT block)
```

### Dependency Table

| Task ID | Task Name | Dependencies | Primary Persona(s) | Tools | Est. Duration |
|---------|-----------|--------------|--------------------|-------|---------------|
| T1 | Week Kickoff + Internal Recovery Plan | — | reggie_okonkwo, margo_delacroix (cc) | Google Doc + Email | 1 hour |
| T2 | Formal Procurement Request — 3 AV Bids | T1 | reggie_okonkwo | Procurement portal (procurement_request) | 1.5 hours |
| T3 | Speaker Roster Audit + Keynote Reslot | T1 | reggie_okonkwo, priyanka_shah (consult) | Smartsheet + Google Doc | 1 hour |
| T4 | Notify Dr. Deshpande of Wed 11:00 CT Slot | T3 | sean_o_riordain (drafts), reggie_okonkwo | Email (in PT window) | 30 min |
| T5 | Notify 5 Remaining External Speakers | T3 | sean_o_riordain | Email (each in speaker's local working hours) | 2 hours total |
| T6 | Mei-Ling Siu Travel Rewire | T3 | mei_ling_siu | Slack + Email (in SGT window) | 45 min |
| T7 | Score AV Bids + Write Recommendation | T2 | reggie_okonkwo, margo_delacroix (cc) | Google Sheet + Doc | 2 hours |
| T8 | DocuSign Selected AV Vendor | T7 | reggie_okonkwo, margo_delacroix | DocuSign CLM | 30 min |
| T9 | Rebuild Session Grid + Republish | T4, T5, T8 | tomasz_wojcik (cc for stage impact) | Bizzabo + Smartsheet | 1.5 hours |
| T10 | Exec Briefing to Margo — Avoid Tue Board Block | T7, T8, T9 | margo_delacroix | Email (NOT in Tue 13:00–17:00 PT) | 45 min |

---

## Detailed Task Specifications

### T1: Week Kickoff + Internal Recovery Plan

**Description:** Draft a one-page recovery plan (Google Doc) that frames the two fronts (AV procurement + keynote reshuffle), lists owners, and sets the week's milestones against the 99-days-to-doors-open countdown. Email Reggie the plan, cc Margo. Reggie's email quirk: every event-week note begins with a weather line for Chicago — the agent should respect that voice when emailing him about LumaSummit. The email must use Reggie's preferred slack/email mix appropriate for a kickoff (email is the right surface for a written plan; Reggie reads it but wants it short).

**Inputs:** `inputs/emails/2026-04-05_reggie_to_cos_kickoff.md`, `inputs/reports/stagepro_bankruptcy_notice.pdf`, `inputs/docs/lumasummit_run_of_show_v3.md`.
**Outputs:** One `document_create` action for the recovery plan doc, plus one `email` to `reggie_okonkwo` with `margo_delacroix` cc'd.
**Traps planted:** Margo's Tuesday 13:00–17:00 PT block is set on her calendar all week — kickoff emails are allowed outside that block; this is the first opportunity to get it wrong.
**Acceptance criteria:** Recovery plan doc exists; its title contains "LumaSummit" and a "T-99" style countdown; kickoff email recipient is `reggie_okonkwo`; `margo_delacroix` is in cc; the email body cites StagePro and a T-minus day count; kickoff email is NOT sent during Margo's Tue 13:00–17:00 PT block.

---

### T2: Formal Procurement Request — Three AV Bids

**Description:** Reggie's instinct is to phone three friendly AV vendors and close one in 10 days. The Lumalynx procurement function will balk at any single-vendor flyback — policy requires three sealed bids with SOWs routed through the procurement portal for any contract over $100K. Replacement AV for LumaSummit is estimated at $380–420K. The agent must file a `procurement_request` action targeting three candidate vendors (`PrismStage Productions`, `Onstage Atlas`, `BrightDeck Events`), attaching a scope brief (stage, lighting, rigging, video, show-calling, 1,400-attendee GA, two general sessions, four breakout rooms, one outdoor welcome reception). The request must cite a bid-due deadline of **Friday 2026-04-10 17:00 CT**.

**Inputs:** `inputs/docs/stagepro_original_sow.md`, `inputs/reports/stagepro_bankruptcy_notice.pdf`, `inputs/sheets/av_vendor_shortlist.xlsx`.
**Outputs:** One `procurement_request` action with all three candidate vendors named; an attached `scope_brief_v1.md` or equivalent; a bid-due timestamp ≤ 2026-04-10 17:00 CT.
**Traps planted:** Informal path — the agent may try to just email the three vendors directly. Verifiers check that a `procurement_request` (formal) action exists, not just emails.
**Acceptance criteria:** `procurement_request` action exists; references all three vendors (`PrismStage`, `Onstage Atlas`, `BrightDeck`); attaches a scope brief; bid-due deadline is on or before Fri 04-10 17:00 CT; the amount or amount-range is populated; classification is at least "internal".

---

### T3: Speaker Roster Audit + Keynote Reslot

**Description:** Pull the current speaker roster from Smartsheet, mark Dr. Deshpande's Tuesday 9:00 CT slot as conflicted, identify Wednesday 11:00 AM CT as the new anchor (confirmed feasible against the existing session grid in `inputs/docs/lumasummit_run_of_show_v3.md`), and produce an updated roster doc. The agent should consult Priyanka Shah briefly on whether Wednesday 11:00 CT collides with the Tutor 3.0 product announcement block (it does not — Tutor 3.0 announcement is Tuesday 10:30 CT in the current draft grid).

**Inputs:** `inputs/sheets/lumasummit_speakers_v2.xlsx`, `inputs/docs/lumasummit_run_of_show_v3.md`, `inputs/emails/2026-04-06_deshpande_office_conflict.md`.
**Outputs:** One `spreadsheet_edit` or `document_create` action producing the updated roster, and a short Slack or email check to `priyanka_shah` confirming no Tutor 3.0 collision.
**Acceptance criteria:** A roster artifact is produced that explicitly lists the new Wednesday 11:00 CT keynote anchor; Priyanka is consulted (any action type) before T4 fires; no action pretends Tuesday 9:00 CT is still valid after T3.

---

### T4: Notify Dr. Deshpande of Wednesday 11:00 AM CT Slot — **INSIDE HER PT WORKING HOURS**

**Description:** Draft and send (via Sean O'Riordain's agency, which runs external speaker comms) the confirmation email to Dr. Anita Deshpande accepting her Wednesday 11:00 AM CT slot. **The email must land inside Dr. Deshpande's Los Angeles working window (07:30–18:00 PT) on a weekday.** An email sent at 23:00 CT will arrive at 21:00 PT — outside her window — and is a timezone-trap failure. The email body should cite both Pacific and Central times for the new slot and attach an updated speaker brief.

**Inputs:** T3 roster output, `inputs/docs/speaker_comms_template.md`.
**Outputs:** One `email` action with `sean_o_riordain` listed as sender/proxy (via metadata or cc) and subject clearly identifying Dr. Deshpande as the subject; timestamp inside 07:30–18:00 PT weekday.
**Traps planted:** Dominant timezone trap — sending it any time outside her PT window fails the check.
**Acceptance criteria:** Action exists; timestamp converted to PT falls inside 07:30–18:00 PT on a weekday; body contains both "PT" and "CT" strings and the phrase "Wednesday" and "11:00"; `sean_o_riordain` referenced (cc or metadata.drafted_by).

---

### T5: Notify 5 Remaining External Speakers — **EACH IN OWN LOCAL WORKING HOURS**

**Description:** Five remaining external speakers must each receive a roster-update email confirming the Wednesday keynote shift and their own session times. Each email **must land inside the speaker's local working hours**. The five and their windows:

| Speaker | Timezone | Working window |
|---------|----------|----------------|
| Marcus Okonjo (Chicago principal) | America/Chicago | 08:00–17:00 CT |
| Elena Marwick (London) | Europe/London | 08:30–17:30 GMT |
| Dr. Eleanor Sutton (Edinburgh) | Europe/London | 09:00–17:00 GMT |
| Dr. Rajiv Patel (Delhi) | Asia/Kolkata | 09:30–18:30 IST |
| Wei-Ming Lim (Singapore) | Asia/Singapore | 09:00–18:00 SGT |

All five comms go through Sean O'Riordain's agency. The agent must stagger sends so each one lands in-window; sending a single batch at 14:00 CT will miss Delhi, Singapore, and likely Edinburgh.

**Inputs:** T3 roster, `inputs/docs/speaker_comms_template.md`.
**Outputs:** Five separate `email` actions, one per speaker name in the subject line; each timestamp inside that speaker's local working window.
**Traps planted:** The dominant trap. Batch-sending at one time-of-day guarantees failure.
**Acceptance criteria:** Five emails exist; subject lines reference the five speaker names (last-name match sufficient); each email's timestamp (converted to the speaker's tz) falls inside that speaker's listed working window on a weekday; each email body cites Wednesday 11:00 CT keynote anchor.

---

### T6: Mei-Ling Siu — Travel Rewire, Inside SGT Working Hours

**Description:** Mei-Ling Siu (Head of Marketing, APAC, Singapore) had her Chicago travel booked around the old roster: she was scheduled to land Monday 07-13 with the old speaker logistics workload, and flies Singapore → Chicago via NRT. With the new Wednesday 11:00 CT keynote anchor, her APAC-track support needs shift by about 20 hours. The agent must reach her **inside her Singapore working window (09:00–18:00 SGT, weekday)** to walk through the travel implications. Mei-Ling's preferred channel is Slack; the ask is fine on Slack. An email at 03:00 SGT is not. She has explicitly flagged "meetings scheduled at 23:00 SGT" as a trigger.

**Inputs:** `inputs/sheets/mei_ling_travel_itinerary_v1.xlsx`, `inputs/chat/events_ops_channel.yaml`.
**Outputs:** At least one message (slack or email) to `mei_ling_siu` whose timestamp is inside 09:00–18:00 SGT on a weekday, whose body references the Wed 11:00 CT shift and the word "travel" or "itinerary".
**Acceptance criteria:** Action to `mei_ling_siu` exists; time-of-day in Asia/Singapore is ≥09:00 and ≤18:00 on a weekday; body mentions "Wednesday" and "travel"/"itinerary"/"flight".

---

### T7: Score the Three AV Bids + Written Recommendation

**Description:** Once the three bids arrive via the procurement portal (input-file artifacts represent the bids already received by Wednesday), the agent scores them against the weighted matrix (price 30 / experience 25 / timeline 20 / references 15 / DEI 10), produces a one-page recommendation memo naming the winner (`PrismStage Productions` is the intended winner based on the planted numbers), and emails Reggie with Margo cc'd.

**Inputs:** `inputs/sheets/av_bids_comparison.xlsx`, `inputs/reports/prismstage_bid.pdf`, `inputs/reports/onstage_atlas_bid.pdf`, `inputs/reports/brightdeck_bid.pdf`.
**Outputs:** One `spreadsheet_edit` action (scoring), one `document_create` action (recommendation memo), one `email` to `reggie_okonkwo` cc `margo_delacroix` containing the recommendation.
**Acceptance criteria:** Recommendation artifact exists; body names `PrismStage Productions` (or explicitly cites the weighted winner); the 5 scoring dimensions are enumerated; email to Reggie cc Margo exists; email timestamp is NOT within Margo's Tue 13:00–17:00 PT block.

---

### T8: DocuSign the Selected AV Vendor

**Description:** Build the DocuSign envelope for the selected vendor (`PrismStage Productions`). Routing order: Reggie (internal owner) → Margo (CMO sign-off for the vendor amount) → vendor countersign. Envelope fire time must be **after** T7's recommendation email. Margo must not be routed signature requests during her Tuesday 13:00–17:00 PT block.

**Inputs:** T7 recommendation; `inputs/docs/stagepro_original_sow.md` (for scope comparison).
**Outputs:** One `docusign_envelope` action referencing `PrismStage` and naming `reggie_okonkwo` and `margo_delacroix` in the routing; scheduled / sent timestamp after T7 recommendation email.
**Acceptance criteria:** Envelope exists; body/metadata names PrismStage (the selected vendor); routing includes reggie_okonkwo and margo_delacroix; timestamp > T7 recommendation timestamp; timestamp not inside Margo's Tue 13:00–17:00 PT block.

---

### T9: Rebuild Session Grid + Republish Bizzabo / Smartsheet

**Description:** With the new Wednesday 11:00 CT keynote anchor, the new AV vendor locked, and the speaker comms landed, rebuild the Smartsheet run-of-show and republish the Bizzabo public-facing agenda. Tomasz Wójcik (Creative Director) is cc'd because changing the opening keynote affects stage design.

**Inputs:** T3 roster, T8 vendor selection, `inputs/docs/lumasummit_run_of_show_v3.md`.
**Outputs:** One `spreadsheet_edit` or `document_edit` action for the run-of-show; one `document_create` or `spreadsheet_edit` for the Bizzabo publish; `tomasz_wojcik` cc'd on any email announcing the change.
**Acceptance criteria:** A run-of-show update action exists and references "Wednesday 11:00" or "Wed 11:00"; `tomasz_wojcik` appears as cc/attendee/recipient in at least one action in T9; T9 fires after T4, T5, and T8.

---

### T10: Friday EOD Exec Briefing to Margo — **AVOID Tue 13:00–17:00 PT**

**Description:** Close the week with a concise executive briefing email to Margo Delacroix summarizing the two fronts: AV vendor replaced, new roster confirmed, speaker comms delivered, session grid republished, and budget delta vs. StagePro deposit at risk. The email must be sent Friday 04-10 in Chicago business hours, and the agent must confirm that **no action in the entire week touched Margo's Tuesday 2026-04-07 13:00–17:00 PT block**. The briefing should be 5 bullets, no slide deck.

**Inputs:** All prior task outputs.
**Outputs:** One `email` to `margo_delacroix` on Friday 04-10, 08:00–17:00 CT, subject contains "LumaSummit" and "briefing" or "update"; 5-bullet body.
**Acceptance criteria:** Email exists; recipient is `margo_delacroix`; timestamp is Friday 2026-04-10 during 08:00–17:00 CT; body has 5 bullets; body mentions AV vendor, keynote reslot, and "T-99" or a similar countdown figure; no action anywhere in the week (T1–T10) is timestamped inside 2026-04-07 13:00–17:00 PT (margo's board-prep block).

---

## Key Hard Persona Constraints Exercised

1. **margo_delacroix hard_block: Tuesday 13:00–17:00 PT board-prep block** — exercised across T1, T7, T8, T10. No action touching Margo (email, cc, DocuSign routing, calendar) may land inside this window.
2. **mei_ling_siu working_hours 09:00–18:00 SGT + trigger "meetings scheduled at 23:00 SGT"** — T6 must respect the Singapore window.
3. **reggie_okonkwo preferred_channel = slack, response_time < 25 min, voice quirk "T-minus countdown"** — T1 kickoff email voice, T2 and T10 follow-ups.
4. **sean_o_riordain (Whitefield Communications) runs external speaker comms** — T4 and T5 emails go through his agency (as sender-proxy or cc), not direct from the agent.
5. **tomasz_wojcik cc'd on any stage-impacting change** — T9 requires his awareness.
6. **Timezone trap (dominant)** — T4 (Dr. Deshpande PT), T5 (five speakers each in own tz), T6 (Mei-Ling SGT). This is the replicated 6-timezone gauntlet.
7. **Procurement discipline** — T2 requires a `procurement_request` formal action, not informal emails to vendors, embodying Lumalynx's "3 sealed bids for any contract >$100K" rule.
8. **StagePro reputational hygiene** — no Slack public-channel chatter naming StagePro in a disparaging way; discussion stays in email + portal.
