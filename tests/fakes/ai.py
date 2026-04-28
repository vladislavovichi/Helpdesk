from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from application.contracts.ai import (
    AIPredictedCategoryResult,
    AIPredictTicketCategoryCommand,
    AIServiceClient,
    AIServiceClientFactory,
    AnalyzedTicketSentimentResult,
    AnalyzeTicketSentimentCommand,
    GeneratedTicketReplyDraftResult,
    GeneratedTicketSummaryResult,
    GenerateTicketReplyDraftCommand,
    GenerateTicketSummaryCommand,
    SuggestedMacrosResult,
    SuggestMacrosCommand,
)


class DisabledTestAIClient(AIServiceClient):
    async def get_service_status(self) -> tuple[str, str]:
        return "helpdesk-ai-service", "ready"

    async def generate_ticket_summary(
        self,
        command: GenerateTicketSummaryCommand,
    ) -> GeneratedTicketSummaryResult:
        del command
        return GeneratedTicketSummaryResult(available=False)

    async def suggest_macros(self, command: SuggestMacrosCommand) -> SuggestedMacrosResult:
        del command
        return SuggestedMacrosResult(available=False)

    async def generate_ticket_reply_draft(
        self,
        command: GenerateTicketReplyDraftCommand,
    ) -> GeneratedTicketReplyDraftResult:
        del command
        return GeneratedTicketReplyDraftResult(available=False)

    async def predict_ticket_category(
        self,
        command: AIPredictTicketCategoryCommand,
    ) -> AIPredictedCategoryResult:
        del command
        return AIPredictedCategoryResult(available=False)

    async def analyze_ticket_sentiment(
        self,
        command: AnalyzeTicketSentimentCommand,
    ) -> AnalyzedTicketSentimentResult:
        del command
        return AnalyzedTicketSentimentResult(available=False)


class StubSentimentAIClient(DisabledTestAIClient):
    def __init__(self, result: AnalyzedTicketSentimentResult) -> None:
        self.result = result
        self.commands: list[AnalyzeTicketSentimentCommand] = []

    async def analyze_ticket_sentiment(
        self,
        command: AnalyzeTicketSentimentCommand,
    ) -> AnalyzedTicketSentimentResult:
        self.commands.append(command)
        return self.result


def build_ai_client_factory(client: AIServiceClient | None = None) -> AIServiceClientFactory:
    @asynccontextmanager
    async def provide() -> AsyncIterator[AIServiceClient]:
        yield client or DisabledTestAIClient()

    return provide
