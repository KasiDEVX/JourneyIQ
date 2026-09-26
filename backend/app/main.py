# -*- coding: utf-8 -*-
"""
backend/app/main.py

FastAPI application entry point — Stage 5 + Stage 7 + Stage 8A Hardening.

Endpoints:
  GET /api/health                               — liveness probe (Stage 1)
  GET /api/ready                                — database readiness probe (Stage 8A)
  GET /api/customers/{customer_id}/journey      — full journey (Stage 3)
  GET /api/customers/{customer_id}/journey/summary — summary metrics (Stage 3)
  GET /api/analytics/overview                   — platform KPI summary (Stage 5)
  GET /api/analytics/channels                   — channel performance breakdown (Stage 5)
  GET /api/analytics/attribution                — single-model attribution (Stage 5)
  GET /api/analytics/attribution/compare        — multi-model comparison (Stage 5)
  GET /api/analytics/journeys                   — journey path pattern analysis (Stage 5)
  GET /api/analytics/journey-flow               — interactive journey flow graph (Stage 7)

Security Controls (Stage 8A):
  - Configurable environment-driven CORS with production wildcard rejection
  - Configurable TrustedHostMiddleware
  - HTTP Security Headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
  - Traceback & internal exception sanitization across all responses
  - Parameterized SQL execution & path parameter validation
  - Structured request logging with X-Request-ID propagation
"""

import logging
import re
import sys
import time
import uuid
from pathlib import Path

# Ensure backend/ and project root are on sys.path so all import styles
# (backend.app... and app...) resolve seamlessly in both local and production ASGI runners.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import (
    get_db,
    check_db_connection,
    check_required_tables,
    check_db_readiness,
)
from app.services.journey_service import (
    CustomerJourney,
    JourneySummary,
    get_customer_journey,
)
from app.services.analytics import (
    OverviewAnalytics,
    ChannelAnalytics,
    AttributionAnalytics,
    AttributionComparison,
    JourneyPattern,
    JourneyFlowResponse,
    get_overview_analytics,
    get_channel_analytics,
    get_attribution_analytics,
    get_attribution_comparison,
    get_journey_patterns,
    get_journey_flow,
)
from app.services.attribution.engine import SUPPORTED_MODELS

# Configure module-level logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Customer Journey Mapping and Channel Attribution API.\n\n"
        "Stage 5 adds comprehensive analytics services: cohort KPI overview, "
        "channel performance, multi-touch attribution, model comparison, "
        "and journey path patterns.\n"
        "Stage 7 adds interactive journey network flow analysis.\n"
        "Stage 8A hardens security, CORS, headers, and request tracking."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middlewares (Stage 8A Hardening) ──────────────────────────────────────────

# 1. CORS Middleware — strictly configurable via environment variables
cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Trusted Host Middleware (if configured)
allowed_hosts = settings.allowed_hosts_list
if allowed_hosts != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )


# 3. Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Inject defensive HTTP response headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# 4. Request Logging & X-Request-ID Propagation Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Log every HTTP request with execution duration and unique request ID.
    Validates client-supplied X-Request-ID or generates a clean UUID.
    Never logs credentials, passwords, or database URLs.
    """
    client_req_id = request.headers.get("X-Request-ID")
    if client_req_id and REQUEST_ID_REGEX.match(client_req_id):
        request_id = client_req_id
    else:
        request_id = uuid.uuid4().hex

    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "Unhandled exception [request_id=%s] %s %s (%.2fms): %s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
            exc,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "%s %s %d (%.2fms) [request_id=%s]",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


# 5. Global Unhandled Exception Sanitizer
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Intercept uncaught exceptions to ensure stack traces, filesystem paths,
    and internal database error details are never exposed to clients.
    """
    logger.exception(
        "Internal server error processing %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    request_id = getattr(request.state, "request_id", None)
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal error processing request. Check server logs."},
        headers=headers,
    )


# ── Input validation helpers ──────────────────────────────────────────────────

def _validate_customer_id(customer_id: str) -> str:
    """Validate customer_id against injection, null bytes, and buffer limits."""
    if "\x00" in customer_id or len(customer_id) > 128:
        raise HTTPException(
            status_code=400,
            detail="Invalid customer ID format.",
        )
    return customer_id


# ── Health & Readiness checks ─────────────────────────────────────────────────

@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check (liveness probe)",
    description="Lightweight liveness probe. Returns HTTP 200 if the API process is alive.",
)
def health_check():
    """Lightweight liveness probe."""
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "service": "journeyiq-api"},
    )


@app.get(
    "/api/ready",
    tags=["System"],
    summary="Readiness check",
    description="Verifies database connectivity and required tables. Returns HTTP 200 if ready, HTTP 503 if unreachable or tables missing.",
)
def readiness_check():
    """
    Readiness probe verifying database connectivity and required tables.
    Does NOT leak connection strings, credentials, or internal exception details.
    """
    if not check_db_connection():
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "disconnected"},
        )

    tables_ok, _ = check_required_tables()
    if not tables_ok:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "connected",
                "message": "Required database tables are missing",
            },
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ready", "database": "connected"},
    )


# ── Journey endpoints ─────────────────────────────────────────────────────────

@app.get(
    "/api/customers/{customer_id}/journey",
    response_model=CustomerJourney,
    tags=["Journeys"],
    summary="Full customer journey",
    description=(
        "Returns the complete structured journey for a customer: "
        "all events grouped into sessions, marketing touchpoints, "
        "channel path, and conversion status."
    ),
)
def get_journey(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """Build and return the full journey for one customer."""
    logger.info("GET /api/customers/%s/journey", customer_id)
    _validate_customer_id(customer_id)

    try:
        journey = get_customer_journey(customer_id, db)
    except Exception as exc:
        logger.exception("Unexpected error building journey for %s", customer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal error building customer journey. Check server logs.",
        ) from exc

    if journey is None:
        raise HTTPException(
            status_code=404,
            detail=f"Customer '{customer_id}' not found.",
        )

    return journey


@app.get(
    "/api/customers/{customer_id}/journey/summary",
    response_model=JourneySummary,
    tags=["Journeys"],
    summary="Journey summary metrics",
    description=(
        "Returns only summary metrics for a customer journey — "
        "no event or session details. Faster and lighter than the full journey."
    ),
)
def get_journey_summary(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """Return a lightweight summary of the customer's journey."""
    logger.info("GET /api/customers/%s/journey/summary", customer_id)
    _validate_customer_id(customer_id)

    try:
        journey = get_customer_journey(customer_id, db)
    except Exception as exc:
        logger.exception("Unexpected error building journey summary for %s", customer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal error building journey summary. Check server logs.",
        ) from exc

    if journey is None:
        raise HTTPException(
            status_code=404,
            detail=f"Customer '{customer_id}' not found.",
        )

    return JourneySummary(
        customer_id              = journey.customer_id,
        converted                = journey.converted,
        conversion_revenue       = journey.conversion_revenue,
        journey_duration_minutes = journey.journey_duration_minutes,
        event_count              = journey.event_count,
        session_count            = journey.session_count,
        touchpoint_count         = journey.touchpoint_count,
        unique_channel_count     = journey.unique_channel_count,
        channels                 = journey.channels,
    )


# ── Analytics endpoints ───────────────────────────────────────────────────────

@app.get(
    "/api/analytics/overview",
    response_model=OverviewAnalytics,
    tags=["Analytics"],
    summary="Platform KPI Overview",
    description=(
        "Returns cohort-level marketing performance indicators including total "
        "customers, events, sessions, conversions, conversion rate, total revenue, "
        "average order value, journey duration, and touchpoints."
    ),
)
def get_overview(db: Session = Depends(get_db)):
    """Fetch and calculate platform-wide cohort KPI summary."""
    logger.info("GET /api/analytics/overview")
    try:
        return get_overview_analytics(db)
    except Exception as exc:
        logger.exception("Unexpected error calculating overview analytics")
        raise HTTPException(
            status_code=500,
            detail="Internal error calculating overview analytics. Check server logs.",
        ) from exc


@app.get(
    "/api/analytics/channels",
    response_model=list[ChannelAnalytics],
    tags=["Analytics"],
    summary="Channel Performance Breakdown",
    description=(
        "Returns engagement, conversion, and revenue metrics for each marketing "
        "channel. Sorted by revenue descending."
    ),
)
def get_channels(db: Session = Depends(get_db)):
    """Fetch and calculate performance metrics for each marketing channel."""
    logger.info("GET /api/analytics/channels")
    try:
        return get_channel_analytics(db)
    except Exception as exc:
        logger.exception("Unexpected error calculating channel analytics")
        raise HTTPException(
            status_code=500,
            detail="Internal error calculating channel analytics. Check server logs.",
        ) from exc


@app.get(
    "/api/analytics/attribution",
    response_model=AttributionAnalytics,
    tags=["Analytics"],
    summary="Channel Attribution by Model",
    description=(
        "Calculates multi-touch attribution across all converted customer journeys "
        "using the requested attribution algorithm. Supported models: first_touch, "
        "last_touch, linear, time_decay, position_based, markov."
    ),
)
def get_attribution(
    model: str = Query("linear", description="Attribution algorithm name"),
    db: Session = Depends(get_db),
):
    """Calculate cohort attribution for the specified attribution model."""
    logger.info("GET /api/analytics/attribution?model=%s", model)
    model_clean = model.strip().lower()
    if model_clean not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid attribution model: '{model}'. "
                f"Supported models are: {', '.join(SUPPORTED_MODELS)}."
            ),
        )

    try:
        return get_attribution_analytics(db, model=model_clean)
    except Exception as exc:
        logger.exception("Unexpected error calculating attribution for model %s", model)
        raise HTTPException(
            status_code=500,
            detail="Internal error calculating attribution analytics. Check server logs.",
        ) from exc


@app.get(
    "/api/analytics/attribution/compare",
    response_model=AttributionComparison,
    tags=["Analytics"],
    summary="Attribution Model Comparison",
    description=(
        "Computes and returns side-by-side channel credit and attributed revenue "
        "allocations across all six attribution models."
    ),
)
def get_attribution_compare(db: Session = Depends(get_db)):
    """Run all 6 attribution models over the journey collection for comparison."""
    logger.info("GET /api/analytics/attribution/compare")
    try:
        return get_attribution_comparison(db)
    except Exception as exc:
        logger.exception("Unexpected error comparing attribution models")
        raise HTTPException(
            status_code=500,
            detail="Internal error comparing attribution models. Check server logs.",
        ) from exc


@app.get(
    "/api/analytics/journeys",
    response_model=list[JourneyPattern],
    tags=["Analytics"],
    summary="Journey Path Pattern Analysis",
    description=(
        "Groups customers by their ordered channel sequence to identify the most common "
        "and highest-converting multi-touch paths."
    ),
)
def get_journeys(
    limit: int = Query(20, description="Max number of journey patterns to return"),
    db: Session = Depends(get_db),
):
    """Aggregate customer journeys by unique channel paths."""
    logger.info("GET /api/analytics/journeys?limit=%s", limit)
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=400,
            detail="Limit must be a positive integer between 1 and 1000.",
        )

    try:
        return get_journey_patterns(db, limit=limit)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err)) from val_err
    except Exception as exc:
        logger.exception("Unexpected error calculating journey patterns")
        raise HTTPException(
            status_code=500,
            detail="Internal error calculating journey patterns. Check server logs.",
        ) from exc


# ── Journey Flow endpoint (Stage 7) ──────────────────────────────────────────

VALID_CONVERSION_FILTERS = frozenset({"all", "converted", "non_converted"})


@app.get(
    "/api/analytics/journey-flow",
    response_model=JourneyFlowResponse,
    tags=["Analytics"],
    summary="Interactive Customer Journey Flow Graph",
    description=(
        "Constructs a directional flow graph showing how customers move between "
        "marketing channels before conversion. "
        "Nodes represent channels and special states (__START__, __CONVERSION__). "
        "Links are aggregated transitions with journey counts as weights. "
        "The `limit` parameter controls how many journeys are used to build the "
        "graph — it does NOT cap the number of links returned."
    ),
)
def get_journey_flow_endpoint(
    conversion: str = Query(
        "all",
        description=(
            "Filter journeys by conversion status. "
            "One of: 'all' (default), 'converted', 'non_converted'."
        ),
    ),
    limit: int = Query(
        1000,
        ge=1,
        le=5000,
        description=(
            "Maximum number of journeys to include in flow construction (1–5000). "
            "Applied after conversion filtering. "
            "Does NOT limit the number of links returned."
        ),
    ),
    db: Session = Depends(get_db),
):
    """Build and return the customer journey flow graph."""
    logger.info(
        "GET /api/analytics/journey-flow?conversion=%s&limit=%d", conversion, limit
    )

    # Validate conversion filter
    conversion_clean = conversion.strip().lower()
    if conversion_clean not in VALID_CONVERSION_FILTERS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid conversion filter: '{conversion}'. "
                f"Supported values are: all, converted, non_converted."
            ),
        )

    try:
        return get_journey_flow(db, conversion_filter=conversion_clean, limit=limit)
    except Exception as exc:
        logger.exception("Unexpected error building journey flow graph")
        raise HTTPException(
            status_code=500,
            detail="Internal error building journey flow graph. Check server logs.",
        ) from exc


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)

