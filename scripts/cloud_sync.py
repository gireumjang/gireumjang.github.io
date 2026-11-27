"""GitHub 서버(비공개 저장소 hanjeom-data 의 Actions)에서 도는 동기화.

폰·PC 어디서든 로그인하고 '↻ 동기화'를 누르면: 앱이 Supabase sync_requests 에 요청을 남기고
→ Supabase 함수 sync 가 GitHub 에 신호(repository_dispatch) → 이 스크립트가
  1) 기다리는 요청을 '처리 중'으로 가져오고  2) sync.py 를 돌리고  3) 끝/실패를 적는다.
sync.py 가 data/(비공개 저장소)와 app/(공개 저장소)를 각각 올린다.

환경 변수: SUPABASE_URL, SUPABASE_SECRET (sb_secret_… — Actions secret 에만 둔다)
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SECRET", "")


def call(method, path, body=None, prefer="return=minimal"):
    req = urllib.request.Request(f"{URL}/rest/v1/{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json", "Prefer": prefer})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main():
    ids = []
    if URL and KEY:
        try:   # 기다리는 요청만 '처리 중'으로 (PC 서버가 먼저 가져간 건 안 건드림)
            got = call("PATCH", "sync_requests?status=eq.pending", {"status": "running"}, prefer="return=representation")
            ids = [r["id"] for r in got or []]
        except Exception as e:  # noqa: BLE001
            print(f"요청 가져오기 실패: {type(e).__name__}", flush=True)
    print(f"동기화 요청 {len(ids)}개", flush=True)

    p = subprocess.run([sys.executable, "-I", "-X", "utf8", str(ROOT / "scripts" / "sync.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(out, flush=True)
    lines = out.splitlines()
    summary = next((l for l in lines if l.startswith("저장 목록")), lines[-1] if lines else "")
    ok = p.returncode == 0 and "동기화 끝" in out

    if ids:
        try:
            call("PATCH", f"sync_requests?id=in.({','.join(map(str, ids))})", {
                "status": "done" if ok else "failed",
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "summary": summary[:300]})
        except Exception as e:  # noqa: BLE001
            print(f"결과 적기 실패: {type(e).__name__}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
