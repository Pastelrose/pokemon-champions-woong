# -*- coding: utf-8 -*-
"""HTML 파서 모음.

사이트는 목록 데이터를 HTML 표(<table>)로 함께 렌더링하므로,
BeautifulSoup으로 표를 읽어 구조화한다.
사이트 구조가 크게 바뀌면 이 파일만 고치면 된다.
파싱 결과가 이상하면 validate.py 단계에서 걸러져 갱신이 중단된다.
"""
import re
from bs4 import BeautifulSoup

from config import TYPES

_TYPE_SET = set(TYPES)

# 상세 링크에서 ID 추출용
_RE_POKE = re.compile(r"/pokemon/(\d+)(?:[?#]|$)")
_RE_MOVE = re.compile(r"/moves/(\d+)(?:[?#]|$)")
_RE_ABIL = re.compile(r"/abilities/(\d+)(?:[?#]|$)")
_RE_ITEM = re.compile(r"/items/(\d+)(?:[?#]|$)")
# 이미지 파일명에서 도감번호 추출 (003.png, 003_1.png)
_RE_IMG_NO = re.compile(r"/(\d+)(?:_\d+)?\.png(?:\?|$)")
# 행 텍스트에서 종족값 추출 (H80A82B83C100D100S80)
_RE_STATS = re.compile(r"H(\d+)\s*A(\d+)\s*B(\d+)\s*C(\d+)\s*D(\d+)\s*S(\d+)")


def _soup(html):
    return BeautifulSoup(html, "lxml")


def _split_types(text):
    """'풀독' 처럼 붙은 문자열을 타입 이름 목록으로 분해. 실패 시 None."""
    text = text.strip().replace(" ", "")
    if not text:
        return None
    result, i = [], 0
    while i < len(text):
        for t in sorted(TYPES, key=len, reverse=True):
            if text.startswith(t, i):
                result.append(t)
                i += len(t)
                break
        else:
            return None
    return result if 1 <= len(result) <= 2 else None


def _find_link(el, regex):
    """el 아래에서 정규식에 맞는 링크의 (id, 텍스트, href)를 반환.

    이미지만 감싼 링크는 텍스트가 비므로, 텍스트가 있는 링크를 우선한다."""
    first = None
    for a in el.find_all("a", href=True):
        m = regex.search(a["href"])
        if not m:
            continue
        text = a.get_text(strip=True)
        if text:
            return int(m.group(1)), text, a["href"]
        if first is None:
            first = (int(m.group(1)), text, a["href"])
    return first if first else (None, None, None)


def parse_pokemon_list(html):
    """포켓몬 목록 페이지 1장 -> 행 dict 리스트.

    반환 키: ID, 도감번호, 이름, 일본어이름, 이미지URL, 타입리스트,
             HP, 공격, 방어, 특공, 특방, 스피드, 싱글순위, 더블순위, 특성명리스트
    """
    rows = []
    for tr in _soup(html).find_all("tr"):
        pid, name, _ = _find_link(tr, _RE_POKE)
        if pid is None or not name:
            continue
        row_text = tr.get_text("", strip=True)
        m = _RE_STATS.search(row_text.replace(" ", ""))
        if not m:
            continue  # 종족값이 없는 행(헤더 등)은 건너뜀
        stats = [int(x) for x in m.groups()]

        img = tr.find("img", src=True)
        img_url, jp_name, dex_no = "", "", None
        if img is not None:
            img_url = img["src"]
            jp_name = (img.get("alt") or "").strip()
            m2 = _RE_IMG_NO.search(img_url)
            if m2:
                dex_no = int(m2.group(1))

        # 타입: 셀 텍스트가 타입 이름만으로 분해되는 셀을 찾는다
        types = None
        for td in tr.find_all(["td", "th"]):
            cand = _split_types(td.get_text("", strip=True))
            if cand:
                types = cand
                break

        # 순위: '#숫자' 패턴 앞쪽 두 개 (싱글, 더블). 없으면 None
        ranks = re.findall(r"#(\d+)", row_text)
        single = int(ranks[0]) if len(ranks) >= 1 else None
        double = int(ranks[1]) if len(ranks) >= 2 else None

        # 특성 이름들: '이름1/이름2' 형태의 마지막 셀
        abil_names = []
        tds = tr.find_all("td")
        if tds:
            last = tds[-1].get_text("", strip=True)
            if last and _split_types(last) is None and not _RE_STATS.search(last.replace(" ", "")):
                abil_names = [x.strip() for x in last.split("/") if x.strip()]

        rows.append({
            "ID": pid, "도감번호": dex_no, "이름": name, "일본어이름": jp_name,
            "이미지URL": img_url, "타입리스트": types or [],
            "HP": stats[0], "공격": stats[1], "방어": stats[2],
            "특공": stats[3], "특방": stats[4], "스피드": stats[5],
            "싱글순위": single, "더블순위": double, "특성명리스트": abil_names,
        })
    return rows


def parse_pokemon_names(html):
    """영어(또는 다른 언어) 목록 페이지 -> {ID: 이름}."""
    names = {}
    for tr in _soup(html).find_all("tr"):
        pid, name, _ = _find_link(tr, _RE_POKE)
        if pid is not None and name:
            names[pid] = name
    return names


def _header_index(table):
    """표 헤더 텍스트 -> 컬럼 인덱스 dict."""
    head = table.find("tr")
    if not head:
        return {}
    return {th.get_text("", strip=True): i
            for i, th in enumerate(head.find_all(["th", "td"]))}


def _find_table_with_header(soup, header_name):
    for table in soup.find_all("table"):
        if header_name in _header_index(table):
            return table
    return None


def parse_moves_list(html):
    """기술 목록 페이지 -> 행 dict 리스트 (기술명 헤더가 있는 표)."""
    soup = _soup(html)
    table = _find_table_with_header(soup, "기술명")
    if table is None:
        return []
    idx = _header_index(table)
    rows = []
    for tr in table.find_all("tr"):
        mid, name, _ = _find_link(tr, _RE_MOVE)
        if mid is None or not name:
            continue
        tds = tr.find_all("td")

        def col(key):
            i = idx.get(key)
            if i is None or i >= len(tds):
                return ""
            return tds[i].get_text(" ", strip=True)

        def num(key):
            v = col(key).replace(",", "")
            return v if v.isdigit() else ""

        rows.append({
            "ID": mid, "기술명": name,
            "타입": col("타입"), "분류": col("분류"),
            "위력": num("위력"), "명중": num("명중"), "PP": num("PP"),
            "성질": col("성질"), "대상": col("대상"), "효과": col("효과"),
        })
    return rows


def parse_learnset(html):
    """포켓몬 상세 페이지 -> [(move_id, 기술명)].

    AI 분석 본문에도 기술 링크가 있으므로,
    반드시 '기술명' 헤더가 있는 표 안의 링크만 수집한다.
    """
    soup = _soup(html)
    table = _find_table_with_header(soup, "기술명")
    if table is None:
        return []
    result, seen = [], set()
    for tr in table.find_all("tr"):
        mid, name, _ = _find_link(tr, _RE_MOVE)
        if mid is not None and name and mid not in seen:
            seen.add(mid)
            result.append((mid, name))
    return result


def parse_abilities_list(html):
    """특성 목록 페이지 -> 행 dict 리스트."""
    soup = _soup(html)
    rows, seen = [], set()
    for tr in soup.find_all("tr"):
        aid, name, _ = _find_link(tr, _RE_ABIL)
        if aid is None or not name or aid in seen:
            continue
        seen.add(aid)
        tds = tr.find_all("td")
        # 효과: 링크 텍스트(특성명)가 아닌 가장 긴 셀 텍스트
        effect = ""
        for td in tds:
            t = td.get_text(" ", strip=True)
            if t and t != name and len(t) > len(effect):
                effect = t
        rows.append({"ID": aid, "특성명": name, "효과": effect})
    return rows


def parse_items_list(html):
    """지닌물건 목록 페이지 -> 행 dict 리스트."""
    soup = _soup(html)
    table = _find_table_with_header(soup, "효과") or soup
    rows, seen = [], set()
    for tr in table.find_all("tr"):
        iid, name, _ = _find_link(tr, _RE_ITEM)
        if iid is None or not name or iid in seen:
            continue
        seen.add(iid)
        img = tr.find("img", src=True)
        img_url = img["src"] if img is not None else ""
        texts = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        texts = [t for t in texts if t and t != name]
        texts.sort(key=len, reverse=True)
        effect = texts[0] if texts else ""
        obtain = texts[1] if len(texts) > 1 else ""
        rows.append({"ID": iid, "이름": name, "효과": effect,
                     "입수방법": obtain, "이미지URL": img_url})
    return rows


def parse_season(html):
    """페이지 텍스트에서 '시즌: M-3 (2026-07-06)' 패턴을 찾아
    (시즌, 기준일) 반환. 못 찾으면 (None, None)."""
    text = _soup(html).get_text(" ", strip=True)
    m = re.search(r"시즌\s*[:：]\s*([A-Za-z0-9\-]+)\s*\((\d{4}-\d{2}-\d{2})\)", text)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"시즌\s*[:：]\s*([A-Za-z0-9\-]+)", text)
    if m:
        return m.group(1), None
    return None, None
