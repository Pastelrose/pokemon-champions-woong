# -*- coding: utf-8 -*-
import os
import time
from urllib.parse import parse_qsl
from typing import List
from fastapi import FastAPI, Request, Query, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv

import queries as Q
import logdb
import rebuild as RB

BASE = os.path.dirname(__file__)
# .env 파일에서 환경변수 로드(파일 없으면 무시). OS 환경변수가 우선.
load_dotenv(os.path.join(BASE, ".env"))
app = FastAPI(title="Pokemon Champions 조회")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))

# 관리자 전용 재빌드 API 토큰(환경변수). 미설정 시 API 비활성(404).
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 요청을 로그 DB에 저장. 응답 생성 이후에 기록하며,
    로깅 중 어떤 예외가 나도 조회 결과에는 영향을 주지 않는다."""
    start = time.perf_counter()
    response = await call_next(request)  # 실제 처리(조회)는 그대로 수행/반환
    try:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        client_ip = request.client.host if request.client else None
        # 쿼리스트링을 사람이 읽을 수 있게 URL 디코딩 (예: type=%EB%B6%88%EA%BD%83 -> type=불꽃)
        readable_query = "&".join(
            "{}={}".format(k, v)
            for k, v in parse_qsl(request.url.query, keep_blank_values=True)
        )
        logdb.log_request(
            method=request.method,
            path=request.url.path,
            query=readable_query,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        pass  # 로그 실패는 무시 (조회 결과에 영향 없음)
    return response


def render(name, request, **ctx):
    return templates.TemplateResponse(request, name, ctx)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return render("index.html", request, counts=Q.counts())


@app.get("/pokemon", response_class=HTMLResponse)
def pokemon_list(request: Request,
                 q: str = "",
                 t1: str = "", t2: str = "", type_mode: str = "and",
                 ability: str = "",
                 move: List[str] = Query(default=[]), move_mode: str = "and",
                 resist: List[str] = Query(default=[]), resist_mode: str = "and",
                 include_mega: str = "1",
                 sort_col: List[str] = Query(default=[]),
                 sort_dir: List[str] = Query(default=[])):
    inc_mega = include_mega != "0"
    rows = Q.pokemon_search(q=q, types=[t1, t2], type_mode=type_mode, ability=ability,
                            moves=move, move_mode=move_mode,
                            resists=resist, resist_mode=resist_mode,
                            include_mega=inc_mega, sort_cols=sort_col, sort_dirs=sort_dir)
    # 폼 재표시용: 비어있지 않은 값만, 슬롯 패딩
    moves_sel = [m for m in move if m][:4]
    resists_sel = [r for r in resist if r]
    sorts_sel = [(c, d) for c, d in zip(sort_col, sort_dir) if c]
    return render("pokemon_list.html", request, rows=rows,
                  q=q, t1=t1, t2=t2, type_mode=type_mode, ability=ability,
                  moves_sel=moves_sel, move_mode=move_mode,
                  resists_sel=resists_sel, resist_mode=resist_mode,
                  include_mega=inc_mega, sorts_sel=sorts_sel,
                  types=Q.TYPES, abilities=Q.ability_names(),
                  move_names=Q.move_names(), sort_columns=list(Q.SORT_COLUMNS.keys()))


@app.get("/pokemon/{pid}", response_class=HTMLResponse)
def pokemon_detail(request: Request, pid: int):
    p = Q.pokemon_detail(pid)
    if not p:
        return HTMLResponse("<h1>not found</h1>", status_code=404)
    eff = Q.pokemon_effectiveness(pid)
    weak = [e for e in eff if e["최종배수"] > 1]
    resist = [e for e in eff if 0 < e["최종배수"] < 1]
    immune = [e for e in eff if e["최종배수"] == 0]
    return render("pokemon_detail.html", request, p=p,
                  abilities=Q.pokemon_abilities(pid), learnset=Q.pokemon_learnset(pid),
                  weak=weak, resist=resist, immune=immune)


@app.get("/moves", response_class=HTMLResponse)
def move_list(request: Request, q: str = "", type: str = "", category: str = "",
              sort_col: List[str] = Query(default=[]),
              sort_dir: List[str] = Query(default=[])):
    rows = Q.move_list(q=q, type_=type, category=category,
                       sort_cols=sort_col, sort_dirs=sort_dir)
    sorts_sel = [(c, d) for c, d in zip(sort_col, sort_dir) if c]
    return render("moves_list.html", request, rows=rows, q=q, type=type, category=category,
                  types=Q.TYPES, categories=["물리", "특수", "변화"],
                  sort_columns=list(Q.MOVE_SORT_COLUMNS.keys()), sorts_sel=sorts_sel)


@app.get("/moves/{mid}", response_class=HTMLResponse)
def move_detail(request: Request, mid: int):
    m = Q.move_detail(mid)
    if not m:
        return HTMLResponse("<h1>not found</h1>", status_code=404)
    return render("move_detail.html", request, m=m, learners=Q.move_learners(mid))


@app.get("/abilities", response_class=HTMLResponse)
def ability_list(request: Request, q: str = ""):
    return render("abilities_list.html", request, rows=Q.ability_list(q=q), q=q)


@app.get("/abilities/{aid}", response_class=HTMLResponse)
def ability_detail(request: Request, aid: int):
    a = Q.ability_detail(aid)
    if not a:
        return HTMLResponse("<h1>not found</h1>", status_code=404)
    return render("ability_detail.html", request, a=a, pokemon=Q.ability_pokemon(aid))


@app.get("/items", response_class=HTMLResponse)
def item_list(request: Request, q: str = ""):
    return render("items_list.html", request, rows=Q.item_list(q=q), q=q)


@app.get("/types", response_class=HTMLResponse)
def type_chart(request: Request):
    return render("type_chart.html", request, matrix=Q.type_chart_matrix(), types=Q.TYPES)


@app.post("/admin/rebuild-db")
def admin_rebuild_db(x_admin_token: str = Header(default="")):
    """관리자 전용 DB 재빌드. 토큰이 없거나 틀리면 404로 숨긴다.
    토큰은 헤더(X-Admin-Token)로 받아 요청 로그(쿼리스트링)에 남지 않게 한다."""
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    try:
        counts = RB.rebuild_database()
        return JSONResponse({"status": "ok", "tables": counts})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
