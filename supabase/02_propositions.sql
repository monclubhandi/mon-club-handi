-- Étape « Inscrire mon club » : les propositions du formulaire arrivent dans la table clubs, masquées.
-- Tu les vérifies dans Table Editor, puis tu coches « publie » pour les afficher dans l'appli.

-- 1. Colonnes privées (jamais visibles depuis le site)
alter table public.clubs add column if not exists propose_par text;   -- email de la personne qui propose
alter table public.clubs add column if not exists message     text;   -- son message pour toi
alter table public.clubs add column if not exists propose_le  timestamptz;

-- 2. Garde-fous contre les abus : longueurs maximales
alter table public.clubs drop constraint if exists clubs_longueurs;
alter table public.clubs add constraint clubs_longueurs check (
  char_length(nom) <= 150 and char_length(sport) <= 60
  and char_length(coalesce(adresse, '')) <= 200 and char_length(coalesce(ville, '')) <= 80
  and char_length(coalesce(code_postal, '')) <= 5 and char_length(coalesce(handicaps, '')) <= 200
  and char_length(coalesce(creneaux, '')) <= 1500 and char_length(coalesce(accessibilite, '')) <= 1000
  and char_length(coalesce(telephone, '')) <= 30 and char_length(coalesce(email, '')) <= 120
  and char_length(coalesce(site, '')) <= 300 and char_length(coalesce(essai, '')) <= 1000
  and char_length(coalesce(propose_par, '')) <= 120 and char_length(coalesce(message, '')) <= 1500
);

-- 3. Le site ne peut lire que les colonnes publiques (les colonnes privées restent cachées)
revoke select on public.clubs from anon, authenticated;
grant select (id, sport, nom, adresse, code_postal, ville, handicaps, pratique, creneaux, accessibilite,
              telephone, email, site, label, para_sportifs, encadrant_forme, verifie_le, essai,
              latitude, longitude, source, publie, cree_le)
  on public.clubs to anon, authenticated;

-- 4. Le formulaire peut AJOUTER un club, uniquement masqué et sans badge de confiance
grant insert on public.clubs to anon, authenticated;
drop policy if exists "Propositions depuis le formulaire" on public.clubs;
create policy "Propositions depuis le formulaire"
  on public.clubs for insert
  to anon, authenticated
  with check (
    publie = false and para_sportifs = false and encadrant_forme = false
    and label is null and verifie_le is null and source = 'formulaire'
  );
