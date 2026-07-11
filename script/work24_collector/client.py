from __future__ import annotations

import time
import threading
from typing import Any
from urllib.parse import urlencode

import requests

from .config import BASE_URL, ApiSpec, CollectionError


_thread_local = threading.local()


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "SmartHRD-Work24-Collector/1.0"})
    return session


def get_thread_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = create_session()
        _thread_local.session = session
    return session


def build_url(spec: ApiSpec, api_key: str, start: str, end: str, page_num: int, page_size: int) -> str:
    params = {
        "authKey": api_key,
        "returnType": "json",
        "outType": "1",
        "pageNum": page_num,
        "pageSize": page_size,
        "srchTraStDt": start,
        "srchTraEndDt": end,
        "sort": "ASC",
        "sortCol": "2",
    }
    return f"{BASE_URL.format(endpoint=spec.endpoint)}?{urlencode(params)}"


def call_json(session: requests.Session, url: str, timeout_seconds: int) -> dict[str, Any]:
    response = session.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise CollectionError("API response was not a JSON object.")
    return payload


def fetch_page(
    session: requests.Session,
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
    page_num: int,
    page_size: int,
    timeout_seconds: int,
    max_retries: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    url = build_url(spec, api_key, start, end, page_num, page_size)
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            payload = call_json(session, url, timeout_seconds)
            rows = payload.get("srchList", [])
            if rows or payload.get("scn_cnt", 0) == 0:
                return payload
            last_error = CollectionError("API returned an empty srchList.")
        except Exception as exc:  # requests/json/schema failures all use the same retry policy.
            last_error = exc

        if attempt < max_retries:
            sleep_for = retry_sleep_seconds * attempt
            print(f"Retry page {page_num}: attempt {attempt}/{max_retries}, sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)

    raise CollectionError(f"Failed to fetch page {page_num}: {last_error}") from last_error


def fetch_page_with_thread_session(
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
    page_num: int,
    page_size: int,
    timeout_seconds: int,
    max_retries: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    return fetch_page(
        get_thread_session(),
        spec,
        api_key,
        start,
        end,
        page_num,
        page_size,
        timeout_seconds,
        max_retries,
        retry_sleep_seconds,
    )
