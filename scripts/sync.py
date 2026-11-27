"""'지금 동기화': 네이버 저장 목록을 다시 받아, 새로 저장한 가게만 수집하고 지도 데이터를 다시 만든다.

- 이미 받아둔 가게는 다시 받지 않는다 (후기·별점은 처음 저장할 때 1번만).
- 목록 받기가 실패하면 예전 목록을 그대로 쓴다 (덮어쓰지 않음).
- 네이버에서 저장을 지운 가게는 다음 빌드부터 지도에서 빠진다.

- data/ 가 비공개 저장소(gireumjang/hanjeom-data)를 받아 둔 폴더면: 시작할 때 받고(pull), 끝나면 올린다(push).
  그래서 PC와 GitHub 서버(cloud_sync.py) 어디서 돌려도 같은 자료를 이어 쓴다.

실행: python3 scripts/sync.py   (PC 동기화 버튼은 dev_server.py, 폰·배포 사이트는 GitHub Actions 의 cloud_sync.py 가 실행)
"""
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
# 공유 폴더 ID는 공개 저장소에 올리지 않는다 → data/shares.json  {"맛집리스트": "<shareId>", "찐맛집": "<shareId>"}
SHARES_FILE = ROOT / "data" / "shares.json"
API = "https://pages.map.naver.com/save-pages/api/maps-bookmark/v3/shares/{}/bookmarks?start=0&limit=5000"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def fetch_list(share):
    r = subprocess.run(["curl", "-s", "--max-time", "20", "-A", UA, API.format(share)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = json.loads(r.stdout)
    if not isinstance(d.get("bookmarkList"), list):
        raise ValueError("목록 형식이 다름")
    return d


def sids(d):
    return {b["sid"] for b in d["bookmarkList"] if b.get("sid")}


def data_git(*a):
    return subprocess.run(["git", "-C", str(ROOT / "data"), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    if (ROOT / "data" / ".git").exists():
        r = data_git("pull", "--ff-only", "-q")
        print("data: 받음" if r.returncode == 0 else f"data: 받기 실패 → 이 PC 자료로 계속 ({(r.stderr or '').strip()[:120]})", flush=True)
    if not SHARES_FILE.exists():
        sys.exit(f"{SHARES_FILE} 이 없어요 (공유 폴더 ID 설정)")
    shares = {k: v for k, v in json.loads(SHARES_FILE.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    before, after = set(), set()
    for name, share in shares.items():
        f = RAW / f"{name}.json"
        old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"bookmarkList": []}
        try:
            new = fetch_list(share)
            f.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8", newline="\n")
        except Exception as e:  # noqa: BLE001
            print(f"! {name} 목록 받기 실패 ({type(e).__name__}) → 예전 목록 그대로 씀", flush=True)
            new = old
        before |= sids(old)
        after |= sids(new)
        time.sleep(1.5)
    print(f"저장 목록 {len(after)}곳 · 새로 저장 {len(after - before)}곳 · 빠진 곳 {len(before - after)}곳", flush=True)

    for step in ("collect_naver.py", "fill_phones.py", "build_data.py"):
        print(f"== {step}", flush=True)
        subprocess.run([sys.executable, "-I", "-X", "utf8", str(ROOT / "scripts" / step)], check=False)
    publish()
    save_data()
    print("동기화 끝", flush=True)


def save_data():
    """수집 자료(data/)를 비공개 저장소에 올린다. data/ 가 저장소가 아니면 건너뜀."""
    if not (ROOT / "data" / ".git").exists():
        return
    data_git("add", "-A")
    if data_git("diff", "--cached", "--quiet").returncode == 0:
        return print("data: 바뀐 것 없음", flush=True)
    c = data_git("commit", "-q", "-m", f"수집 {time.strftime('%Y-%m-%d %H:%M')}")
    p = data_git("push", "-q", "origin", "HEAD:main") if c.returncode == 0 else c
    print("data: 올림" if p.returncode == 0 else f"data: 올리기 실패 {(p.stderr or p.stdout).strip()[:200]}", flush=True)


def publish():
    """바뀐 지도 데이터(app/)만 GitHub 에 올린다 → Actions 가 Pages 로 배포. 원격 저장소가 없으면 건너뜀."""
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if git("remote", "get-url", "origin").returncode != 0:
        return print("publish: origin 없음, 건너뜀", flush=True)
    git("add", "app")
    if git("diff", "--cached", "--quiet", "--", "app").returncode == 0:
        return print("publish: 바뀐 것 없음", flush=True)
    c = git("commit", "-m", f"데이터 갱신 {time.strftime('%Y-%m-%d')} (동기화)", "--", "app")
    p = git("push", "origin", "HEAD:main") if c.returncode == 0 else c
    print("publish: 올림" if p.returncode == 0 else f"publish 실패: {(p.stderr or p.stdout).strip()[:200]}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
