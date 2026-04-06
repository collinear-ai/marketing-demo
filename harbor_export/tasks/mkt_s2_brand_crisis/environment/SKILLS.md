# Agent Communication & Coordination Skills

General best practices for agents operating in multi-stakeholder workplace environments. These apply across scenarios and should be combined with persona-specific information to guide behavior.

## Discovery Protocol (read this first)

You will not be told every persona's preferences, every org's conventions, or every deliverable's required shape up front. You are expected to *discover* these before acting. The cost of asking a clarifying question is always lower than the cost of doing work that gets bounced back.

- **Read `inputs/handbook/` first.** Every scenario has a domain-specific handbook in `inputs/handbook/` with org-wide norms (ticket formats, channel policies, audit-trail requirements, subject-line conventions, materiality thresholds, sign-off matrices). These are not suggestions — they are the conventions you will be held to. Read the whole thing once at the start of the scenario, then re-read the relevant section before each task.
- **Before executing each task, ask yourself three questions**:
  1. Which handbook sections apply to what I'm about to do?
  2. Which personas will I touch, and do I know their preferences (timezone, preferred channel, format conventions, working hours, hard boundaries)? If not, ask them.
  3. What's the required shape of the deliverable (structured ticket fields? specific subject keywords? specific numeric precision?)? Verify from the handbook before drafting.
- **Ask personas about their preferences directly.** When you're about to work with a persona for the first time, send a short clarifying message: "Quick check before I send — what's your preferred format / working hours / review timeline for X?". NPCs answer honestly. One clarifying message beats one round of rework.
- **Cross-reference prior comms in inputs/**. `inputs/emails/`, `inputs/chat/`, and `inputs/docs/` often contain examples of how a particular persona writes and what conventions they follow. If you see Ayo using `[DECISION]` subject tags in prior emails, that's the convention.
- **Write down what you learn.** When a persona tells you their working hours, preferred channel, subject-label convention, or pet peeve, note it internally and do not violate it again. Repeated violations are remembered.
- **Don't barrel ahead on assumptions.** The most common failure mode is to skip discovery, guess at conventions, and ship a deliverable that gets bounced on a format technicality. Discovery is not overhead — it is the work.

## Channel Selection

- **Match the channel to the topic and recipient.** Some stakeholders prefer Slack, others email, others phone. Security-sensitive topics should never be discussed on informal channels regardless of preference.
- **Respect organizational policies on sensitive data.** PHI, credentials, financial data, and security findings have specific channel requirements that override personal preference.
- **Use formal channels for formal deliverables.** Pre-read distributions, official sign-offs, and stakeholder communications go via email, not Slack.

## Tone & Detail Calibration

- **Adapt tone and length to the recipient.** Some stakeholders want terse bullet points; others want warm, context-rich messages. Read persona profiles before drafting.
- **Lead with the conclusion for executive audiences.** Senior leaders generally want the punchline first, then supporting data.
- **Lead with data for analytical audiences.** Finance, ops, and engineering stakeholders often want numbers before narrative.
- **Match precision expectations.** Some stakeholders care about exact figures; others accept approximations. When in doubt, be precise.

## Timezone & Availability

- **Send messages during the recipient's working hours.** Check timezone before sending. A 10 AM message in your timezone may be a 7 AM or 1 AM message in theirs.
- **Respect after-hours boundaries.** If a persona disconnects at a specific time, do not send non-urgent requests after that.
- **Account for clinic days, travel, and on-call schedules.** Some stakeholders have limited availability on specific days. Check before scheduling.
- **Find overlapping windows for cross-timezone scheduling.** Calculate the intersection of all attendees' working hours before proposing meeting times.

## Request Framing

- **Give adequate lead time.** Thorough reviewers (security, compliance, legal) need weeks, not days. Build this into the plan.
- **Be specific about what you need and when.** Vague requests get deprioritized. Include explicit deliverables and deadlines.
- **Frame requests in terms the recipient cares about.** Engineering cares about technical risk and architecture. Finance cares about unit economics. Clinical cares about patient impact. Compliance cares about regulatory obligations.
- **Avoid triggering known tensions.** If two functions have a history of conflict (e.g., sales vs. engineering on feature prioritization), frame requests neutrally rather than taking sides.

## Information Handling

- **Distinguish confirmed from tentative information.** If a stakeholder flags something as uncommitted, provisional, or tentative, do not present it as decided.
- **Capture qualitative context alongside quantitative data.** Narratives, customer quotes, and contextual details often matter as much as the numbers.
- **Flag data freshness issues.** If a data source has known staleness or integration problems, note this when presenting the data.
- **Cross-validate data across sources.** When multiple systems track the same metric, discrepancies will be noticed by attentive stakeholders.

## Stakeholder Management

- **Follow up privately with conflict-avoidant participants.** Some people won't voice concerns in group settings but will share them 1:1.
- **Save key stakeholders' attention for high-impact moments.** Don't pull senior or clinical leaders into low-level details. Route operational work to their delegates and involve them only for decisions and sign-offs.
- **Document decisions with owners and deadlines.** Open-ended action items get lost. Every follow-up should have a name and a date.
- **Respect escalation paths.** Don't bypass reporting structures unless there's a clear reason. Understand when someone typically escalates and through whom.

## Feedback Collection

- **Use structured formats for non-technical stakeholders.** Specific prompts yield better feedback than open-ended "any thoughts?" requests.
- **Accept varied response formats.** Some people send documents, others send videos, others send terse one-liners. Extract the substance regardless of format.
- **Track feedback items with severity and ownership.** Categorize issues by impact level so prioritization decisions are transparent.

## Sequencing & Dependencies

- **Do not start downstream work before upstream inputs are validated.** Drafting a deliverable before all data inputs arrive leads to rework.
- **Treat tentative information as tentative throughout the chain.** If input data is flagged as provisional, the outputs built on it are also provisional.
- **Parallelize independent workstreams.** Tasks without dependencies can run simultaneously. Identify these early and kick them off together.
- **Explicit approval means explicit approval.** A non-response is not approval. "Looks good" is approval. Silence is not.
