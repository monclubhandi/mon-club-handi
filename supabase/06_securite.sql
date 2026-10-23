-- Sécurité : à coller une fois dans Supabase (SQL Editor > New query > Run).
-- 1. Les visiteurs (anon) ne peuvent ni modifier ni supprimer de club, même si une règle était ajoutée par erreur.
-- 2. Anti-spam : si un robot envoie des centaines de propositions directement à la base, les envois sont
--    refusés au-delà de 30 propositions en attente par heure (les vrais clubs proposés restent bien en dessous).

revoke update, delete, truncate, references, trigger on public.clubs from anon, authenticated;

create or replace function public.limiter_propositions() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from public.clubs where source = 'formulaire' and propose_le > now() - interval '1 hour') >= 30 then
    raise exception 'Trop de propositions en ce moment, réessaie plus tard.';
  end if;
  new.propose_le := now();
  return new;
end $$;

drop trigger if exists limiter_propositions on public.clubs;
create trigger limiter_propositions before insert on public.clubs
  for each row when (new.source = 'formulaire') execute function public.limiter_propositions();

-- Vérification : doit afficher seulement INSERT (la lecture est accordée colonne par colonne, sans les colonnes privées)
select grantee, string_agg(distinct privilege_type, ', ') as droits
from information_schema.role_table_grants
where table_schema = 'public' and table_name = 'clubs' and grantee in ('anon', 'authenticated')
group by grantee;
