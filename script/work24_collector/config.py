from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_URL = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo{endpoint}.do"
DEFAULT_PAGE_SIZE = 100
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_SLEEP_SECONDS = 3.0
DEFAULT_SAVE_EVERY_PAGES = 100
DEFAULT_PROGRESS_EVERY_PAGES = 1
DEFAULT_WORKERS = 1
MAX_WORKERS = 4


@dataclass(frozen=True)
class ApiSpec:
    code: str
    display_name: str
    endpoint: str
    key_env: str
    output_dir_name: str


@dataclass(frozen=True)
class CollectorSettings:
    output_dir: Path
    checkpoint_dir: Path
    log_path: Path
    page_size: int
    timeout_seconds: int
    max_retries: int
    retry_sleep_seconds: float
    save_every_pages: int
    progress_every_pages: int
    workers: int
    encoding: str
    resume: bool
    simple_filename: bool


API_SPECS = {
    "national-card": ApiSpec(
        code="national-card",
        display_name="국민내일배움카드훈련과정",
        endpoint="310L01",
        key_env="WORK24_API_KEY_NATIONAL_CARD",
        output_dir_name="국민내일배움카드",
    ),
    "employer": ApiSpec(
        code="employer",
        display_name="사업주훈련",
        endpoint="311L01",
        key_env="WORK24_API_KEY_EMPLOYER",
        output_dir_name="사업주훈련",
    ),
    "consortium": ApiSpec(
        code="consortium",
        display_name="국가인적자원개발 컨소시엄",
        endpoint="312L01",
        key_env="WORK24_API_KEY_CONSORTIUM",
        output_dir_name="국가인적자원개발 컨소시엄",
    ),
    "work-study": ApiSpec(
        code="work-study",
        display_name="일학습병행",
        endpoint="313L01",
        key_env="WORK24_API_KEY_WORK_STUDY",
        output_dir_name="일학습병행",
    ),
}

API_COLLECTION_ORDER = ("national-card", "employer", "consortium", "work-study")
NON_NATIONAL_CARD_COLLECTION_ORDER = ("employer", "consortium", "work-study")


class CollectionError(RuntimeError):
    """Raised when collection cannot continue safely."""
