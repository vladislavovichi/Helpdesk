from __future__ import annotations

from dataclasses import dataclass

from domain.enums.tickets import TicketAttachmentKind


@dataclass(slots=True, frozen=True)
class PredictTicketCategoryCommand:
    text: str | None
    attachment_kind: TicketAttachmentKind | None = None
    attachment_filename: str | None = None
    attachment_mime_type: str | None = None
