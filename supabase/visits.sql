-- 「한 점」 방문자 수. Supabase 대시보드 › SQL Editor 에 통째로 붙여 넣고 Run. 다시 실행해도 안전.
-- 기기마다 아무 뜻 없는 번호(앱이 만들어 localStorage에 둠)로 하루 1번만 센다. 이름·IP 같은 개인 정보는 남기지 않는다.
-- 표(hits)는 아무도 직접 못 읽고 못 쓴다. 기록은 hit() 함수로만(누구나), 숫자 보기는 hit_stats() 로만(로그인한 나만).
-- kv · sync_requests · votes · grades · says 테이블은 건드리지 않는다.

create table if not exists public.hits (
  day date not null default (now() at time zone 'Asia/Seoul')::date,
  device text not null check (char_length(device) between 8 and 40),
  kind text not null,   -- open: 앱을 엶 / place: 가게 상세를 엶 / from: 어디서 들어왔나 (ref = insta·kakao·naver…)
  ref text not null default '' check (char_length(ref) <= 40),   -- open: ''·share(가게 링크)·vote(약속 링크) / place: 가게 id
  at timestamptz not null default now(),
  primary key (day, device, kind, ref)
);
alter table public.hits drop constraint if exists hits_kind_check;
alter table public.hits add constraint hits_kind_check check (kind in ('open', 'place', 'from'));
alter table public.hits enable row level security;
revoke all on public.hits from anon, authenticated;

-- 기록: 같은 기기·같은 날·같은 것은 한 번만
create or replace function public.hit(p_device text, p_kind text, p_ref text default '')
returns void language sql security definer set search_path = public as $$
  insert into hits (device, kind, ref) values (p_device, p_kind, coalesce(p_ref, '')) on conflict do nothing;
$$;
revoke execute on function public.hit(text, text, text) from public;
grant execute on function public.hit(text, text, text) to anon, authenticated;

-- 숫자 보기: 로그인한 나만 (새 가입은 막혀 있어 계정은 나 하나)
create or replace function public.hit_stats()
returns json language sql stable security definer set search_path = public as $$
  with k as (select (now() at time zone 'Asia/Seoul')::date as t)
  select json_build_object(
    'today', (select count(distinct device) from hits, k where kind = 'open' and day = k.t),
    'week',  (select count(distinct device) from hits, k where kind = 'open' and day > k.t - 7),
    'month', (select count(distinct device) from hits, k where kind = 'open' and day > k.t - 30),
    'total', (select count(distinct device) from hits where kind = 'open'),
    'share', (select count(*) from hits, k where kind = 'open' and ref = 'share' and day > k.t - 30),
    'vote',  (select count(*) from hits, k where kind = 'open' and ref = 'vote' and day > k.t - 30),
    'days',  (select coalesce(json_agg(json_build_object('d', d, 'n', n) order by d), '[]'::json)
              from (select day as d, count(distinct device) as n from hits, k where kind = 'open' and day > k.t - 14 group by day) x),
    'from',  (select coalesce(json_agg(json_build_object('s', ref, 'n', n) order by n desc), '[]'::json)
              from (select ref, count(distinct device) as n from hits, k where kind = 'from' and day > k.t - 30 group by ref) z),
    'top',   (select coalesce(json_agg(json_build_object('id', ref, 'n', n) order by n desc), '[]'::json)
              from (select ref, count(*) as n from hits, k where kind = 'place' and day > k.t - 30 group by ref order by n desc limit 10) y)
  );
$$;
revoke execute on function public.hit_stats() from public, anon;
grant execute on function public.hit_stats() to authenticated;
