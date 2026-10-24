"""The signal refresh / re-score pass, shared by the API and the scheduler.

``POST /signals/refresh`` (task 10) and the daily backend scheduler (task 38)
run the same work: for every asset, re-enrich KEV/EPSS signals, re-score the
findings, and create any new ``top tier`` notification job (idempotent per
lifecycle). Factoring it here keeps the two callers identical.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulntriage.db.models import Asset
from vulntriage.ingest.notifications import create_top_tier_jobs
from vulntriage.ingest.ranking import rank_asset
from vulntriage.ingest.signals import EpssClientProtocol, KevClientProtocol, enrich_asset


def refresh_all(
    session: Session,
    kev_client: KevClientProtocol | None,
    epss_client: EpssClientProtocol | None,
) -> None:
    """Re-enrich, re-score and create top-tier jobs for every asset.

    The caller owns the transaction (commits). A feed failure during enrichment
    marks signals stale and never raises (E3). Creating jobs is idempotent via
    the lifecycle key, so a second call the same day makes no second job (US-8).
    """
    for asset_id in list(session.scalars(select(Asset.id))):
        if kev_client is not None or epss_client is not None:
            enrich_asset(session, asset_id, kev_client, epss_client)
        rank_asset(session, asset_id)
        create_top_tier_jobs(session, asset_id)
