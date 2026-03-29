from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from application.services.helpdesk import HelpdeskServiceFactory

router = Router(name="client")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_client_text(
    message: Message,
    helpdesk_service_factory: HelpdeskServiceFactory,
) -> None:
    if message.text is None:
        return

    async with helpdesk_service_factory() as helpdesk_service:
        ticket = await helpdesk_service.create_ticket_from_client_message(
            client_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            text=message.text,
        )

    await message.answer(
        f"Ticket {ticket.public_number} created. "
        "An operator will respond in a later iteration."
    )
