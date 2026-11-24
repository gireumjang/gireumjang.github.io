"""행정동 경계 → app/dong/{도 코드}.json (지도에서 시·군·구를 눌렀을 때만 불러오는 동 경계·이름).

원본: data/geo_raw/HangJeongDong_ver*.geojson (vuski/admdongkor, 통계청 SGIS 행정동 경계 가공, CC BY 4.0)
      → 가장 최신 파일을 쓴다. 공개 저장소엔 원본을 올리지 않고(data/), 줄인 결과만 app/dong 에 둔다.

지도의 시·군·구(app/geo.js)는 예전 경계라 이름이 안 맞는 곳이 있어서(인천·화성 신설 구 등),
동 중심점이 어느 시·군·구 안에 들어가는지로 묶는다.

실행: python3 scripts/build_dong.py
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "geo_raw"
OUT = ROOT / "app" / "dong"
PROV_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주",
              "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원도": "강원",
              "충청북도": "충북", "충청남도": "충남", "전라북도": "전북", "전라남도": "전남", "경상북도": "경북",
              "경상남도": "경남", "제주특별자치도": "제주"}
TOL = 0.00025  # 단순화 허용 오차(도). 약 25m — 확대해도 경계가 매끈해 보이는 정도


def simplify(pts, tol):
    """Douglas-Peucker (반복형)."""
    if len(pts) < 4:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        best, idx = 0.0, -1
        for i in range(a + 1, b):
            x0, y0 = pts[i]
            # 닫힌 고리는 처음·끝 점이 같아 선분이 없다 → 그 점과의 거리로
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm if norm > 1e-12 else math.hypot(x0 - x1, y0 - y1)
            if d > best:
                best, idx = d, i
        if best > tol and idx > 0:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def rings_of(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [poly[0] for poly in polys]  # 바깥 테두리만 (구멍은 선 그리기에 필요 없음)


def area_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1
        a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-14:
        xs, ys = zip(*ring)
        return [sum(xs) / len(xs), sum(ys) / len(ys)], 0.0
    return [cx / (3 * a), cy / (3 * a)], abs(a) / 2


def inside(pt, ring):
    x, y = pt
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def main():
    src = sorted(RAW.glob("HangJeongDong_ver*.geojson"))
    if not src:
        sys.exit("data/geo_raw/HangJeongDong_ver*.geojson 이 없어요")
    feats = json.loads(src[-1].read_text(encoding="utf-8"))["features"]
    s = (ROOT / "app" / "geo.js").read_text(encoding="utf-8")
    geo = json.loads(s[s.index("=") + 1:s.rstrip().rindex(";")])
    code_of = {PROV_SHORT.get(p["name"], p["name"]): p["code"] for p in geo["provinces"]}
    munis = [{**g, "prov": "서울"} for g in geo["seoul"]] + geo["munis"]
    for m in munis:
        xs = [x for r in m["polys"] for x, _ in r]; ys = [y for r in m["polys"] for _, y in r]
        m["bbox"] = (min(xs), min(ys), max(xs), max(ys))
        m["c"] = area_centroid(max(m["polys"], key=len))[0]

    out, missed = {}, 0
    for f in feats:
        rings = rings_of(f["geometry"])
        main_ring = max(rings, key=lambda r: area_centroid(r)[1])
        c, _ = area_centroid(main_ring)
        if not inside(c, main_ring):  # 오목한 모양이면 테두리 안쪽 한 점으로
            c = main_ring[len(main_ring) // 2]
        home = next((m for m in munis
                     if m["bbox"][0] <= c[0] <= m["bbox"][2] and m["bbox"][1] <= c[1] <= m["bbox"][3]
                     and any(inside(c, r) for r in m["polys"])), None)
        if home is None:  # 해안선 단순화로 살짝 밖에 떨어진 곳은 가장 가까운 시·군·구로
            missed += 1
            home = min(munis, key=lambda m: math.hypot(m["c"][0] - c[0], m["c"][1] - c[1]))
        name = f["properties"]["adm_nm"].split()[-1]
        polys = [[[round(x, 5), round(y, 5)] for x, y in simplify(r, TOL)] for r in rings]
        polys = [p for p in polys if len(p) >= 4]
        out.setdefault(code_of[home["prov"]], {}).setdefault(home["name"], []).append(
            [name, [round(c[0], 5), round(c[1], 5)], polys])

    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for code, by_muni in sorted(out.items()):
        f = OUT / f"{code}.json"
        f.write_text(json.dumps(by_muni, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
        total += f.stat().st_size
    print(f"동 {len(feats)}곳 → {len(out)}개 파일, {total // 1024}KB (가까운 곳으로 붙인 동 {missed}곳)")


if __name__ == "__main__":
    sys.exit(main())
