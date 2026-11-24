-- 「한 점」 Supabase 테이블. Supabase 대시보드 › SQL Editor 에 통째로 붙여 넣고 Run.
-- 모든 행은 로그인한 본인만 읽고 쓸 수 있다 (친구에게 공유한 링크로는 아무것도 안 보임).

-- 방문 기록·메모 등 개인 기록: 사용자마다 key 하나에 JSON 하나 ("visits", "notes")
create table if not exists public.kv (
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  key        text not null,
  value      jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, key)
);
alter table public.kv enable row level security;
drop policy if exists "kv: 본인만" on public.kv;
create policy "kv: 본인만" on public.kv
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- 폰에서 누른 '동기화' 요청. 데스크탑의 dev_server.py 가 켜져 있을 때 가져가서 처리한다.
create table if not exists public.sync_requests (
  id           bigint generated always as identity primary key,
  user_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  requested_at timestamptz not null default now(),
  status       text not null default 'pending' check (status in ('pending', 'running', 'done', 'failed')),
  finished_at  timestamptz,
  summary      text
);
alter table public.sync_requests enable row level security;
drop policy if exists "sync: 본인 요청 보기" on public.sync_requests;
create policy "sync: 본인 요청 보기" on public.sync_requests
  for select to authenticated using (user_id = auth.uid());
drop policy if exists "sync: 본인 요청 넣기" on public.sync_requests;
create policy "sync: 본인 요청 넣기" on public.sync_requests
  for insert to authenticated with check (user_id = auth.uid());
-- 처리(상태 바꾸기)는 데스크탑이 service_role 키로 한다 → 일반 사용자 update 정책은 두지 않음

-- 이 프로젝트는 새 테이블 권한을 자동으로 주지 않는다. 로그인한 사용자(authenticated)에게만 연다 (로그인 안 한 anon은 없음).
grant usage on schema public to authenticated;
grant select, insert, update, delete on public.kv to authenticated;
grant select, insert on public.sync_requests to authenticated;
grant select, insert, update on public.kv, public.sync_requests to service_role;
