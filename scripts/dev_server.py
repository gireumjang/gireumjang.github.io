"""로컬 개발 서버: app/ 정적 파일 + /api/transit (네이버 지도 대중교통 경로를 대신 받아 요약해서 돌려줌)
+ /api/sync (앱의 동기화 버튼 → scripts/sync.py 실행, 진행 상황 조회)
+ 폰에서 남긴 동기화 요청(Supabase) 1분마다 처리 (data/supabase.json 이 있을 때).

브라우저는 네이버에 직접 요청할 수 없어서(CORS) 이 서버가 중계한다.
배포 후에는 같은 역할을 supabase/functions/transit 이 맡는다.

실행: python3 scripts/dev_server.py  →  http://localhost:5173
"""
import functools
import http.server
import json
import pathlib
import re
import subprocess
import sys
import threading
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
SYNC_LOG = ROOT / "data" / "sync.log"
sync_lock = threading.Lock()
sync_proc = None
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
COORD = re.compile(r"^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$")
WHEN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")  # 출발 시각 (한국 시간, 약속용)


def summarize(d):
    """네이버 응답에서 화면에 필요한 것만: 총 시간, 도보, 요금, 환승, 구간."""
    paths = d.get("paths") or []
    if not paths:
        return {"ok": False, "status": d.get("status")}
    p = paths[0]
    steps = []
    for leg in p.get("legs") or []:
        for st in leg.get("steps") or []:
            names = [r.get("name") for r in (st.get("routes") or []) if r.get("name")]
            stations = st.get("stations") or []
            steps.append({
                "type": st.get("type"),
                "min": st.get("duration"),
                "name": names[0] if names else None,
                "from": stations[0].get("displayName") if stations else None,
                "to": stations[-1].get("displayName") if stations else None,
            })
    return {
        "ok": True,
        "min": p.get("duration"),
        "walk": p.get("walkingDuration"),
        "fare": p.get("fare"),
        "transfers": p.get("transferCount"),
        "kind": d.get("status"),  # CITY / INTERCITY / WALK
        "steps": steps,
    }


def naver_transit(start, goal, when=None):
    q = {"start": start, "goal": goal, "crs": "EPSG:4326", "mode": "TIME", "lang": "ko"}
    if when:
        q["departureTime"] = when
    url = "https://map.naver.com/p/api/directions/pubtrans?" + urllib.parse.urlencode(q)
    r = subprocess.run(["curl", "-s", "--max-time", "12", "-A", UA, "-H", "Referer: https://map.naver.com/", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return summarize(json.loads(r.stdout))


def sync_status():
    running = sync_proc is not None and sync_proc.poll() is None
    lines = SYNC_LOG.read_text(encoding="utf-8", errors="replace").splitlines() if SYNC_LOG.exists() else []
    return {"ok": True, "running": running, "log": lines[-6:],
            "finishedAt": None if running or not SYNC_LOG.exists() else int(SYNC_LOG.stat().st_mtime)}


def start_sync():
    global sync_proc
    with sync_lock:
        if sync_proc is not None and sync_proc.poll() is None:
            return False
        log = SYNC_LOG.open("w", encoding="utf-8")
        sync_proc = subprocess.Popen([sys.executable, "-I", "-X", "utf8", str(ROOT / "scripts" / "sync.py")], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT)
        log.close()
        return True


def cloud_sync_loop():
    """폰에서 남긴 동기화 요청(Supabase sync_requests)을 1분마다 확인해 처리한다.
    data/supabase.json {"url": "...", "secret": "sb_secret_..."} 가 있을 때만 돈다 (secret 키는 저장소에 올리지 않음)."""
    import time
    import urllib.request
    if (ROOT / "data" / ".git").exists():   # 폰 요청은 이제 GitHub 서버(cloud_sync.py)가 처리 → PC는 안 가져감 (둘이 같이 돌면 네이버 요청이 두 배)
        return print("폰 동기화 요청은 GitHub 서버가 처리 (PC 확인 꺼짐)", flush=True)
    cfg_file = ROOT / "data" / "supabase.json"
    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        url, key = cfg["url"].rstrip("/"), cfg["secret"]
        if not key.startswith("sb_secret_"):
            return
    except Exception:  # noqa: BLE001 — 설정이 없으면 폰 동기화만 꺼진다
        return

    def call(method, path, body=None):
        req = urllib.request.Request(f"{url}/rest/v1/{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"apikey": key, "Content-Type": "application/json", "Prefer": "return=minimal"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    print("폰 동기화 요청 확인 켜짐 (1분마다)", flush=True)
    while True:
        try:
            pending = call("GET", "sync_requests?status=eq.pending&select=id&order=id")
            if pending and start_sync():
                ids = ",".join(str(r["id"]) for r in pending)
                call("PATCH", f"sync_requests?id=in.({ids})&status=eq.pending", {"status": "running"})
                while sync_proc.poll() is None:
                    time.sleep(5)
                lines = SYNC_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
                summary = next((l for l in lines if l.startswith("저장 목록")), lines[-1] if lines else "")
                call("PATCH", f"sync_requests?id=in.({ids})", {
                    "status": "done" if sync_proc.returncode == 0 else "failed",
                    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "summary": summary[:300]})
        except Exception as e:  # noqa: BLE001 — 인터넷이 잠깐 끊겨도 다음 확인 때 다시
            print(f"폰 동기화 확인 실패: {type(e).__name__}", flush=True)
        time.sleep(60)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/sync":
            return self._json(404, {"ok": False})
        # 다른 사이트가 몰래 부르지 못하게: 커스텀 헤더가 있으면 브라우저가 사전 확인을 하고, 여기선 허락하지 않는다
        if self.headers.get("X-Hanjeom") != "sync":
            return self._json(403, {"ok": False})
        started = start_sync()
        return self._json(200, {**sync_status(), "started": started})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/sync":
            return self._json(200, sync_status())
        if u.path == "/api/transit":
            q = urllib.parse.parse_qs(u.query)
            start, goal = (q.get("start") or [""])[0], (q.get("goal") or [""])[0]
            if not (COORD.match(start) and COORD.match(goal)):
                return self._json(400, {"ok": False, "error": "start/goal = lng,lat"})
            when = (q.get("time") or [""])[0]
            try:
                return self._json(200, naver_transit(start, goal, when if WHEN.match(when) else None))
            except Exception as e:  # noqa: BLE001
                return self._json(502, {"ok": False, "error": type(e).__name__})
        return super().do_GET()

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 5173), functools.partial(Handler, directory=str(APP)))
    print("http://localhost:5173", flush=True)
    threading.Thread(target=cloud_sync_loop, daemon=True).start()
    srv.serve_forever()
