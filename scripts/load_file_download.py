#!/usr/bin/env python3
"""
Simple load tester for Material Bin file download endpoints.

Examples:
  python scripts/load_file_download.py --url https://example.com/api/pastes/.../files/...?encryption_key=... --concurrency 8 --requests 80
  python scripts/load_file_download.py --url-file urls.txt --steps 1,2,4,8,16 --requests 40 --range 0-1048575
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://paste.fifcom.cn"


@dataclass
class Result:
    ok: bool
    status: int | None
    seconds: float
    bytes_read: int
    error: str | None = None


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * pct))
    return ordered[max(0, min(index, len(ordered) - 1))]


def normalize_base_url(value: str | None) -> str:
    base_url = (value or DEFAULT_BASE_URL).strip()
    if not base_url:
        return DEFAULT_BASE_URL
    return base_url.rstrip("/")


def build_url(base_url: str, value: str) -> str:
    raw = value.strip()
    if raw.startswith(("http://", "https://")):
        return raw
    if not raw.startswith("/"):
        raw = "/" + raw
    return f"{base_url}{raw}"


def fetch_once(
    url: str,
    *,
    method: str,
    timeout: float,
    byte_range: str | None,
    read_body: bool,
) -> Result:
    headers = {
        "User-Agent": "materialbin-load-test/1.0",
    }
    if byte_range:
        headers["Range"] = f"bytes={byte_range}"

    start = time.perf_counter()
    bytes_read = 0
    status: int | None = None
    try:
        req = Request(url, headers=headers, method=method)
        with urlopen(req, timeout=timeout) as resp:
            status = int(resp.status)
            if method == "HEAD":
                bytes_read = int(resp.headers.get("Content-Length") or 0)
            elif read_body:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
            else:
                bytes_read = int(resp.headers.get("Content-Length") or 0)
        elapsed = time.perf_counter() - start
        return Result(200 <= status < 400, status, elapsed, bytes_read)
    except HTTPError as exc:
        elapsed = time.perf_counter() - start
        return Result(False, int(exc.code), elapsed, bytes_read, type(exc).__name__)
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return Result(False, status, elapsed, bytes_read, type(exc).__name__)


async def run_batch(
    urls: list[str],
    *,
    concurrency: int,
    requests: int,
    method: str,
    timeout: float,
    byte_range: str | None,
    read_body: bool,
) -> list[Result]:
    queue: asyncio.Queue[int] = asyncio.Queue()
    for index in range(requests):
        queue.put_nowait(index)

    results: list[Result] = []
    lock = asyncio.Lock()
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=concurrency)

    async def worker(worker_id: int) -> None:
        while True:
            try:
                index = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            url = urls[(index + worker_id) % len(urls)]
            result = await loop.run_in_executor(
                executor,
                partial(
                    fetch_once,
                    url,
                    method=method,
                    timeout=timeout,
                    byte_range=byte_range,
                    read_body=read_body,
                ),
            )
            async with lock:
                results.append(result)
            queue.task_done()

    started = time.perf_counter()
    try:
        await asyncio.gather(*(worker(i) for i in range(concurrency)))
    finally:
        executor.shutdown(wait=True)
    elapsed = time.perf_counter() - started

    summarize(results, concurrency=concurrency, wall_seconds=elapsed)
    return results


def summarize(results: list[Result], *, concurrency: int, wall_seconds: float) -> None:
    latencies = [r.seconds for r in results]
    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    total_bytes = sum(r.bytes_read for r in results)
    by_status: dict[str, int] = {}
    for result in results:
        key = str(result.status) if result.status is not None else result.error or "error"
        by_status[key] = by_status.get(key, 0) + 1

    avg = statistics.mean(latencies) if latencies else 0.0
    print(
        "concurrency={concurrency} requests={requests} ok={ok} failed={failed} "
        "wall={wall:.2f}s rps={rps:.2f} throughput={mbps:.2f}MiB/s "
        "avg={avg:.3f}s p50={p50:.3f}s p95={p95:.3f}s p99={p99:.3f}s max={maxv:.3f}s "
        "statuses={statuses}".format(
            concurrency=concurrency,
            requests=len(results),
            ok=len(ok),
            failed=len(failed),
            wall=wall_seconds,
            rps=(len(results) / wall_seconds) if wall_seconds > 0 else 0.0,
            mbps=(total_bytes / wall_seconds / 1024 / 1024)
            if wall_seconds > 0
            else 0.0,
            avg=avg,
            p50=percentile(latencies, 0.50),
            p95=percentile(latencies, 0.95),
            p99=percentile(latencies, 0.99),
            maxv=max(latencies) if latencies else 0.0,
            statuses=by_status,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", action="append", help="Download URL to test.")
    parser.add_argument("--url-file", help="File containing one URL per line.")
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Base URL used for relative paths. Defaults to BASE_URL env var, "
            f"then {DEFAULT_BASE_URL}."
        ),
    )
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--requests", type=int, default=1)
    parser.add_argument(
        "--method",
        choices=("GET", "HEAD"),
        default="GET",
        help="HTTP method to use. HEAD avoids body transfer if the upstream supports it.",
    )
    parser.add_argument(
        "--steps",
        help="Comma-separated concurrency steps, for example: 1,2,4,8,16.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--range",
        dest="byte_range",
        help="Optional byte range without the 'bytes=' prefix, for example 0-1048575.",
    )
    parser.add_argument(
        "--headers-only",
        action="store_true",
        help="Do not read the response body. Useful for isolating response-header latency.",
    )
    return parser.parse_args()


def load_urls(args: argparse.Namespace) -> list[str]:
    base_url = normalize_base_url(args.base_url or os.getenv("BASE_URL"))
    raw_urls = list(args.url or [])
    if args.url_file:
        with open(args.url_file, encoding="utf-8") as f:
            raw_urls.extend(line.strip() for line in f if line.strip())
    if not raw_urls:
        raise SystemExit("Provide --url or --url-file.")
    return [build_url(base_url, value) for value in raw_urls]


async def main() -> None:
    args = parse_args()
    urls = load_urls(args)
    steps = (
        [int(item.strip()) for item in args.steps.split(",") if item.strip()]
        if args.steps
        else [args.concurrency]
    )
    for concurrency in steps:
        await run_batch(
            urls,
            concurrency=max(1, concurrency),
            requests=max(1, args.requests),
            method=args.method,
            timeout=args.timeout,
            byte_range=args.byte_range,
            read_body=not args.headers_only,
        )


if __name__ == "__main__":
    asyncio.run(main())
