# ai-generated: 100% - drafted with ChatGPT from MONITORING-SPEC.md M-01 to M-07 and reviewed by the student

import os
import time

import httpx
from fastapi import Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Histogram, generate_latest


FIRST_DRAFT_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.11,
    0.12,
    0.13,
    0.14,
    0.15,
    0.16,
    0.18,
    0.2,
    0.25,
    0.3,
    0.4,
    0.5,
    0.75,
    1.0,
    1.5,
    2.5,
)

REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "Duration of HTTP server requests in seconds",
    (
        "http_request_method",
        "http_route",
        "http_response_status_code",
    ),
    buckets=FIRST_DRAFT_BUCKETS,
)


class UpstreamUnavailable(Exception):
    pass


_kb_client = httpx.AsyncClient(
    timeout=httpx.Timeout(3.0),
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=100,
    ),
)


async def close_kb_client() -> None:
    await _kb_client.aclose()


async def fetch_kb_hits(query: str):
    base_url = os.getenv(
        "KB_INDEX_URL",
        "http://kb-index:8080",
    ).rstrip("/")

    try:
        response = await _kb_client.get(
            f"{base_url}/search",
            params={"q": query},
        )
    except httpx.RequestError as exc:
        raise UpstreamUnavailable from exc

    if response.status_code != 200:
        raise UpstreamUnavailable

    try:
        body = response.json()
        return body["hits"]
    except (ValueError, KeyError, TypeError) as exc:
        raise UpstreamUnavailable from exc


async def observe_request(request: Request, call_next):
    # M-03 allows /metrics itself to be omitted from observation.
    if request.url.path == "/metrics":
        return await call_next(request)

    started = time.perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        elapsed = time.perf_counter() - started

        route = request.scope.get("route")
        route_template = getattr(
            route,
            "path",
            "unmatched",
        )

        REQUEST_DURATION.labels(
            http_request_method=request.method,
            http_route=route_template,
            http_response_status_code=status_code,
        ).observe(elapsed)


def prometheus_response() -> Response:
    return Response(
        content=generate_latest(),
        status_code=200,
        headers={
            "Content-Type": CONTENT_TYPE_LATEST,
        },
    )
