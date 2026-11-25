-- 「한 점」 내 맛집 등급 (S·A·B·C). Supabase 대시보드 › SQL Editor 에 통째로 붙여 넣고 Run. 다시 실행해도 안전.
-- 친구(로그인 안 한 anon)도 링크로 등급을 볼 수 있다. 매기고 바꾸고 지우는 건 로그인한 본인만.
-- kv · sync_requests · votes 테이블은 건드리지 않는다.

create table if not exists public.grades (
  place_id   text primary key check (char_length(place_id) between 1 and 40),
  grade      text not null check (grade in ('S', 'A', 'B', 'C')),
  owner      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  updated_at timestamptz not null default now()
);
alter table public.grades enable row level security;

drop policy if exists "grades: 누구나 보기" on public.grades;
create policy "grades: 누구나 보기" on public.grades for select to anon, authenticated using (true);
drop policy if exists "grades: 본인만 넣기" on public.grades;
create policy "grades: 본인만 넣기" on public.grades for insert to authenticated with check (owner = auth.uid());
drop policy if exists "grades: 본인만 바꾸기" on public.grades;
create policy "grades: 본인만 바꾸기" on public.grades for update to authenticated using (owner = auth.uid()) with check (owner = auth.uid());
drop policy if exists "grades: 본인만 지우기" on public.grades;
create policy "grades: 본인만 지우기" on public.grades for delete to authenticated using (owner = auth.uid());

-- 이 프로젝트는 새 테이블 권한을 자동으로 주지 않는다
grant usage on schema public to anon, authenticated;
revoke all on public.grades from anon, authenticated;
grant select on public.grades to anon, authenticated;
grant insert, update, delete on public.grades to authenticated;
