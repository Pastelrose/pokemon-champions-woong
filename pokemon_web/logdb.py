# -*- coding: utf-8 -*-
"""요청 로그 저장 모듈 (텍스트 파일 방식).

 - pokemon_web/logs/ 폴더에 날짜별(yyyymmdd.txt) 파일로 한 줄씩 append 한다.
 - DB를 쓰지 않으므로 잠금/동시성 문제가 없고, 서버 실행 중에도 자유롭게 열어볼 수 있다.
 - 로그 기록 전 과정을 try/except로 감싸, 실패해도 결과 조회에는 영향을 주지 않는다.
 - 같은 프로세스 내 여러 스레드가 동시에 같은 파일에 쓰지 않도록 Lock으로 직렬화.
"""
import os
import threading
import datetime
from pathlib import Path

# 로그 폴더: 이 파일(__file__) 기준 ./logs (작업 폴더 위치와 무관)
# 필요 시 환경변수 POKEMON_LOG_DIR로 덮어쓸 수 있다.
_LOG_DIR = os.environ.get("POKEMON_LOG_DIR") or str(Path(__file__).resolve().parent / "logs")

_lock = threading.Lock()


def log_request(method, path, query, status, duration_ms, client_ip, user_agent):
    """요청 한 건을 오늘 날짜 파일(yyyymmdd.txt)에 한 줄로 기록.
    실패는 조용히 무시한다(조회에 영향 없음)."""
    try:
        now = datetime.datetime.now()
        full_path = path + (("?" + query) if query else "")
        line = (
            f'{now.isoformat(sep=" ", timespec="milliseconds")} | '
            f'{method} {full_path} | '
            f'status={status} | {duration_ms}ms | '
            f'ip={client_ip} | ua="{user_agent}"\n'
        )
        file_path = os.path.join(_LOG_DIR, now.strftime("%Y%m%d") + ".txt")
        with _lock:
            os.makedirs(_LOG_DIR, exist_ok=True)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        # 로그 저장 실패가 결과 조회에 영향을 주지 않도록 무시
        pass
