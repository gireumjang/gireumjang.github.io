-- 「한 점」 가게마다 내 한마디 + 꼭 시킬 메뉴. Supabase 대시보드 › SQL Editor 에 통째로 붙여 넣고 Run. 다시 실행해도 안전.
-- 친구(로그인 안 한 anon)도 링크로 볼 수 있다. 쓰고 고치고 지우는 건 로그인한 본인만. (메모 kv 는 나만 보는 것, 이건 공개)
-- kv · sync_requests · votes · grades 테이블은 건드리지 않는다.

create table if not exists public.says (
  place_id   text primary key check (char_length(place_id) between 1 and 40),
  say        text not null default '' check (char_length(say) <= 120),
  dish       text not null default '' check (char_length(dish) <= 40),
  owner      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  updated_at timestamptz not null default now()
);
alter table public.says enable row level security;

drop policy if exists "says: 누구나 보기" on public.says;
create policy "says: 누구나 보기" on public.says for select to anon, authenticated using (true);
drop policy if exists "says: 본인만 넣기" on public.says;
create policy "says: 본인만 넣기" on public.says for insert to authenticated with check (owner = auth.uid());
drop policy if exists "says: 본인만 바꾸기" on public.says;
create policy "says: 본인만 바꾸기" on public.says for update to authenticated using (owner = auth.uid()) with check (owner = auth.uid());
drop policy if exists "says: 본인만 지우기" on public.says;
create policy "says: 본인만 지우기" on public.says for delete to authenticated using (owner = auth.uid());

-- 이 프로젝트는 새 테이블 권한을 자동으로 주지 않는다
grant usage on schema public to anon, authenticated;
revoke all on public.says from anon, authenticated;
grant select on public.says to anon, authenticated;
grant insert, update, delete on public.says to authenticated;
