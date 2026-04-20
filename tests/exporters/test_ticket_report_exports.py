from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from pytest import MonkeyPatch

from application.use_cases.tickets.exports import (
    TicketReport,
    TicketReportAttachment,
    TicketReportMessage,
)
from domain.enums.tickets import TicketAttachmentKind, TicketMessageSenderType, TicketStatus
from infrastructure.exports.ticket_report_csv import render_ticket_report_csv
from infrastructure.exports.ticket_report_html import render_ticket_report_html


def test_render_ticket_report_html_embeds_local_photo(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    photo_dir = tmp_path / "photo"
    photo_dir.mkdir(parents=True, exist_ok=True)
    photo_path = photo_dir / "unique-photo.png"
    photo_path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
            "0000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082"
        )
    )
    monkeypatch.setattr(
        "infrastructure.exports.ticket_report_html.get_settings",
        lambda: SimpleNamespace(assets=SimpleNamespace(path=tmp_path)),
    )

    report = TicketReport(
        public_id=uuid4(),
        public_number="HD-ARCH0001",
        client_chat_id=2002,
        status=TicketStatus.CLOSED,
        priority="high",
        subject="Проверка фото во внутреннем отчёте",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        assigned_operator_username="ivan_petrov",
        created_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 13, 0, tzinfo=UTC),
        first_response_at=datetime(2026, 4, 7, 12, 10, tzinfo=UTC),
        first_response_seconds=600,
        closed_at=datetime(2026, 4, 7, 14, 0, tzinfo=UTC),
        category_code="access",
        category_title="Доступ и вход",
        sentiment=None,
        sentiment_confidence=None,
        sentiment_reason=None,
        sentiment_detected_at=None,
        tags=("vip",),
        feedback=None,
        messages=(
            TicketReportMessage(
                sender_type=TicketMessageSenderType.CLIENT,
                sender_operator_name=None,
                text="Скриншот ошибки во вложении",
                created_at=datetime(2026, 4, 7, 12, 1, tzinfo=UTC),
                attachment=TicketReportAttachment(
                    kind=TicketAttachmentKind.PHOTO,
                    telegram_file_id="file-1",
                    telegram_file_unique_id="unique-photo",
                    filename="screen.png",
                    mime_type="image/png",
                    storage_path="photo/unique-photo.png",
                ),
            ),
        ),
        events=(),
    )

    html = render_ticket_report_html(report).decode("utf-8")

    assert "Материалы дела" in html
    assert "data:image/png;base64," in html
    assert "Скриншот ошибки во вложении" in html
    assert "https://t.me/ivan_petrov" in html


def test_render_ticket_report_csv_sanitizes_formula_like_cells() -> None:
    report = TicketReport(
        public_id=uuid4(),
        public_number="HD-ARCH0002",
        client_chat_id=3003,
        status=TicketStatus.CLOSED,
        priority="high",
        subject="=cmd|' /C calc'!A0",
        assigned_operator_id=7,
        assigned_operator_name="@bad",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 13, 0, tzinfo=UTC),
        first_response_at=None,
        first_response_seconds=None,
        closed_at=datetime(2026, 4, 7, 14, 0, tzinfo=UTC),
        category_code="access",
        category_title="Доступ и вход",
        sentiment=None,
        sentiment_confidence=None,
        sentiment_reason=None,
        sentiment_detected_at=None,
        tags=("+urgent",),
        feedback=None,
        messages=(
            TicketReportMessage(
                sender_type=TicketMessageSenderType.CLIENT,
                sender_operator_name=None,
                text="-danger",
                created_at=datetime(2026, 4, 7, 12, 1, tzinfo=UTC),
                attachment=None,
            ),
        ),
        events=(),
    )

    csv_bytes = render_ticket_report_csv(report)
    csv_text = csv_bytes.decode("utf-8-sig")

    assert "'=cmd|' /C calc'!A0" in csv_text
    assert "'@bad" in csv_text
    assert "'+urgent" in csv_text
    assert "'-danger" in csv_text


def test_render_ticket_report_html_uses_contained_photo_layout(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    photo_dir = tmp_path / "photo"
    photo_dir.mkdir(parents=True, exist_ok=True)
    photo_path = photo_dir / "wide-photo.png"
    photo_path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
            "0000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082"
        )
    )
    monkeypatch.setattr(
        "infrastructure.exports.ticket_report_html.get_settings",
        lambda: SimpleNamespace(assets=SimpleNamespace(path=tmp_path)),
    )

    report = TicketReport(
        public_id=uuid4(),
        public_number="HD-ARCH0003",
        client_chat_id=2002,
        status=TicketStatus.CLOSED,
        priority="normal",
        subject="Проверка новой фотогалереи",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 13, 0, tzinfo=UTC),
        first_response_at=datetime(2026, 4, 7, 12, 10, tzinfo=UTC),
        first_response_seconds=600,
        closed_at=datetime(2026, 4, 7, 14, 0, tzinfo=UTC),
        category_code="access",
        category_title="Доступ и вход",
        sentiment=None,
        sentiment_confidence=None,
        sentiment_reason=None,
        sentiment_detected_at=None,
        tags=(),
        feedback=None,
        messages=(
            TicketReportMessage(
                sender_type=TicketMessageSenderType.CLIENT,
                sender_operator_name=None,
                text="Прикладываю широкий скриншот.",
                created_at=datetime(2026, 4, 7, 12, 1, tzinfo=UTC),
                attachment=TicketReportAttachment(
                    kind=TicketAttachmentKind.PHOTO,
                    telegram_file_id="file-2",
                    telegram_file_unique_id="wide-photo",
                    filename="wide.png",
                    mime_type="image/png",
                    storage_path="photo/wide-photo.png",
                ),
            ),
        ),
        events=(),
    )

    html = render_ticket_report_html(report).decode("utf-8")

    assert "object-fit: contain" in html
    assert 'class="asset-media"' in html


def test_render_ticket_report_html_uses_first_attachment_as_case_summary() -> None:
    report = TicketReport(
        public_id=uuid4(),
        public_number="HD-ARCH0004",
        client_chat_id=2002,
        status=TicketStatus.CLOSED,
        priority="normal",
        subject="Обращение клиента",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 13, 0, tzinfo=UTC),
        first_response_at=datetime(2026, 4, 7, 12, 10, tzinfo=UTC),
        first_response_seconds=600,
        closed_at=datetime(2026, 4, 7, 14, 0, tzinfo=UTC),
        category_code="access",
        category_title="Доступ и вход",
        sentiment=None,
        sentiment_confidence=None,
        sentiment_reason=None,
        sentiment_detected_at=None,
        tags=(),
        feedback=None,
        messages=(
            TicketReportMessage(
                sender_type=TicketMessageSenderType.CLIENT,
                sender_operator_name=None,
                text=None,
                created_at=datetime(2026, 4, 7, 12, 1, tzinfo=UTC),
                attachment=TicketReportAttachment(
                    kind=TicketAttachmentKind.DOCUMENT,
                    telegram_file_id="file-2",
                    telegram_file_unique_id="file-unique-2",
                    filename="issue.pdf",
                    mime_type="application/pdf",
                    storage_path="document/file-unique-2.pdf",
                ),
            ),
        ),
        events=(),
    )

    html = render_ticket_report_html(report).decode("utf-8")

    assert "Файл · issue.pdf" in html
    assert "document/file-unique-2.pdf" in html
