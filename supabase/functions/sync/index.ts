// 「한 점」 동기화 신호: 로그인한 나만 → GitHub 비공개 저장소(gireumjang/hanjeom-data)의 Actions 를 깨운다.
// 앱이 sync_requests 에 요청을 남긴 뒤 이 함수를 부르고, Actions 의 cloud_sync.py 가 처리해서 상태를 적는다.
// 대시보드 › Edge Functions › sync 에 붙여 넣어 배포. Verify JWT 켬.
// Secrets: GH_PAT (gireumjang.github.io · hanjeom-data 두 저장소 Contents 읽기/쓰기 토큰), ALLOW_ORIGIN=https://gireumjang.github.io
const ALLOW = (Deno.env.get("ALLOW_ORIGIN") ?? "").split(",").map((s) => s.trim()).filter(Boolean);
const REPO = "gireumjang/hanjeom-data";

const cors = (origin: string | null) => ({
  "Access-Control-Allow-Origin": origin && ALLOW.includes(origin) ? origin : ALLOW[0] ?? "",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
});

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin");
  if (req.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
  const h = cors(origin);
  if (ALLOW.length && (!origin || !ALLOW.includes(origin))) return new Response("forbidden", { status: 403 });

  // 로그인한 사람인지 (익명 키만 들고 온 요청은 거절). 새 가입은 막혀 있어 계정은 나 하나
  const auth = req.headers.get("Authorization") ?? "";
  const u = await fetch(`${Deno.env.get("SUPABASE_URL")}/auth/v1/user`, {
    headers: { Authorization: auth, apikey: Deno.env.get("SUPABASE_ANON_KEY") ?? "" },
  });
  if (!u.ok) return Response.json({ ok: false, error: "login" }, { status: 401, headers: h });

  const r = await fetch(`https://api.github.com/repos/${REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${Deno.env.get("GH_PAT")}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "hanjeom-sync",
    },
    body: JSON.stringify({ event_type: "sync" }),
  });
  return Response.json({ ok: r.status === 204, status: r.status }, { status: r.status === 204 ? 200 : 502, headers: h });
});
