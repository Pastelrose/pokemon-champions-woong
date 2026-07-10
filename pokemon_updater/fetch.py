# -*- coding: utf-8 -*-
"""HTTP 수집기. 요청 간격 준수 + 재시도."""
import time
import requests

from config import REQUEST_DELAY_SEC, TIMEOUT_SEC, USER_AGENT


class Fetcher:
    def __init__(self, delay=REQUEST_DELAY_SEC):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.delay = delay
        self._last = 0.0
        self.count = 0

    def get(self, url, retries=3):
        """URL의 HTML 텍스트를 반환. 실패 시 지수적으로 쉬면서 재시도."""
        last_err = None
        for attempt in range(retries):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                res = self.session.get(url, timeout=TIMEOUT_SEC)
                self._last = time.monotonic()
                self.count += 1
                if res.status_code == 200:
                    res.encoding = "utf-8"
                    return res.text
                last_err = RuntimeError(f"HTTP {res.status_code}: {url}")
            except requests.RequestException as e:
                self._last = time.monotonic()
                last_err = e
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"요청 실패({retries}회 시도): {url} / {last_err}")
