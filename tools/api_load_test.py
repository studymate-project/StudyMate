#!/usr/bin/env python3
"""Small, fail-closed read-only HTTP smoke/load harness for StudyMate.

This intentionally uses only the Python standard library. It does not retry
requests, create accounts, upload files, or call mutating API endpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


TOOL_VERSION = "1.0"
DEFAULT_DURATION_SECONDS = 10.0
DEFAULT_CONCURRENCY = 1
DEFAULT_RATE_PER_SECOND = 1.0
DEFAULT_MAX_REQUESTS = 20
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_RESPONSE_BYTES = 1_048_576
MAX_DURATION_SECONDS = 300.0
MAX_CONCURRENCY = 20
MAX_RATE_PER_SECOND = 20.0
MAX_REQUESTS = 2_000
MAX_TIMEOUT_SECONDS = 30.0

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
STAGING_MARKERS = ("staging", "stage", "qa", "test", "dev")
PRODUCTION_MARKERS = ("prod", "production", "live")
PRODUCTION_SERVICE_SUFFIXES = (
    ".onrender.com",
    ".neon.tech",
    ".upstash.io",
    ".upstash.com",
)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, msg, headers, newurl):
        return None


_HTTP_OPENER = build_opener(_NoRedirectHandler)

ENDPOINTS: dict[str, tuple[str, bool]] = {
    "health": ("/api/health/", False),
    "search": ("/api/search/?q=load-test-smoke&limit=5&offset=0", False),
    "resources": ("/api/resources/?page=1&page_size=5", False),
    "videos": ("/api/videos/?page=1&page_size=5", False),
    "questions": ("/api/questions/?page=1&page_size=5", False),
    "subjects": ("/api/resources/subjects/", True),
    "notifications": ("/api/notifications/?page=1&page_size=5", True),
    "profile": ("/api/auth/me/", True),
}


class SafetyError(ValueError):
    """Raised when the harness cannot prove that a target is safe."""


@dataclass(frozen=True)
class Target:
    base_url: str
    environment: str
    hostname: str


@dataclass
class RequestResult:
    latency_ms: float
    status: int | None
    error: str | None
    timed_out: bool


def _is_local_host(hostname: str) -> bool:
    if hostname in LOCAL_HOSTS:
        return True
    try:
        return socket.inet_aton(hostname).startswith(b"\x7f")
    except OSError:
        return False


def _has_marker(hostname: str, markers: tuple[str, ...]) -> bool:
    labels = hostname.replace("_", "-").split(".")
    return any(
        marker in label
        for label in labels
        if label != "test"  # Do not treat the reserved .test TLD as a staging marker.
        for marker in markers
    )


def _service_host_is_production(hostname: str) -> bool:
    return (
        _has_marker(hostname, PRODUCTION_MARKERS)
        or hostname.endswith(PRODUCTION_SERVICE_SUFFIXES)
    )


def _target_host_is_production(hostname: str) -> bool:
    # A Render hostname can be a clearly named staging service. Generic
    # provider hostnames remain blocked because the harness cannot infer their
    # deployment environment safely.
    return _has_marker(hostname, PRODUCTION_MARKERS) or (
        hostname.endswith(".onrender.com") and not _has_marker(hostname, STAGING_MARKERS)
    )


def validate_target(base_url: str, environment: str, staging_hostname: str | None) -> Target:
    """Validate the explicit HTTP target without making a request."""

    parsed = urlsplit(base_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise SafetyError("--base-url must use http:// or https://.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise SafetyError("--base-url must contain a hostname and no embedded credentials.")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise SafetyError("--base-url must not contain a path, query, or fragment.")

    hostname = parsed.hostname.casefold().rstrip(".")
    if _target_host_is_production(hostname):
        raise SafetyError("Refusing a hostname that looks like production or a production service.")

    if environment == "local":
        if not _is_local_host(hostname):
            raise SafetyError("--target-environment local requires localhost or a loopback address.")
    elif environment == "staging":
        if not staging_hostname:
            raise SafetyError("--staging-hostname is required for a staging target.")
        expected = staging_hostname.casefold().rstrip(".")
        if hostname != expected:
            raise SafetyError("--base-url hostname must exactly match --staging-hostname.")
        if not _has_marker(hostname, STAGING_MARKERS):
            raise SafetyError(
                "Staging hostnames must contain a staging/test marker such as staging, qa, or test."
            )
    else:
        raise SafetyError("--target-environment must be local or staging.")

    normalized = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
    return Target(base_url=normalized, environment=environment, hostname=hostname)


def _config_host(value: str) -> str:
    parsed = urlsplit(value.strip())
    if not parsed.hostname:
        raise SafetyError("A configured database/cache URL has no hostname.")
    return parsed.hostname.casefold().rstrip(".")


def validate_runtime_configuration(environment: str, environ: dict[str, str] | None = None) -> None:
    """Reject recognizable production DB/cache/broker settings in the runner."""

    values = os.environ if environ is None else environ
    for name in ("DATABASE_URL", "REDIS_URL", "CELERY_BROKER_URL"):
        raw_value = values.get(name, "").strip()
        if not raw_value:
            continue
        host = _config_host(raw_value)
        if _is_local_host(host):
            continue
        if _service_host_is_production(host):
            raise SafetyError(f"Refusing {name} that points at a production service.")
        if environment == "local":
            raise SafetyError(f"Local load tests require {name} to be unset or loopback-only.")
        if not _has_marker(host, STAGING_MARKERS):
            raise SafetyError(
                f"Staging load tests require {name} to use a hostname with a staging/test marker."
            )


def _bounded_float(value: str, name: str, maximum: float) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be a number.") from exc
    if number <= 0 or number > maximum:
        raise argparse.ArgumentTypeError(f"{name} must be greater than 0 and no more than {maximum}.")
    return number


def _bounded_int(value: str, name: str, maximum: int) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be an integer.") from exc
    if number <= 0 or number > maximum:
        raise argparse.ArgumentTypeError(f"{name} must be greater than 0 and no more than {maximum}.")
    return number


def _p95(values: list[float]) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[94]


def _endpoint_url(target: Target, endpoint: str) -> str:
    path, _ = ENDPOINTS[endpoint]
    return f"{target.base_url}{path}"


def _request_once(
    url: str,
    timeout: float,
    max_response_bytes: int,
    headers: dict[str, str],
) -> RequestResult:
    started = time.perf_counter()
    try:
        request = Request(url, headers=headers, method="GET")
        with _HTTP_OPENER.open(request, timeout=timeout) as response:
            response.read(max_response_bytes + 1)
            status = int(response.status)
            error = None if 200 <= status < 400 else f"http_{status}"
            timed_out = False
    except HTTPError as exc:
        status = int(exc.code)
        error = f"http_{status}"
        timed_out = False
    except (TimeoutError, socket.timeout) as exc:
        status = None
        error = type(exc).__name__
        timed_out = True
    except URLError as exc:
        reason = exc.reason
        timed_out = isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in str(reason).casefold()
        status = None
        error = "timeout" if timed_out else type(reason).__name__
    except Exception as exc:  # noqa: BLE001 - the harness must report request failures safely.
        status = None
        error = type(exc).__name__
        timed_out = False
    return RequestResult(
        latency_ms=(time.perf_counter() - started) * 1000,
        status=status,
        error=error,
        timed_out=timed_out,
    )


def _run_requests(
    *,
    url: str,
    duration: float,
    concurrency: int,
    rate: float,
    max_requests: int,
    timeout: float,
    max_response_bytes: int,
    headers: dict[str, str],
) -> tuple[list[RequestResult], float]:
    results: list[RequestResult] = []
    in_flight: set[Future[RequestResult]] = set()
    started_at = time.perf_counter()
    deadline = started_at + duration
    interval = 1.0 / rate
    next_dispatch = started_at
    launched = 0

    def collect(done: set[Future[RequestResult]]) -> None:
        for future in done:
            results.append(future.result())
        in_flight.difference_update(done)

    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="studymate-load") as executor:
        while launched < max_requests and time.perf_counter() < deadline:
            now = time.perf_counter()
            if next_dispatch > now:
                time.sleep(min(next_dispatch - now, max(0.0, deadline - now)))
            now = time.perf_counter()
            if now >= deadline:
                break
            while len(in_flight) >= concurrency:
                done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
                collect(done)
            in_flight.add(
                executor.submit(
                    _request_once,
                    url,
                    timeout,
                    max_response_bytes,
                    headers,
                )
            )
            launched += 1
            next_dispatch = max(next_dispatch + interval, time.perf_counter())

        if in_flight:
            done, _ = wait(in_flight)
            collect(done)

    return results, time.perf_counter() - started_at


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded, read-only StudyMate API smoke/load test against local or staging only."
    )
    parser.add_argument("--version", action="version", version=f"studymate-api-load-test {TOOL_VERSION}")
    parser.add_argument("--base-url", required=True, help="Explicit API origin, for example http://127.0.0.1:8000")
    parser.add_argument("--target-environment", required=True, choices=("local", "staging"))
    parser.add_argument("--staging-hostname", help="Exact staging hostname; required for staging targets")
    parser.add_argument("--endpoint", choices=tuple(ENDPOINTS), default="health")
    parser.add_argument("--auth-mode", choices=("anonymous", "bearer"), default="anonymous")
    parser.add_argument("--auth-token-env", default="STUDYMATE_LOADTEST_TOKEN")
    parser.add_argument("--account-label", default="anonymous", help="Non-secret label printed with workload metadata")
    parser.add_argument(
        "--duration",
        type=lambda value: _bounded_float(value, "--duration", MAX_DURATION_SECONDS),
        default=DEFAULT_DURATION_SECONDS,
    )
    parser.add_argument(
        "--concurrency",
        type=lambda value: _bounded_int(value, "--concurrency", MAX_CONCURRENCY),
        default=DEFAULT_CONCURRENCY,
    )
    parser.add_argument(
        "--rate",
        type=lambda value: _bounded_float(value, "--rate", MAX_RATE_PER_SECOND),
        default=DEFAULT_RATE_PER_SECOND,
        help="Global request-start rate per second; requests are never retried",
    )
    parser.add_argument(
        "--max-requests",
        type=lambda value: _bounded_int(value, "--max-requests", MAX_REQUESTS),
        default=DEFAULT_MAX_REQUESTS,
    )
    parser.add_argument(
        "--timeout",
        type=lambda value: _bounded_float(value, "--timeout", MAX_TIMEOUT_SECONDS),
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument("--max-response-bytes", type=lambda value: _bounded_int(value, "--max-response-bytes", 10_485_760), default=DEFAULT_MAX_RESPONSE_BYTES)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the workload without sending requests")
    return parser


def _validate_args(args: argparse.Namespace) -> tuple[Target, str | None]:
    target = validate_target(args.base_url, args.target_environment, args.staging_hostname)
    validate_runtime_configuration(args.target_environment)
    _, requires_auth = ENDPOINTS[args.endpoint]
    if requires_auth and args.auth_mode != "bearer":
        raise SafetyError(f"The {args.endpoint} endpoint requires --auth-mode bearer.")
    token = None
    if args.auth_mode == "bearer":
        token = os.environ.get(args.auth_token_env, "").strip()
        if not token:
            raise SafetyError(f"Bearer mode requires a non-empty ${args.auth_token_env} environment variable.")
        if args.account_label == "anonymous":
            raise SafetyError("Bearer mode requires an explicit --account-label.")
    return target, token


def _workload_metadata(args: argparse.Namespace, target: Target, url: str) -> dict[str, Any]:
    return {
        "tool": "studymate-api-load-test",
        "tool_version": TOOL_VERSION,
        "python_version": platform.python_version(),
        "target_environment": target.environment,
        "target_hostname": target.hostname,
        "endpoint": args.endpoint,
        "url": url,
        "method": "GET",
        "auth_mode": args.auth_mode,
        "account_label": args.account_label,
        "duration_seconds": args.duration,
        "concurrency": args.concurrency,
        "rate_per_second": args.rate,
        "max_requests": args.max_requests,
        "timeout_seconds": args.timeout,
        "max_response_bytes": args.max_response_bytes,
        "retries": 0,
    }


def _render(metadata: dict[str, Any], results: list[RequestResult], elapsed_seconds: float, output_format: str) -> None:
    status_counts = Counter(str(result.status) for result in results if result.status is not None)
    latencies = [result.latency_ms for result in results]
    errors = [result for result in results if result.error is not None]
    summary = {
        **metadata,
        "observed_wall_seconds": elapsed_seconds,
        "request_count": len(results),
        "error_count": len(errors),
        "timeout_count": sum(result.timed_out for result in results),
        "http_status_counts": dict(sorted(status_counts.items())),
        "throughput_requests_per_second": len(results) / elapsed_seconds if elapsed_seconds else 0.0,
        "latency_ms_p50": statistics.median(latencies) if latencies else None,
        "latency_ms_p95": _p95(latencies) if latencies else None,
    }
    if output_format == "json":
        print(json.dumps(summary, sort_keys=True))
        return
    for key, value in summary.items():
        print(f"{key}={value}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        target, token = _validate_args(args)
        url = _endpoint_url(target, args.endpoint)
        metadata = _workload_metadata(args, target, url)
        if args.dry_run:
            _render(metadata, [], 0.0, args.format)
            return 0

        headers = {"User-Agent": "StudyMateApiLoadTest/" + TOOL_VERSION}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        results, elapsed_seconds = _run_requests(
            url=url,
            duration=args.duration,
            concurrency=args.concurrency,
            rate=args.rate,
            max_requests=args.max_requests,
            timeout=args.timeout,
            max_response_bytes=args.max_response_bytes,
            headers=headers,
        )
        _render(metadata, results, elapsed_seconds, args.format)
        return 1 if not results or any(result.error is not None for result in results) else 0
    except SafetyError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
