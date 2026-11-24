"""네이버 플레이스에 전화번호가 없는 가게를 네이버 검색 결과에서 찾아 채운다.

블로그 글에 다른 가게 번호가 섞여 나오는 경우가 많아서,
번호 바로 앞뒤(220자 안)에 '도로명+건물번호'가 같이 있을 때만 받아들인다 (가게 이름까지 있으면 가산점).
결과는 data/naver/{sid}.json 의 phoneSearch / phoneSearchAt 에 저장 (30일 안에 찾아본 곳은 건너뜀).

실행: python3 scripts/fill_phones.py
"""
import html
import json
import pathlib
import random
import re
import subprocess
import time
import urllib.parse
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAV = ROOT / "data" / "naver"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
PHONE = re.compile(r"(?<![\d-])(0\d{1,3}-\d{3,4}-\d{4})(?![\d-])")


def fetch(query):
    url = "https://m.search.naver.com/search.naver?" + urllib.parse.urlencode({"query": query})
    r = subprocess.run(["curl", "-s", "-L", "--max-time", "20", "-A", UA, "-H", "Accept-Language: ko-KR,ko;q=0.9", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def plain(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\\u002F", "/")
    return re.sub(r"\s+", " ", s)


def keys(d):
    name = re.sub(r"\s+", "", d["name"])
    short = re.sub(r"(본점|본관|\S+점)$", "", d["name"]).strip()
    road = d.get("roadAddress") or ""
    m = re.search(r"(\S+(?:로|길))\s*(\d+(?:-\d+)?)", road)
    roadkey = f"{m.group(1)} {m.group(2)}" if m else None
    return name, short, roadkey


def find_phone(d, text):
    name, short, roadkey = keys(d)
    squashed_ok = lambda w: w.replace(" ", "")
    votes = Counter()
    for m in PHONE.finditer(text):
        win = text[max(0, m.start() - 220): m.end() + 220]
        flat = win.replace(" ", "")
        near_name = (name and name in flat) or (len(short) >= 2 and squashed_ok(short) in flat)
        near_addr = roadkey and roadkey in win
        if near_addr:  # 이름만 맞는 건 블로그 코스 글 등에서 다른 가게 번호일 때가 많아 버린다
            votes[m.group(1)] += 2 if near_name else 1
    if not votes:
        return None
    phone, score = votes.most_common(1)[0]
    return phone if score >= 1 else None


def main():
    todo = []
    for f in sorted(NAV.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("error") or d.get("phone"):
            continue
        if d.get("phoneSearchAt") and time.time() - d["phoneSearchAt"] < 30 * 86400:
            continue
        todo.append((f, d))
    print(f"전화번호 없는 곳 {len(todo)}곳 검색", flush=True)
    found = 0
    for i, (f, d) in enumerate(todo, 1):
        road = d.get("roadAddress") or ""
        q = f'{d["name"]} {" ".join(road.split()[:2])}'.strip()
        try:
            phone = find_phone(d, plain(fetch(q)))
        except Exception as e:  # noqa: BLE001
            print(f"  ! {d['name']} {type(e).__name__}", flush=True)
            phone = None
        d["phoneSearch"] = phone
        d["phoneSearchAt"] = int(time.time())
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        if phone:
            found += 1
            print(f"  {d['name']}: {phone}", flush=True)
        time.sleep(random.uniform(2.5, 4.0))
    print(f"끝: {found}/{len(todo)}곳 찾음", flush=True)


if __name__ == "__main__":
    main()
