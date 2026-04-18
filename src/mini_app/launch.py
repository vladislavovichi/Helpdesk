from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote_plus, urlparse


@dataclass(slots=True, frozen=True)
class ResolvedMiniAppLaunch:
    init_data: str
    source: str
    client_source: str | None
    diagnostics: tuple[str, ...]

    @property
    def has_init_data(self) -> bool:
        return bool(self.init_data)


def resolve_mini_app_launch(*, path: str, headers: Mapping[str, str]) -> ResolvedMiniAppLaunch:
    diagnostics: list[str] = []
    parsed = urlparse(path)
    query = parse_qs(parsed.query, keep_blank_values=True)
    client_source = _normalize_header_value(headers.get("X-Mini-App-Launch-Source"))

    header_init_data = _normalize_header_value(headers.get("X-Telegram-Init-Data"))
    if header_init_data:
        diagnostics.append("init_data_source=x-telegram-init-data")
        return ResolvedMiniAppLaunch(
            init_data=header_init_data,
            source="header:x-telegram-init-data",
            client_source=client_source,
            diagnostics=tuple(diagnostics),
        )
    if "X-Telegram-Init-Data" in headers:
        diagnostics.append("x-telegram-init-data-header-empty")

    authorization = _normalize_header_value(headers.get("Authorization"))
    if authorization.lower().startswith("tma "):
        token = authorization[4:].strip()
        if token:
            diagnostics.append("init_data_source=authorization-tma")
            return ResolvedMiniAppLaunch(
                init_data=token,
                source="header:authorization-tma",
                client_source=client_source,
                diagnostics=tuple(diagnostics),
            )
        diagnostics.append("authorization-tma-empty")

    for key in ("tgWebAppData", "init_data"):
        value = _first_query_value(query, key)
        if value:
            diagnostics.append(f"init_data_source=query:{key}")
            return ResolvedMiniAppLaunch(
                init_data=value,
                source=f"query:{key}",
                client_source=client_source,
                diagnostics=tuple(diagnostics),
            )
        if key in query:
            diagnostics.append(f"query:{key}:empty")

    if "tgWebAppVersion" in query:
        diagnostics.append("telegram-launch-markers-present")

    diagnostics.append("init_data_missing")
    return ResolvedMiniAppLaunch(
        init_data="",
        source="missing",
        client_source=client_source,
        diagnostics=tuple(diagnostics),
    )


def _first_query_value(query: Mapping[str, list[str]], key: str) -> str:
    for raw_value in query.get(key, []):
        normalized = _decode_query_value(raw_value)
        if normalized:
            return normalized
    return ""


def _normalize_header_value(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _decode_query_value(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    for _ in range(2):
        decoded = unquote_plus(normalized).strip()
        if decoded == normalized:
            break
        normalized = decoded
    return normalized
