-- ============================================================
-- Migration: create product_reviews table
-- Run in Supabase SQL Editor
-- ============================================================

create table if not exists public.product_reviews (
  id            uuid primary key default gen_random_uuid(),
  product_id    text not null,
  company_id    uuid references public.company_mapping(company_id_uuid) on delete cascade,
  reviewer_name text not null default 'Anonyme',
  text          text not null,
  rating        smallint not null check (rating >= 1 and rating <= 5),
  created_at    timestamptz not null default now()
);

-- Index for fast lookup per product
create index if not exists idx_product_reviews_product_id on public.product_reviews(product_id);
create index if not exists idx_product_reviews_company_id on public.product_reviews(company_id);

-- RLS: anyone can read reviews for a product
alter table public.product_reviews enable row level security;

create policy "Public read product reviews"
  on public.product_reviews for select
  using (true);

create policy "Public insert product reviews"
  on public.product_reviews for insert
  with check (true);
