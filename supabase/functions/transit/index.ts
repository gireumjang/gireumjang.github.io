// 배포용 대중교통 중계 (Supabase Edge Function).
// 로컬의 scripts/dev_server.py /api/transit 과 같은 일을 한다:
// 네이버 지도 대중교통 경로를 받아 화면에 필요한 요약만 돌려준다.
//
// 배포:  supabase functions deploy transit --no-verify-jwt
// 그 다음 app/config.js 의 transitProxy 에 https://<프로젝트>.supabase.co/functions/v1/transit 를 넣는다.

const COORD = /^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$/;
const WHEN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;  // 출발 시각 (한국 시간, 약속용)
// 내 GitHub Pages 주소만 허용 (다른 사이트가 이 중계를 쓰지 못하게)
const ALLOW = (Deno.env.get("ALLOW_ORIGIN") ?? "").split(",").map((s) => s.trim()).filter(Boolean);

const cors = (origin: string | null) => ({
  "Access-Control-Allow-Origin": origin && ALLOW.includes(origin) ? origin : ALLOW[0] ?? "",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Vary": "Origin",
});

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin");
  if (req.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
  // 내 사이트에서 온 요청만 (주소가 안 붙은 요청도 막음 — 브라우저는 다른 사이트로 보낼 때 항상 Origin을 붙임)
  if (ALLOW.length && (!origin || !ALLOW.includes(origin))) return new Response("forbidden", { status: 403 });

  const u = new URL(req.url);
  const start = u.searchParams.get("start") ?? "", goal = u.searchParams.get("goal") ?? "";
  if (!COORD.test(start) || !COORD.test(goal)) {
    return Response.json({ ok: false, error: "start/goal = lng,lat" }, { status: 400, headers: cors(origin) });
  }
  const q = new URLSearchParams({ start, goal, crs: "EPSG:4326", mode: "TIME", lang: "ko" });
  const when = u.searchParams.get("time") ?? "";
  if (WHEN.test(when)) q.set("departureTime", when);
  try {
    const r = await fetch(`https://map.naver.com/p/api/directions/pubtrans?${q}`, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Referer": "https://map.naver.com/",
      },
    });
    const d = await r.json();
    const p = d.paths?.[0];
    if (!p) return Response.json({ ok: false, status: d.status }, { headers: cors(origin) });
    const steps = (p.legs ?? []).flatMap((leg: any) => (leg.steps ?? []).map((st: any) => ({
      type: st.type,
      min: st.duration,
      name: st.routes?.[0]?.name ?? null,
      from: st.stations?.[0]?.displayName ?? null,
      to: st.stations?.at(-1)?.displayName ?? null,
    })));
    return Response.json({
      ok: true, min: p.duration, walk: p.walkingDuration, fare: p.fare,
      transfers: p.transferCount, kind: d.status, steps,
    }, { headers: { ...cors(origin), "Cache-Control": "public, max-age=300" } });
  } catch (e) {
    return Response.json({ ok: false, error: String(e) }, { status: 502, headers: cors(origin) });
  }
});
