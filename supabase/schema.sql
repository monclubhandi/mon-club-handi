-- Table des clubs : une ligne par club, sport et lieu de pratique
create table public.clubs (
  id               bigint generated always as identity primary key,
  sport            text not null,
  nom              text not null,
  adresse          text,
  code_postal      text,
  ville            text,
  handicaps        text,
  pratique         text,
  creneaux         text,
  accessibilite    text,
  telephone        text,
  email            text,
  site             text,
  label            text,
  para_sportifs    boolean not null default false,
  encadrant_forme  boolean not null default false,
  verifie_le       date,
  essai            text,
  latitude         double precision,
  longitude        double precision,
  source           text,
  publie           boolean not null default true,
  cree_le          timestamptz not null default now()
);

alter table public.clubs enable row level security;

create policy "Lecture publique des clubs publiés"
  on public.clubs for select
  to anon, authenticated
  using (publie = true);
