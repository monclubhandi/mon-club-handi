-- « Un club = une fiche » : plusieurs sports dans la colonne sport (séparés par des virgules),
-- et la base refuse désormais tout doublon (même nom et même code postal).

-- 1. La colonne sport peut contenir plusieurs sports
alter table public.clubs drop constraint if exists clubs_longueurs;
alter table public.clubs add constraint clubs_longueurs check (
  char_length(nom) <= 150 and char_length(sport) <= 400
  and char_length(coalesce(adresse, '')) <= 200 and char_length(coalesce(ville, '')) <= 80
  and char_length(coalesce(code_postal, '')) <= 5 and char_length(coalesce(handicaps, '')) <= 200
  and char_length(coalesce(creneaux, '')) <= 1500 and char_length(coalesce(accessibilite, '')) <= 1000
  and char_length(coalesce(telephone, '')) <= 60 and char_length(coalesce(email, '')) <= 120
  and char_length(coalesce(site, '')) <= 300 and char_length(coalesce(essai, '')) <= 1000
  and char_length(coalesce(propose_par, '')) <= 120 and char_length(coalesce(message, '')) <= 1500
);

-- 2. Fusion des clubs déjà présents en plusieurs lignes (un sport par ligne) en une seule fiche
with groupes as (
  select min(id) as garde, string_agg(distinct sport, ', ') as sports
  from public.clubs
  group by regexp_replace(lower(nom), '[^a-z0-9]', '', 'g'), coalesce(code_postal, '')
  having count(*) > 1
)
update public.clubs c set sport = g.sports from groupes g where c.id = g.garde;

delete from public.clubs c
using public.clubs d
where regexp_replace(lower(c.nom), '[^a-z0-9]', '', 'g') = regexp_replace(lower(d.nom), '[^a-z0-9]', '', 'g')
  and coalesce(c.code_postal, '') = coalesce(d.code_postal, '')
  and c.id > d.id;

-- 3. Plus jamais de doublon : même nom (sans tenir compte des majuscules, espaces et tirets) + même code postal
create unique index if not exists clubs_sans_doublon
  on public.clubs (regexp_replace(lower(nom), '[^a-z0-9]', '', 'g'), coalesce(code_postal, ''));
