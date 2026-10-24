-- Retire les clubs importés depuis le livret Savoie (CDOS 73), faute d'accord écrit de l'éditeur.
-- Sans effet si le fichier 11_import_savoie.sql n'a jamais été lancé.
delete from public.clubs where source = 'Livret Sport et handicap en Savoie 2025-2026, CDOS de la Savoie';
