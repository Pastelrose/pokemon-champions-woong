# -*- coding: utf-8 -*-
import os
from typing import List
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import queries as Q

BASE = os.path.dirname(__file__)
app = FastAPI(title="Pokemon Champions 조회")
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))


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
