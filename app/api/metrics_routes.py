from __future__ import annotations

from fastapi import APIRouter
from fastapi import Response

from app.api.authz import ensure_admin
from app.api.dependencies import CurrentUser

router = APIRouter(tags=["Observability"])


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics(current_user: CurrentUser) -> Response:
    """Expose Prometheus metrics in text format.

    Restricted to administrators: it leaks operational figures (claim
    volumes, payout totals). Scrapers should authenticate with an admin
    token or be confined to an internal network."""
    ensure_admin(current_user)
    try:
        from prometheus_client import CONTENT_TYPE_LATEST
        from prometheus_client import generate_latest

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    except ImportError:
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain",
        )


@router.get("/metrics/summary")
def metrics_summary(current_user: CurrentUser) -> dict:
    """Human-readable metric snapshot for dashboards and health checks."""
    ensure_admin(current_user)
    try:
        from prometheus_client import REGISTRY

        output: dict[str, object] = {}
        for metric in REGISTRY.collect():
            for sample in metric.samples:
                output[sample.name] = sample.value
        return {"metrics": output}
    except ImportError:
        return {"metrics": {}, "note": "prometheus_client not installed"}
