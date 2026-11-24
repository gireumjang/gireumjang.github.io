"""네이버 저장 목록(raw JSON) + 행정경계(geo JSON) → 웹에서 바로 쓰는 data/*.js 로 변환.

실행: python3 scripts/build_data.py
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from classify import TYPE_INFO, classify  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
GEO = ROOT / "data" / "geo"
OUT = ROOT / "app"

# 주소 첫 단어 → 짧은 지역명
REGION = {
    "서울": "서울", "서울특별시": "서울",
    "경기": "경기", "경기도": "경기",
    "인천": "인천", "인천광역시": "인천",
    "강원": "강원", "강원도": "강원", "강원특별자치도": "강원",
    "부산": "부산", "부산광역시": "부산",
    "대구": "대구", "대구광역시": "대구",
    "광주": "광주", "광주광역시": "광주",
    "대전": "대전", "대전광역시": "대전",
    "울산": "울산", "울산광역시": "울산",
    "세종": "세종", "세종특별자치시": "세종",
    "충북": "충북", "충청북도": "충북",
    "충남": "충남", "충청남도": "충남",
    "전북": "전북", "전라북도": "전북", "전북특별자치도": "전북",
    "전남": "전남", "전라남도": "전남",
    "경북": "경북", "경상북도": "경북",
    "경남": "경남", "경상남도": "경남",
    "제주": "제주", "제주특별자치도": "제주",
}


def r5(v):
    return round(v, 5)


def simplify_ring(ring, step):
    """좌표를 step 간격으로 솎아내서 용량을 줄인다 (애니메이션용이라 정밀도 불필요)."""
    if len(ring) <= 8:
        return [[r5(x), r5(y)] for x, y in ring]
    pts = ring[::step]
    if pts[-1] != ring[-1]:
        pts.append(ring[-1])
    return [[r5(x), r5(y)] for x, y in pts]


def polys(geom, step):
    if geom["type"] == "Polygon":
        gs = [geom["coordinates"]]
    else:
        gs = geom["coordinates"]
    out = []
    for poly in gs:
        outer = poly[0]
        if len(outer) < 4:
            continue
        out.append(simplify_ring(outer, step))
    return out


def build_geo():
    prov = json.loads((GEO / "skorea_provinces_geo_simple.json").read_text(encoding="utf-8"))
    muni = json.loads((GEO / "skorea_municipalities_geo_simple.json").read_text(encoding="utf-8"))
    provinces = [
        {"name": f["properties"]["name"], "code": f["properties"]["code"], "polys": polys(f["geometry"], 2)}
        for f in prov["features"]
    ]
    seoul = [
        {"name": f["properties"]["name"], "polys": polys(f["geometry"], 1)}
        for f in muni["features"]
        if f["properties"]["code"].startswith("11")
    ]
    code2short = {f["code"]: REGION.get(f["name"], f["name"]) for f in provinces}
    munis = [
        {"name": f["properties"]["name"], "prov": code2short.get(f["properties"]["code"][:2], ""), "polys": polys(f["geometry"], 2)}
        for f in muni["features"]
        if not f["properties"]["code"].startswith("11")
    ]
    return {"provinces": provinces, "seoul": seoul, "munis": munis}


def build_places():
    places = {}
    for fname, folder in (("맛집리스트.json", "맛집리스트"), ("찐맛집.json", "찐맛집")):
        data = json.loads((RAW / fname).read_text(encoding="utf-8"))
        for b in data["bookmarkList"]:
            if b.get("px") is None or b.get("py") is None:
                continue
            key = b.get("sid") or f'{b["name"]}@{b["px"]:.5f},{b["py"]:.5f}'
            addr = b.get("address") or ""
            first = addr.split()[0] if addr else ""
            p = places.get(key)
            if p is None:
                p = places[key] = {
                    "id": key,
                    "name": b.get("displayName") or b["name"],
                    "addr": addr,
                    "region": REGION.get(first, "기타"),
                    "lng": r5(b["px"]),
                    "lat": r5(b["py"]),
                    "cat": b.get("mcidName") or "",
                    "sid": b.get("sid"),
                    "saved": b.get("creationTime"),
                    "folders": [],
                }
            if folder not in p["folders"]:
                p["folders"].append(folder)
    attach_naver(places.values())
    for p in places.values():
        parts = p["addr"].split()
        p["area"] = parts[1] if len(parts) > 1 else ""
        # 체인·지점: "OO 강남점", "OO본점"처럼 지점 이름이 붙은 곳
        p["main"] = bool(re.search(r"본점$", p["name"]))
        p["chain"] = not p["main"] and bool(re.search(r"(\s\S+|직영|호|역|분)점$", p["name"])) and not re.search(r"(전문|식당|판매|정육)점$", p["name"])
        p["types"] = classify(
            p.get("kind"), p["cat"], p["name"],
            [m["name"] for m in p.get("menus", [])],
            [m["name"] for m in p.get("reviewMenus", [])],
        )
    return list(places.values())


def attach_naver(places):
    """collect_naver.py 가 모은 메뉴/후기 요약을 붙인다 (없으면 그냥 넘어감)."""
    nav = ROOT / "data" / "naver"
    got = 0
    for p in places:
        f = nav / f"{p['sid']}.json" if p.get("sid") else None
        if not f or not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("error"):
            continue
        got += 1
        p["kind"] = d.get("category")
        if d.get("roadAddress"):
            p["addr"] = d["roadAddress"]
        p["phone"] = d.get("phone") or d.get("phoneSearch")
        if not d.get("phone") and d.get("phoneSearch"):
            p["phoneSrc"] = "search"  # 네이버 검색 결과에서 주소로 확인한 번호
        p["rating"] = d.get("rating")
        p["vr"] = d.get("visitorReviews")
        p["br"] = d.get("blogReviews")
        p["one"] = d.get("oneLiner")
        p["menus"] = [{"name": m["name"], "price": m.get("price"), "img": m.get("img")} for m in d.get("menus", [])[:8]]
        p["reviewMenus"] = d.get("reviewMenus", [])[:6]
        if d.get("hours"):
            p["hours"] = d["hours"]
        p["keywords"] = [{"name": k["name"], "count": k["count"]} for k in d.get("keywords", [])[:4]]
        wk = weekly_stats(nav / "history" / f"{p['sid']}.jsonl")
        if wk:
            p["wk"] = wk
    print(f"naver 상세 붙임: {got}곳")


def weekly_stats(path):
    """주 1회 쌓이는 스냅샷으로 최근 4주 평균 별점, 지난주 대비 새 후기 수를 낸다."""
    if not path.exists():
        return None
    snaps = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    snaps.sort(key=lambda x: x["t"])
    last4 = snaps[-4:]
    ratings = [x["rating"] for x in last4 if x.get("rating")]
    out = {"n": len(snaps)}
    if ratings:
        out["avgRating"] = round(sum(ratings) / len(ratings), 2)
    if len(snaps) >= 2 and snaps[-1].get("vr") is not None and snaps[-2].get("vr") is not None:
        out["newReviews"] = snaps[-1]["vr"] - snaps[-2]["vr"]
    return out


def main():
    OUT.mkdir(exist_ok=True)
    geo = build_geo()
    places = build_places()
    (OUT / "geo.js").write_text("window.GEO=" + json.dumps(geo, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8", newline="\n")
    (OUT / "types.js").write_text("window.TYPES=" + json.dumps(TYPE_INFO, ensure_ascii=False) + ";\n", encoding="utf-8", newline="\n")
    (OUT / "places.js").write_text("window.PLACES=" + json.dumps(places, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8", newline="\n")
    print(f"places: {len(places)}  (찐맛집 {sum('찐맛집' in p['folders'] for p in places)})")
    print(f"geo: provinces {len(geo['provinces'])}, seoul gu {len(geo['seoul'])}")


if __name__ == "__main__":
    main()
