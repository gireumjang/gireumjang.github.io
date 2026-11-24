-- 「한 점」 약속·투표. Supabase 대시보드 › SQL Editor 에 통째로 붙여 넣고 Run. 다시 실행해도 안전.
--
-- 친구는 로그인하지 않는다(anon). 테이블은 아무도 직접 못 읽고 쓴다 (RLS 켜고 정책 없음 + 권한 안 줌).
-- 대신 아래 함수들만 부를 수 있고, 함수는 투표 ID(추측 불가능한 32자)를 알아야 그 투표 하나만 보여 준다.
-- 투표 목록을 훑는 방법은 없다 (my_votes 는 로그인한 만든 사람 본인 것만).
-- kv · sync_requests 테이블은 건드리지 않는다.

create table if not exists public.votes (
  id          text primary key default replace(gen_random_uuid()::text, '-', ''),
  owner       uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title       text not null check (char_length(title) between 1 and 40),
  size        int  not null check (size between 2 and 12),
  status      text not null default 'gather' check (status in ('gather', 'computing', 'voting', 'closed')),
  compute_at  timestamptz,               -- 후보 계산을 맡은 시각 (2분 넘게 안 끝나면 다른 사람이 이어받음)
  candidates  jsonb,                     -- [{id, name, addr, phone, kind, area, sum, times: {pid: {min, real}}}] 최대 3곳
  winner      text,
  created_at  timestamptz not null default now(),
  closed_at   timestamptz
);
create table if not exists public.vote_people (
  id        bigint generated always as identity primary key,
  vote_id   text not null references public.votes (id) on delete cascade,
  name      text not null check (char_length(name) between 1 and 20),
  label     text not null check (char_length(label) between 1 and 40),
  lat       double precision not null check (lat between 33 and 39),
  lng       double precision not null check (lng between 124 and 132),
  token     uuid not null default gen_random_uuid(),   -- 이 기기만 아는 비밀 (투표할 때 확인)
  choice    text,
  joined_at timestamptz not null default now(),
  voted_at  timestamptz,
  unique (vote_id, name)
);
-- 먹고 싶은 것 (검색어, 비우면 저장한 곳 전체에서 고름)
alter table public.votes add column if not exists want text check (want is null or char_length(want) between 1 and 20);
create index if not exists vote_people_vote on public.vote_people (vote_id);
alter table public.votes enable row level security;
alter table public.vote_people enable row level security;
revoke all on public.votes, public.vote_people from anon, authenticated;

-- 화면에 보여 줄 투표 한 건 (토큰은 절대 안 내보냄, 각자 고른 곳은 마감 뒤에만)
create or replace function public.vote_json(v public.votes) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'id', v.id, 'title', v.title, 'want', v.want, 'size', v.size, 'status', v.status,
    'computing_stale', v.status = 'computing' and v.compute_at < now() - interval '2 minutes',
    'candidates', v.candidates, 'winner', v.winner, 'created_at', v.created_at, 'closed_at', v.closed_at,
    'is_owner', v.owner = auth.uid(),
    'people', coalesce((select jsonb_agg(jsonb_build_object(
        'pid', p.id, 'name', p.name, 'label', p.label, 'lat', p.lat, 'lng', p.lng,
        'voted', p.choice is not null,
        'choice', case when v.status = 'closed' then p.choice end) order by p.id)
      from public.vote_people p where p.vote_id = v.id), '[]'::jsonb));
$$;

create or replace function public.get_vote(p_id text) returns jsonb
language sql stable security definer set search_path = public as $$
  select public.vote_json(v) from public.votes v where v.id = p_id;
$$;

-- 만들기: 로그인한 사람만
drop function if exists public.create_vote(text, int);
create or replace function public.create_vote(p_title text, p_size int, p_want text default null) returns text
language plpgsql security definer set search_path = public as $$
declare vid text;
begin
  if auth.uid() is null then raise exception 'login_required'; end if;
  insert into public.votes (owner, title, size, want) values (auth.uid(), trim(p_title), p_size, nullif(trim(coalesce(p_want, '')), '')) returning id into vid;
  return vid;
end $$;

create or replace function public.my_votes() returns jsonb
language sql stable security definer set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', v.id, 'title', v.title, 'want', v.want, 'size', v.size, 'status', v.status,
           'created_at', v.created_at, 'n', (select count(*) from public.vote_people p where p.vote_id = v.id)) order by v.created_at desc), '[]'::jsonb)
  from (select * from public.votes where owner = auth.uid() order by created_at desc limit 20) v;
$$;

-- 참여: 이름 + 출발지. 이 기기에서 쓸 pid·token 을 돌려준다
create or replace function public.join_vote(p_id text, p_name text, p_label text, p_lat double precision, p_lng double precision) returns jsonb
language plpgsql security definer set search_path = public as $$
declare v public.votes; n int; me public.vote_people;
begin
  select * into v from public.votes where id = p_id for update;
  if not found then raise exception 'not_found'; end if;
  if v.status <> 'gather' then raise exception 'not_gathering'; end if;
  select count(*) into n from public.vote_people where vote_id = p_id;
  if n >= v.size then raise exception 'full'; end if;
  if exists (select 1 from public.vote_people where vote_id = p_id and name = trim(p_name)) then raise exception 'name_taken'; end if;
  insert into public.vote_people (vote_id, name, label, lat, lng)
    values (p_id, trim(p_name), trim(p_label), round(p_lat::numeric, 3), round(p_lng::numeric, 3)) returning * into me;
  return jsonb_build_object('pid', me.id, 'token', me.token);
end $$;

-- 모이는 중에 빠지기 (이 기기의 token 이 있어야)
create or replace function public.leave_vote(p_id text, p_pid bigint, p_token uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from public.vote_people p using public.votes v
    where v.id = p.vote_id and v.status = 'gather' and p.vote_id = p_id and p.id = p_pid and p.token = p_token;
end $$;

-- 만든 사람만: 덜 모였어도 지금 인원(2명 이상)으로 시작
create or replace function public.start_now(p_id text) returns void
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  select count(*) into n from public.vote_people where vote_id = p_id;
  if n < 2 then raise exception 'need_two'; end if;
  update public.votes set size = n where id = p_id and owner = auth.uid() and status = 'gather';
  if not found then raise exception 'not_allowed'; end if;
end $$;

-- 후보 계산 맡기: 다 모였으면 처음 부른 한 기기만 true. 2분 넘게 안 끝나면 다른 기기가 이어받는다
create or replace function public.claim_compute(p_id text) returns boolean
language plpgsql security definer set search_path = public as $$
declare v public.votes; n int;
begin
  select * into v from public.votes where id = p_id for update;
  if not found then return false; end if;
  select count(*) into n from public.vote_people where vote_id = p_id;
  if (v.status = 'gather' and n >= v.size and n >= 2)
     or (v.status = 'computing' and v.compute_at < now() - interval '2 minutes') then
    update public.votes set status = 'computing', compute_at = now() where id = p_id;
    return true;
  end if;
  return false;
end $$;

create or replace function public.save_candidates(p_id text, p_cands jsonb) returns void
language plpgsql security definer set search_path = public as $$
begin
  if jsonb_typeof(p_cands) <> 'array' or jsonb_array_length(p_cands) not between 1 and 3
     or octet_length(p_cands::text) > 20000 then raise exception 'bad_candidates'; end if;
  update public.votes set candidates = p_cands, status = 'voting' where id = p_id and status = 'computing';
end $$;

-- 마감 처리 (안에서만 씀): 표 많은 곳 → 같으면 이동시간 합 작은 곳 → 그래도 같으면 후보 순서
create or replace function public.finish_vote(p_id text) returns void
language plpgsql security definer set search_path = public as $$
declare v public.votes; win text;
begin
  select * into v from public.votes where id = p_id;
  select c->>'id' into win from jsonb_array_elements(v.candidates) with ordinality as t(c, i)
    order by (select count(*) from public.vote_people p where p.vote_id = p_id and p.choice = c->>'id') desc,
             (c->>'sum')::numeric asc, i asc limit 1;
  update public.votes set status = 'closed', winner = win, closed_at = now() where id = p_id;
end $$;

-- 투표 (마감 전엔 바꿀 수 있음). 모두 투표하면 자동 마감
create or replace function public.cast_vote(p_id text, p_pid bigint, p_token uuid, p_choice text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare v public.votes; left_n int;
begin
  select * into v from public.votes where id = p_id for update;
  if not found or v.status <> 'voting' then raise exception 'not_voting'; end if;
  if not exists (select 1 from jsonb_array_elements(v.candidates) c where c->>'id' = p_choice) then raise exception 'bad_choice'; end if;
  update public.vote_people set choice = p_choice, voted_at = now() where vote_id = p_id and id = p_pid and token = p_token;
  if not found then raise exception 'not_allowed'; end if;
  select count(*) into left_n from public.vote_people where vote_id = p_id and choice is null;
  if left_n = 0 then perform public.finish_vote(p_id); end if;
  return public.get_vote(p_id);
end $$;

-- 만든 사람만: 안 한 사람은 빼고 지금까지 들어온 표로 마감 (1표 이상 있어야)
create or replace function public.close_now(p_id text) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  perform 1 from public.votes where id = p_id and owner = auth.uid() and status = 'voting' for update;
  if not found then raise exception 'not_allowed'; end if;
  if not exists (select 1 from public.vote_people where vote_id = p_id and choice is not null) then raise exception 'no_votes'; end if;
  perform public.finish_vote(p_id);
  return public.get_vote(p_id);
end $$;

-- 함수는 기본으로 누구나(PUBLIC) 부를 수 있게 만들어지므로 먼저 막고 필요한 것만 연다
revoke execute on function public.vote_json(public.votes), public.finish_vote(text) from public, anon, authenticated;
revoke execute on function public.get_vote(text), public.create_vote(text, int, text), public.my_votes(),
  public.join_vote(text, text, text, double precision, double precision),
  public.leave_vote(text, bigint, uuid),
  public.start_now(text), public.close_now(text), public.claim_compute(text), public.save_candidates(text, jsonb),
  public.cast_vote(text, bigint, uuid, text) from public;
grant usage on schema public to anon, authenticated;
grant execute on function public.get_vote(text), public.join_vote(text, text, text, double precision, double precision),
  public.leave_vote(text, bigint, uuid),
  public.claim_compute(text), public.save_candidates(text, jsonb), public.cast_vote(text, bigint, uuid, text)
  to anon, authenticated;
grant execute on function public.create_vote(text, int, text), public.my_votes(), public.start_now(text), public.close_now(text) to authenticated;
