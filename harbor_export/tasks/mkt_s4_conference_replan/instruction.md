# mkt_s4_conference_replan

**Domain**: marketing
**Agent role**: Chief of Staff to Events Director Reggie Okonkwo
**Simulated start**: 2026-04-06T09:00:00-04:00 (America/New_York)
**DAG tasks**: 10
**Programmatic checks**: 50
**Personas**: 14

## Company context
## Marketing — Lumalynx Learning

Series C K-12 edtech. $94M ARR, 640 employees. SF HQ, Dublin EMEA, Singapore APAC. Current crises and concurrent initiatives: Tutor 3.0 launch slipped April 28 → May 12; KnowGraph partner under The Verge investigation March 27; Project Lighthouse top-20 district ABM mid-flight; LumaSummit July 14-16 Chicago with StagePro AV vendor bankruptcy March 18; rebrand "Lumalynx Tutor → Lumalynx Learn" with 2,400-URL SEO migration May 5.

## Brief
### mkt_s4_conference_replan — Annual user conference replan after vendor cancellation

**Agent role:** Chief of Staff to Events Director Reggie Okonkwo.
**Duration:** 1 week. **Tasks:** 10. **Dominant trap:** timezone_scheduling_trap. **Regulatory:** none.
**Premise:** LumaSummit is July 14-16 in Chicago. 1,200 attendees confirmed. On March 18, AV vendor StagePro files bankruptcy. Reggie has 118 days to find a replacement, re-contract, re-brief, and not miss the event. In parallel, a keynote speaker (a high-profile district superintendent) has a scheduling conflict that surfaces during the sprint week — she can no longer do the Tuesday 9:00 AM CT slot but can do Wednesday 11:00 AM CT. The agent must rebuild the keynote roster and communicate with 6 external speakers across US, UK, India, and Singapore timezones. Mei-Ling Siu (Singapore APAC lead) is flying in for the APAC track; her travel was booked around the old speaker roster. Sean O'Riordain's agency runs speaker comms. Margo's Tuesday 13:00-17:00 PT board-prep block falls inside the sprint week and the agent must not schedule anything touching Margo in that window.
**Key tensions:** 118 days is tight for AV re-procurement (Reggie wants it done in 10 days, Procurement-equivalent will balk); the keynote reshuffle cascades into session grid; multi-timezone speaker comms with hard working-hour boundaries.
**Deliverables:** 3 AV vendor bids with SOWs, AV vendor selected and contracted (DocuSign), updated keynote roster, new session grid published, speaker comms sent within each speaker's working hours, travel changes for Mei-Ling, internal exec briefing for Margo.

## Available personas

- `margo_delacroix` | Marguerite "Margo" Delacroix-Hollis | Chief Marketing Officer | email
- `priyanka_shah` | Priyanka Shah | VP Product Marketing | slack
- `tomasz_wojcik` | Tomasz Wojcik | Creative Director | slack
- `fiona_breathnach` | Fiona Ní Bhreathnach | Director of Brand & PR, EMEA | email
- `kofi_asante` | Kofi Asante | Director of Demand Generation | slack
- `aanya_iyer` | Aanya Iyer | ABM Program Manager (Top-20 District Accounts) | slack
- `sunita_kaur_gill` | Sunita Kaur Gill | Director of Content & Editorial | email
- `ollie_brennan` | Ollie Brennan | SEO Lead | slack
- `yuki_tanaka_hendricks` | Yuki Tanaka-Hendricks | Marketing Operations & Attribution Lead | slack
- `devika_raghunathan` | Devika Raghunathan, Esq. | Senior Counsel, Marketing & Regulatory (FTC, COPPA, Claims Review) | email [banned: slack, sms, verbal]
- `reggie_okonkwo` | Reginald "Reggie" Okonkwo | Head of Events & Experiential Marketing | slack
- `mei_ling_siu` | Mei-Ling Siu | Head of Marketing, APAC (based Singapore; covers SG, ANZ, India, SEA, JP) | slack
- `sean_o_riordain` | Seán Ó Ríordáin | Managing Partner, Whitefield Communications (Lumalynx's AOR for global PR) | email
- `connor_yazzie` | Connor Yazzie | VP Sales, Classroom Segment (District K-12) | slack

## Input files

- `inputs/chat/events_ops_channel.yaml`
- `inputs/chat/lumasummit_speakers_slack.yaml`
- `inputs/docs/lumasummit_run_of_show_v3.md`
- `inputs/docs/speaker_comms_template.md`
- `inputs/docs/stagepro_original_sow.md`
- `inputs/emails/2026-04-05_reggie_to_cos_kickoff.md`
- `inputs/emails/2026-04-06_deshpande_office_conflict.md`
- `inputs/emails/2026-04-06_procurement_portal_rules.md`
- `inputs/emails/2026-04-06_sean_whitefield_standing_rules.md`
- `inputs/reports/brightdeck_bid.pdf`
- `inputs/reports/onstage_atlas_bid.pdf`
- `inputs/reports/prismstage_bid.pdf`
- `inputs/reports/stagepro_bankruptcy_notice.pdf`
- `inputs/sheets/av_bids_comparison.xlsx`
- `inputs/sheets/av_vendor_shortlist.xlsx`
- `inputs/sheets/lumasummit_speakers_v2.xlsx`
- `inputs/sheets/mei_ling_travel_itinerary_v1.xlsx`
