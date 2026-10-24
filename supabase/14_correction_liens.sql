-- Contrôle des liens vers les sites des clubs (24 octobre 2026).
-- 1. Lien racheté par un site de casino : retiré.
update public.clubs set site = null where site = 'https://www.tccourseulles.com/';
-- 2. Pages qui n'existent plus (erreur 404) : liens retirés.
update public.clubs set site = null where site in (
  'https://esfalaisetennisdet.wixsite.com/website',
  'http://www.charavoile-asnelles.net/spip/',
  'http://www.capsport-epi.fr/adapte/');
-- 3. Sites qui fonctionnent en version sécurisée : http:// remplacé par https://
update public.clubs set site = 'https://gagny-judo-club.com/' where site = 'http://www.gagny-judo-club.com';
update public.clubs set site = 'https://www.asbondy.com' where site = 'http://www.asbondy.com';
update public.clubs set site = 'https://www.tremblayathletiqueclub.fr/page/1718007-handisport' where site = 'http://www.tremblayathletiqueclub.fr/page/1718007-handisport';
update public.clubs set site = 'https://www.staarp.org' where site = 'http://www.staarp.org';
update public.clubs set site = 'https://ja-drancy.com/' where site = 'http://www.ja-drancy.com';
update public.clubs set site = 'https://www.escrimebondy.net' where site = 'http://www.escrimebondy.net';
update public.clubs set site = 'https://www.vsescrime.net' where site = 'http://www.vsescrime.net';
update public.clubs set site = 'https://csntt.fr/' where site = 'http://www.noisy-tennis-de-table.fr';
update public.clubs set site = 'https://www.ganoisy93.com' where site = 'http://www.ganoisy93.com';
update public.clubs set site = 'https://normandiebad.com/Bapadoz/' where site = 'http://normandiebad.com/Bapadoz/';
update public.clubs set site = 'https://www.agcaen.com/sport/basket/1' where site = 'http://www.agcaen.com/sport/basket/1';
update public.clubs set site = 'https://www.caensudbasket.fr/' where site = 'http://caensudbasket.fr/';
update public.clubs set site = 'https://shuc-centreequestrecaen.fr/' where site = 'http://shuc-centreequestrecaen.fr/';
update public.clubs set site = 'https://www.escalade-mea.com/' where site = 'http://www.escalade-mea.com/';
update public.clubs set site = 'https://www.agcaen.com/sport/tennis_de_table/8' where site = 'http://www.agcaen.com/sport/tennis_de_table/8';
