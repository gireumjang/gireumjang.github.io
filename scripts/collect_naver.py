"""저장한 식당마다 네이버 플레이스 홈 페이지에서 메뉴/후기 요약을 모은다.

- 한 곳당 페이지 1번 요청 (홈 페이지에 메뉴, 후기 통계가 다 들어있음)
- 결과는 data/naver/{sid}.json 으로 캐시 → 중간에 끊겨도 이어서 실행 가능
- 네이버에 부담 주지 않게 요청 사이 2.5~4초 쉼 (빠르면 429로 막힘)

실행: python3 scripts/collect_naver.py            (전체, 이미 받은 곳은 건너뜀)
      python3 scripts/collect_naver.py --limit 5  (시험용)
      python3 scripts/collect_naver.py --refresh  (캐시 무시하고 다시)
"""
import argparse
import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "naver"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


class Blocked(Exception):
    pass


def fetch(url):
    # Python urllib 요청은 네이버가 429로 막아서 curl 로 가져온다.
    r = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "20", "-A", UA, "-H", "Accept-Language: ko-KR,ko;q=0.9",
         "-w", "\n__HTTP__%{http_code}", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    body, _, code = r.stdout.rpartition("\n__HTTP__")
    if code in ("429", "403"):
        raise Blocked(code)
    if code != "200":
        raise RuntimeError(f"HTTP {code}")
    return body


def apollo(html):
    i = html.find("window.__APOLLO_STATE__")
    if i < 0:
        return None
    i = html.index("{", i)
    obj, _ = json.JSONDecoder().raw_decode(html[i:])
    return obj


def parse(sid, st):
    base = st.get(f"PlaceDetailBase:{sid}")
    if not base:
        return None
    stats = st.get(f"VisitorReviewStatsResult:{sid}") or {}
    analysis = stats.get("analysis") or {}
    review = stats.get("review") or {}

    menus = []
    for k, v in st.items():
        if not k.startswith("PlaceMenuItem:"):
            continue
        price = (v.get("price") or {}).get("displayText")
        menus.append({
            "name": v.get("name"),
            "price": price,
            "img": v.get("thumbnailUrl"),
            "desc": v.get("description"),
            "badges": [b if isinstance(b, str) else b.get("name") or b.get("text") for b in (v.get("badges") or [])],
        })

    review_menus = [{"name": m["label"], "count": m["count"]} for m in (analysis.get("menus") or [])][:10]
    voted = (analysis.get("votedKeyword") or {}).get("details") or []
    keywords = [{"name": d["displayName"], "count": d["count"], "icon": d.get("iconUrl")} for d in voted][:6]

    # 영업시간: 요일별 {start, end} / 휴무면 None + 설명
    hours = {}
    rq = st.get("ROOT_QUERY") or {}
    pd = next((v for k, v in rq.items() if k.startswith("placeDetail")), {}) or {}
    for nb in (pd.get("newBusinessHours") or [])[:1]:
        for d in nb.get("businessHours") or []:
            bh = d.get("businessHours")
            hours[d.get("day")] = {
                "start": bh.get("start") if bh else None,
                "end": bh.get("end") if bh else None,
                "breaks": [[b.get("start"), b.get("end")] for b in (d.get("breakHours") or []) if b],
                "last": (d.get("lastOrderTimes") or [{}])[0].get("time") if d.get("lastOrderTimes") else None,
                "note": d.get("description"),
            }

    return {
        "sid": sid,
        "hours": hours or None,
        "name": base.get("name"),
        "category": base.get("category"),
        "roadAddress": base.get("roadAddress"),
        "phone": base.get("phone") or base.get("virtualPhone"),
        "rating": base.get("visitorReviewsScore") or review.get("avgRating"),
        "visitorReviews": base.get("visitorReviewsTotal"),
        "blogReviews": base.get("cafeBlogReviewsTotal"),
        "oneLiner": (base.get("microReviews") or [None])[0],
        "menus": menus,
        "reviewMenus": review_menus,
        "keywords": keywords,
        "fetchedAt": int(time.time()),
    }


HIST = OUT / "history"


def snapshot(d):
    """주간 평균을 내기 위해 별점/후기 수/추천 메뉴를 한 줄씩 쌓는다 (같은 날 중복은 건너뜀)."""
    HIST.mkdir(parents=True, exist_ok=True)
    f = HIST / f"{d['sid']}.jsonl"
    day = time.strftime("%Y-%m-%d", time.localtime(d["fetchedAt"]))
    if f.exists() and f'"day": "{day}"' in f.read_text(encoding="utf-8"):
        return
    row = {"t": d["fetchedAt"], "day": day, "rating": d.get("rating"), "vr": d.get("visitorReviews"),
           "br": d.get("blogReviews"), "reviewMenus": d.get("reviewMenus", [])[:6]}
    with f.open("a", encoding="utf-8", newline="\n") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def place_ids():
    seen = {}
    for f in ("맛집리스트.json", "찐맛집.json"):
        for b in json.loads((RAW / f).read_text(encoding="utf-8"))["bookmarkList"]:
            if b.get("sid"):
                seen[b["sid"]] = b["name"]
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--backfill-history", action="store_true", help="이미 받은 결과로 첫 기록만 만든다")
    args = ap.parse_args()
    if args.backfill_history:
        n = 0
        for f in OUT.glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            if not d.get("error"):
                snapshot(d); n += 1
        print(f"기록 {n}곳"); return

    OUT.mkdir(parents=True, exist_ok=True)
    ids = place_ids()
    def need(s):
        f = OUT / f"{s}.json"
        return args.refresh or not f.exists() or '"error": true' in f.read_text(encoding="utf-8")
    todo = [s for s in ids if need(s)]
    if args.limit:
        todo = todo[: args.limit]
    print(f"전체 {len(ids)}곳 / 이번에 수집 {len(todo)}곳", flush=True)

    ok = fail = 0
    backoff = 0
    for n, sid in enumerate(todo, 1):
        data = None
        for kind in ("restaurant", "place"):
            try:
                st = apollo(fetch(f"https://m.place.naver.com/{kind}/{sid}/home"))
                data = parse(sid, st) if st else None
                backoff = 0
            except Blocked as e:
                backoff = min(300, (backoff or 30) * 2)
                print(f"  ! {e} 차단 감지 → {backoff}초 쉬고 다시", flush=True)
                time.sleep(backoff)
                try:
                    st = apollo(fetch(f"https://m.place.naver.com/{kind}/{sid}/home"))
                    data = parse(sid, st) if st else None
                except Exception:
                    data = None
            except Exception as e:  # 네트워크 등
                print(f"  ! {sid} {type(e).__name__}", flush=True)
            if data:
                break
            time.sleep(0.6)
        if data:
            old_f = OUT / f"{sid}.json"
            if old_f.exists():  # 검색으로 보강한 전화번호는 유지
                old = json.loads(old_f.read_text(encoding="utf-8"))
                for k in ("phoneSearch", "phoneSearchAt"):
                    if k in old:
                        data[k] = old[k]
            (OUT / f"{sid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
            snapshot(data)
            ok += 1
        else:
            f = OUT / f"{sid}.json"
            # 실패해도 예전에 잘 받아둔 데이터는 덮어쓰지 않는다 (잠자기·네트워크 끊김 대비)
            if not f.exists() or '"error": true' in f.read_text(encoding="utf-8"):
                f.write_text(json.dumps({"sid": sid, "name": ids[sid], "error": True, "fetchedAt": int(time.time())}, ensure_ascii=False), encoding="utf-8")
            fail += 1
        if n % 25 == 0 or n == len(todo):
            print(f"{n}/{len(todo)}  성공 {ok}  실패 {fail}", flush=True)
        time.sleep(random.uniform(2.5, 4.0))
    print("끝", flush=True)


if __name__ == "__main__":
    sys.exit(main())
