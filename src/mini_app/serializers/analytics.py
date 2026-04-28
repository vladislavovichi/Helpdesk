from __future__ import annotations

from typing import Any

from application.services.stats import HelpdeskAnalyticsSnapshot
from mini_app import serializers_analytics


def serialize_analytics_snapshot(snapshot: HelpdeskAnalyticsSnapshot) -> dict[str, Any]:
    return serializers_analytics.serialize_analytics_snapshot(snapshot)
