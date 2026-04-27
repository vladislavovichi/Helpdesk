from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from application.contracts.ai import (
    AICategoryOption,
    AIContextAttachment,
    AIContextInternalNote,
    AIContextMessage,
    AIPredictTicketCategoryCommand,
    AIReplyDraftSummaryContext,
    GenerateTicketReplyDraftCommand,
    GenerateTicketSummaryCommand,
    MacroCandidate,
    SuggestMacrosCommand,
)
from domain.enums.tickets import TicketAttachmentKind, TicketMessageSenderType, TicketStatus

BASE_TIME = datetime(2026, 4, 21, 9, 0, tzinfo=UTC)

DEFAULT_CATEGORIES = (
    AICategoryOption(id=1, code="access", title="Доступ"),
    AICategoryOption(id=2, code="billing", title="Оплата"),
    AICategoryOption(id=3, code="delivery", title="Доставка"),
    AICategoryOption(id=4, code="technical", title="Техническая проблема"),
)

DEFAULT_MACROS = (
    MacroCandidate(
        id=10,
        title="Запрос деталей",
        body="Пожалуйста, пришлите номер заказа и скриншот ошибки.",
    ),
    MacroCandidate(
        id=20,
        title="Проверим вручную",
        body="Мы проверим обращение и вернёмся с ответом.",
    ),
    MacroCandidate(
        id=30,
        title="Проблема решена",
        body="Рады, что вопрос удалось решить. Обращайтесь, если потребуется помощь.",
    ),
)


@dataclass(frozen=True, slots=True)
class TicketAIFixture:
    name: str
    ticket_public_id: UUID
    subject: str
    status: TicketStatus
    category_title: str | None
    tags: tuple[str, ...]
    message_history: tuple[AIContextMessage, ...]
    internal_notes: tuple[AIContextInternalNote, ...] = ()
    categories: tuple[AICategoryOption, ...] = DEFAULT_CATEGORIES
    macros: tuple[MacroCandidate, ...] = DEFAULT_MACROS
    prediction_text: str | None = None
    prediction_attachment: AIContextAttachment | None = None
    reply_summary: AIReplyDraftSummaryContext | None = None

    def summary_command(self) -> GenerateTicketSummaryCommand:
        return GenerateTicketSummaryCommand(
            ticket_public_id=self.ticket_public_id,
            subject=self.subject,
            status=self.status,
            category_title=self.category_title,
            tags=self.tags,
            message_history=self.message_history,
            internal_notes=self.internal_notes,
        )

    def macro_command(self) -> SuggestMacrosCommand:
        return SuggestMacrosCommand(
            ticket_public_id=self.ticket_public_id,
            subject=self.subject,
            status=self.status,
            category_title=self.category_title,
            tags=self.tags,
            message_history=self.message_history,
            macros=self.macros,
        )

    def category_command(self) -> AIPredictTicketCategoryCommand:
        return AIPredictTicketCategoryCommand(
            text=self.prediction_text,
            attachment=self.prediction_attachment,
            categories=self.categories,
        )

    def reply_draft_command(
        self,
        *,
        include_summary: bool = True,
    ) -> GenerateTicketReplyDraftCommand:
        return GenerateTicketReplyDraftCommand(
            ticket_public_id=self.ticket_public_id,
            subject=self.subject,
            status=self.status,
            category_title=self.category_title,
            tags=self.tags,
            message_history=self.message_history,
            internal_notes=self.internal_notes,
            summary=self.reply_summary if include_summary else None,
        )


def get_ai_fixture(name: str) -> TicketAIFixture:
    return AI_QUALITY_FIXTURES[name]


def customer_message(
    text: str | None,
    *,
    offset_minutes: int,
    sender_label: str | None = "Мария",
    attachment: AIContextAttachment | None = None,
) -> AIContextMessage:
    return AIContextMessage(
        sender_type=TicketMessageSenderType.CLIENT,
        sender_label=sender_label,
        text=text,
        created_at=BASE_TIME + timedelta(minutes=offset_minutes),
        attachment=attachment,
    )


def operator_message(
    text: str,
    *,
    offset_minutes: int,
    sender_label: str | None = "Олег",
) -> AIContextMessage:
    return AIContextMessage(
        sender_type=TicketMessageSenderType.OPERATOR,
        sender_label=sender_label,
        text=text,
        created_at=BASE_TIME + timedelta(minutes=offset_minutes),
    )


def internal_note(text: str, *, offset_minutes: int) -> AIContextInternalNote:
    return AIContextInternalNote(
        author_name="Старший оператор",
        text=text,
        created_at=BASE_TIME + timedelta(minutes=offset_minutes),
    )


def _long_history() -> tuple[AIContextMessage, ...]:
    messages: list[AIContextMessage] = []
    for index in range(25):
        if index % 2 == 0:
            messages.append(
                customer_message(
                    f"long-history-customer-message-{index + 1:02d}",
                    offset_minutes=index,
                )
            )
        else:
            messages.append(
                operator_message(
                    f"long-history-operator-message-{index + 1:02d}",
                    offset_minutes=index,
                )
            )
    return tuple(messages)


AI_QUALITY_FIXTURES: dict[str, TicketAIFixture] = {
    "short_ticket_missing_details": TicketAIFixture(
        name="short_ticket_missing_details",
        ticket_public_id=UUID(int=101),
        subject="Нужна помощь",
        status=TicketStatus.NEW,
        category_title=None,
        tags=("new",),
        message_history=(customer_message("Помогите, пожалуйста.", offset_minutes=0),),
        prediction_text="Помогите, пожалуйста.",
        reply_summary=None,
    ),
    "angry_customer": TicketAIFixture(
        name="angry_customer",
        ticket_public_id=UUID(int=102),
        subject="Оплата прошла, доступа нет",
        status=TicketStatus.ASSIGNED,
        category_title="Оплата",
        tags=("billing", "frustrated"),
        message_history=(
            customer_message(
                "Я уже заплатил, а доступа нет. Сколько можно ждать?",
                offset_minutes=0,
            ),
            operator_message("Проверяем платёж по заявке.", offset_minutes=4),
        ),
        internal_notes=(
            internal_note(
                "Внутренний billing_check_id=BX-771 не раскрывать клиенту.",
                offset_minutes=5,
            ),
        ),
        prediction_text="Я уже заплатил, а доступа нет.",
        reply_summary=AIReplyDraftSummaryContext(
            short_summary="Клиент оплатил, но не видит доступ.",
            user_goal="Получить доступ после оплаты.",
            actions_taken="Оператор начал проверку платежа.",
            current_status="Проверка ещё не завершена.",
        ),
    ),
    "attachment_only_ticket": TicketAIFixture(
        name="attachment_only_ticket",
        ticket_public_id=UUID(int=103),
        subject="Скриншот ошибки",
        status=TicketStatus.QUEUED,
        category_title=None,
        tags=("attachment",),
        message_history=(
            customer_message(
                None,
                offset_minutes=0,
                attachment=AIContextAttachment(
                    kind=TicketAttachmentKind.PHOTO,
                    filename="error-screen.png",
                    mime_type="image/png",
                ),
            ),
        ),
        prediction_text=None,
        prediction_attachment=AIContextAttachment(
            kind=TicketAttachmentKind.PHOTO,
            filename="error-screen.png",
            mime_type="image/png",
        ),
    ),
    "long_conversation": TicketAIFixture(
        name="long_conversation",
        ticket_public_id=UUID(int=104),
        subject="Долгая переписка по доставке",
        status=TicketStatus.ASSIGNED,
        category_title="Доставка",
        tags=("delivery", "long"),
        message_history=_long_history(),
        internal_notes=(
            internal_note(
                "Проверить последние сообщения, старые детали устарели.",
                offset_minutes=26,
            ),
        ),
        prediction_text="Не могу понять статус доставки после долгой переписки.",
    ),
    "already_resolved_ticket": TicketAIFixture(
        name="already_resolved_ticket",
        ticket_public_id=UUID(int=105),
        subject="Вход восстановлен",
        status=TicketStatus.CLOSED,
        category_title="Доступ",
        tags=("resolved",),
        message_history=(
            customer_message("Не могу войти в кабинет.", offset_minutes=0),
            operator_message("Мы сбросили временный пароль.", offset_minutes=5),
            customer_message("Спасибо, теперь всё работает.", offset_minutes=8),
        ),
        prediction_text="Спасибо, теперь всё работает.",
        reply_summary=AIReplyDraftSummaryContext(
            short_summary="Доступ восстановлен, клиент подтвердил решение.",
            user_goal="Закрыть вопрос по входу.",
            actions_taken="Оператор помог восстановить вход.",
            current_status="Клиент подтвердил, что всё работает.",
        ),
    ),
    "escalation_required": TicketAIFixture(
        name="escalation_required",
        ticket_public_id=UUID(int=106),
        subject="Нужно изменить данные аккаунта",
        status=TicketStatus.ESCALATED,
        category_title="Доступ",
        tags=("admin", "escalated"),
        message_history=(
            customer_message(
                "Нужно срочно поменять телефон в аккаунте, сам сделать не могу.",
                offset_minutes=0,
            ),
            operator_message("Передали запрос администратору на проверку.", offset_minutes=7),
        ),
        internal_notes=(
            internal_note(
                "Нужна проверка владельца аккаунта перед изменением телефона.",
                offset_minutes=8,
            ),
        ),
        prediction_text="Нужно поменять телефон в аккаунте.",
    ),
    "ambiguous_category": TicketAIFixture(
        name="ambiguous_category",
        ticket_public_id=UUID(int=107),
        subject="Не получается завершить заказ",
        status=TicketStatus.NEW,
        category_title=None,
        tags=("ambiguous",),
        message_history=(
            customer_message(
                "Не получается завершить заказ: то оплата, то доставка не выбирается.",
                offset_minutes=0,
            ),
        ),
        prediction_text="Не получается завершить заказ: то оплата, то доставка не выбирается.",
    ),
    "no_prediction_signal": TicketAIFixture(
        name="no_prediction_signal",
        ticket_public_id=UUID(int=108),
        subject="Пустое обращение",
        status=TicketStatus.NEW,
        category_title=None,
        tags=("empty",),
        message_history=(customer_message("   ", offset_minutes=0),),
        prediction_text="   ",
    ),
}
