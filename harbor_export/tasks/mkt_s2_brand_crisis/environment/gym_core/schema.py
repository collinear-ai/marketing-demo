"""
Shared schema for the action log, verifier results, and rubric scores.

The ActionType enum is a superset covering all scenarios across all domains.
When adding a new scenario, reuse existing values where semantically correct
before adding a new one. Scenarios that need a truly bespoke action can use
ActionType.CUSTOM and put the specific kind in Action.metadata["custom_kind"].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActionType(str, Enum):
    # --- messaging ---
    SLACK_MESSAGE = "slack_message"
    SLACK_REACTION = "slack_reaction"
    TEAMS_MESSAGE = "teams_message"
    SMS = "sms"
    VOICE_MEMO = "voice_memo"

    # --- email ---
    EMAIL = "email"
    ENCRYPTED_EMAIL = "encrypted_email"
    EMAIL_REPLY = "email_reply"
    EMAIL_FORWARD = "email_forward"

    # --- calendar & meetings ---
    CALENDAR_INVITE = "calendar_invite"
    CALENDAR_UPDATE = "calendar_update"
    CALENDAR_CANCEL = "calendar_cancel"
    VIDEO_CALL = "video_call"
    PHONE_CALL = "phone_call"

    # --- documents ---
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_EDIT = "document_edit"
    DOCUMENT_SHARE = "document_share"
    DOCUMENT_COMMENT = "document_comment"
    SPREADSHEET_CREATE = "spreadsheet_create"
    SPREADSHEET_EDIT = "spreadsheet_edit"
    SLIDE_CREATE = "slide_create"
    SLIDE_EDIT = "slide_edit"
    PDF_CREATE = "pdf_create"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"

    # --- knowledge bases & wikis ---
    NOTION_PAGE = "notion_page"
    NOTION_TASK = "notion_task"
    CONFLUENCE_PAGE = "confluence_page"
    WIKI_EDIT = "wiki_edit"

    # --- ticketing & work tracking ---
    JIRA_TICKET = "jira_ticket"
    JIRA_SUBTASK = "jira_subtask"
    JIRA_COMMENT = "jira_comment"
    LINEAR_TICKET = "linear_ticket"
    SERVICENOW_TICKET = "servicenow_ticket"
    ZENDESK_TICKET = "zendesk_ticket"
    FRESHDESK_TICKET = "freshdesk_ticket"

    # --- CRM ---
    SALESFORCE_UPDATE = "salesforce_update"
    SALESFORCE_QUERY = "salesforce_query"
    HUBSPOT_UPDATE = "hubspot_update"
    GONG_QUERY = "gong_query"

    # --- HR systems ---
    HRIS_ACTION = "hris_action"          # Workday, BambooHR, etc.
    PERFORMANCE_REVIEW = "performance_review"

    # --- procurement / finance / legal ---
    DOCUSIGN_ENVELOPE = "docusign_envelope"
    SIGNATURE_REQUEST = "signature_request"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_GRANT = "approval_grant"
    APPROVAL_REJECT = "approval_reject"
    PROCUREMENT_REQUEST = "procurement_request"
    VENDOR_ACTION = "vendor_action"
    INVOICE_ACTION = "invoice_action"
    BUDGET_ENTRY = "budget_entry"
    JOURNAL_ENTRY = "journal_entry"

    # --- marketing stack ---
    MARKETING_CAMPAIGN = "marketing_campaign"
    AD_CREATIVE = "ad_creative"
    EMAIL_CAMPAIGN = "email_campaign"
    ANALYTICS_QUERY = "analytics_query"
    DASHBOARD_VIEW = "dashboard_view"
    REPORT_EXPORT = "report_export"

    # --- infra / engineering (kept for cross-domain use) ---
    AWS_ACTION = "aws_action"
    GITHUB_ACTION = "github_action"
    PAGERDUTY_ACTION = "pagerduty_action"

    # --- escape hatch ---
    CUSTOM = "custom"


@dataclass
class Action:
    """
    A single action taken by the agent, as recorded in the action log.

    The log is the canonical input to all verifiers. Verifiers MUST NOT reach
    past the log into free-text tool outputs; anything that needs to be checked
    should be surfaced on this dataclass or in ``metadata``.
    """
    action_type: ActionType
    timestamp: datetime
    tool: str                                    # "slack", "gmail", "workday", ...

    # --- recipients & channels ---
    recipient: str | None = None                 # persona_id, channel name, or group
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    channel: str | None = None                   # "dm", "#incidents", "encrypted_outlook"

    # --- content ---
    subject: str | None = None
    body: str | None = None
    attachments: list[str] = field(default_factory=list)

    # --- meetings ---
    attendees: list[str] = field(default_factory=list)
    duration_minutes: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    # --- compliance / classification ---
    classification: str | None = None            # "public", "internal", "confidential", "restricted"
    contains_pii: bool = False
    contains_phi: bool = False
    contains_financials: bool = False

    # --- finance / procurement specific ---
    amount: float | None = None
    currency: str | None = None
    approval_status: str | None = None           # "pending", "approved", "rejected"

    # --- free-form extension ---
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # convenience
    # ------------------------------------------------------------------

    def body_lower(self) -> str:
        return (self.body or "").lower()

    def subject_lower(self) -> str:
        return (self.subject or "").lower()

    def full_text_lower(self) -> str:
        return f"{self.subject_lower()} {self.body_lower()}"


@dataclass
class VerifierResult:
    """Result of a single programmatic check."""
    check_id: str                                # e.g. "T1_PC1"
    name: str
    passed: bool
    details: str
    severity: Severity = Severity.ERROR
    compliance_relevant: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
            "severity": self.severity.value,
            "compliance_relevant": self.compliance_relevant,
        }


@dataclass
class RubricScore:
    """Result of a qualitative rubric evaluation (1–5) by human or LLM judge."""
    rubric_id: str                               # e.g. "T1_R1"
    name: str
    dimension: str                               # "Persona Fidelity", "Content Quality", ...
    score: int                                   # 1..5
    justification: str
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.score <= 5:
            raise ValueError(f"RubricScore.score must be in 1..5, got {self.score}")
