"""Import du livret « Sport et handicap en Savoie 2025-2026 » (CDOS de la Savoie) dans la table clubs.

Le livret présente les clubs labellisés « Pour un sport ensemble » par discipline : nom du club, commune de
pratique, référent (nom, téléphone, mail), site, puis 5 pictogrammes (psychique, mental, moteur, visuel,
auditif) : foncé = handicap accueilli, grisé = non. Le livret ne fait que 4 pages de clubs et la couleur des
pictogrammes ne se lit pas de façon fiable dans le fichier : le tableau LIVRET ci-dessous est recopié du livret,
page par page (lettres P M Mo V A = pictogrammes foncés).

Ne sont pas importés : les 3 clubs « en cours de labellisation » (pas encore labellisés) et les 2 comités
départementaux (ce ne sont pas des clubs). Le nom des référents n'est pas repris, ni une adresse mail qui
contient leur nom. Le livret ne donne que la commune : le code postal est remplacé par le numéro du département (73).

Utilisation : python import_savoie.py > 11_import_savoie.sql
"""
from csv_vers_sql import normaliser_sports, requete
from import_eure import mail_du_club

SOURCE = "Livret Sport et handicap en Savoie 2025-2026, CDOS de la Savoie"
H = {"P": "psychique", "M": "mental", "Mo": "moteur", "V": "visuel", "A": "auditif"}

# nom | commune | sports | pictogrammes foncés | référent (sert seulement à écarter son mail) | téléphone | mail | site
LIVRET = """
Entente Aviron Aix-les-Bains | Aix-les-Bains | aviron | P M Mo V A | Christian Paressant | 07 78 24 97 15 | christian.paressant@gmail.com | https://avironaix.fr/
Badminton Club de Chambéry | Chambéry | badminton | M Mo | Laurent Valliere | 06 24 45 66 65 | president@bcc73.com | https://www.bcc73.com
Grand Chambéry Basket Savoie Mont Blanc | Chambéry | basket | P M | Zakaria Miloudi | 06 03 19 67 55 | contact@grandchamberybasket.fr | https://www.grandchamberybasket.fr
Montmélian Savoie BMX | Montmélian | bmx | P M | Dominique Leiser | 06 66 14 71 70 | entraineurs@montmelian-savoie-bmx.com | https://montmelian-savoie-bmx.com
Chambéry Le Bourget Canoë-Kayak | Le Bourget-du-Lac | canoë-kayak | P M Mo V | Agnès Daille | 06 81 12 34 51 | agnes.daille@wanadoo.fr | https://www.clbck.fr
Sportdif' | Le Montcel | cyclisme | Mo V | Katia Belien | 06 66 73 09 76 | katia.belien@wanadoo.fr | https://sportdif.webself.net/accueil
Le Pied à l'Etrier | Saint-Julien-Montdenis | équitation | P M Mo V A | Ludivine Escoffier | 06 61 19 74 86 | piedetrier73@gmail.com | https://piedetrier.ffe.com
Centre équestre d'Aix-les-Bains | Aix-les-Bains | équitation | P M Mo V A | Clémentine Costes | 07 68 12 91 26 | costes.clementine@hotmail.fr | http://ce-aix-les-bains.wix.com/ce-aix-les-bains
Club Alpin Français de Chambéry | Chambéry | escalade, montagne | P M Mo V A | Téofil Adamski | 07 68 09 59 23 | handicaf@cafchambery.com | https://www.cafchambery.com
Roc et Vertige | Grésy-sur-Aix | escalade | P M Mo V A | Jean-Jacques Marin | 07 81 82 31 30 | rocetvertige@gmail.com | https://www.rocetvertige.net
Cercle d'escrime de Chambéry | Chambéry | escrime | P M Mo A | Laurence Bachetta | 06 87 68 50 37 | laurence.bachetta@orange.fr | http://chambery.escrime.free.fr
Aix Football Club | Aix-les-Bains | football | M Mo | Franck Palumbo | 06 70 26 11 46 | aixfootballclub@gmail.com | https://aix-football-club.footeo.com
Football Club Sud Lac | Voglans | football | P M | Pietro Costanza | 06 16 63 13 44 | fc.sudlac.sa@gmail.com | https://fcsudlac.footeo.com/
US La Ravoire Football | La Ravoire | football | M | Matthis Lussiez | 07 82 29 31 67 | lussiezmatthis@gmail.com | https://union-sportive-la-ravoire.footeo.com/
Union Sportive Motteraine | La Motte-Servolex | football | P M | Jerome Roussilon | 06 67 27 02 49 | j.collombroussillon@gmail.com | https://www.facebook.com/usmfootball
Club des Sports de la Gendarmerie de Savoie | Bassens | gymnastique | P M Mo V A | Bernardette Frison | 06 79 84 27 20 | galopine73@gmail.com | https://csgs-galopins.e-monsite.com/
Union Gymnique d'Aix-les-Bains | Aix-les-Bains | gymnastique | M Mo V | Karine Colombier | 06 81 11 76 48 | kcolombier@wanadoo.fr | https://www.ugaix.com
Gymnastique Volontaire d'Aix-les-Bains | Aix-les-Bains | gymnastique | P M | Anne Lefay | 06 09 93 19 21 | anne.lefay@gvaixlesbains.fr | https://gvaaixlesbains.fr
Judo Club d'Aix-les-Bains | Aix-les-Bains | judo | P M Mo V | Françoise Bedoc | 06 72 08 73 81 | bedoc.francoise@orange.fr | https://judoclubaixois1.wixsite.com/judoclubaixois
Albertville Handisport | Albertville | natation, basket fauteuil, cyclisme | M Mo V A | Isabelle Pinto | 06 78 23 92 40 | albertville73.handisport@gmail.com | https://www.facebook.com/albertvillehandisport/
Association des Sourds de Cognin | Cognin | football, cyclisme, natation, randonnée, ski alpin, volley-ball, pétanque | A | Jean-Paul Girard | 06 85 14 73 74 | ascognin@gmail.com | https://www.facebook.com/ascognin/
Association Sport et Handicap de Maurienne | Saint-Jean-de-Maurienne | natation, pétanque, ski alpin, ski nordique, raquettes, randonnée, sport boule | P M | Laurence Diernaz | 06 95 13 09 09 | ashm73@outlook.fr |
Club Handisport de l'Agglomération Chambérienne | Chambéry | tir à l'arc, basket fauteuil, tennis de table | Mo V A | Delphine Balzaretti | 06 58 55 76 78 | chachandi73@gmail.com | https://www.instagram.com/basket_fauteuil-chambery/
Elan Chambérien | Chambéry | tennis de table, natation, activités de neige, pétanque, randonnée, danse, gymnastique | P M | Romain Rivalland | 07 83 34 95 91 | educ.elan@gmail.com |
Handisport Club du Bassin Aixois | Aix-les-Bains | randonnée, natation, cyclisme, escalade, sports de boules | P M Mo V A | Jean-Henri Bouillon | 06 66 51 35 78 | handi.club.aix@gmail.com | https://handisportclubbassinaixois.org/
Maison Savoyarde des Sourds | Chambéry | sports de boules | A | Richard Biniek | 06 24 49 19 36 | mss73.1965@gmail.com |
Les Jeunes Chamois | | foot fauteuil électrique, boccia, sarbacane, cyclisme | Mo V A | Jean Thomas | 06 45 94 01 94 | lesjeuneschamois73@gmail.com | https://www.facebook.com/lesjeuneschamois73/
Stade Olympique Chambéry Natation | Chambéry | natation | P M | Marie-José Cadoux | 06 33 61 54 58 | soc.natation73@gmail.com | https://www.socnatation.com
Cercle des nageurs Aix-les-Bains Riviera | Aix-les-Bains | natation | P M Mo | Fabrice Marion | 07 66 28 69 49 | fab9marion@hotmail.fr | https://cn-aixlesbains-riviera.fr/
Rugby Club Motterain | La Motte-Servolex | rugby | P M | Maud Mrugacz Christelle Duvinage | 06 14 48 08 90 / 06 83 17 05 54 | m_mrugacz@yahoo.fr | https://rcm.ffr.fr
Football Club d'Aix-les-Bains Rugby | Aix-les-Bains | rugby | P M | Arthur Cabaret | 06 05 01 06 92 | fca.arthurcabaret@gmail.com | https://www.fcaixlesbainsrugby.fr/
Grand Chambéry Ski | Les Aillons | ski alpin | M Mo V A | Jean Léon Perrier | 06 14 31 10 03 | jean-leon.perrier@orange.fr | https://www.grandchamberyski.fr/
Club de Ski Nordique La Féclaz | La Féclaz | ski nordique | P M Mo V A | Bernard Jaillet Christophe Planet | 06 74 55 29 83 / 06 21 59 10 83 | bjailletech@orange.fr | https://www.skinordiquelafeclaz.org
Tennis Club du Nivolet | Bassens | tennis | P M | Pierre-Edouard Mietton | 06 03 49 39 45 | pierreed1@hotmail.com | https://www.facebook.com/TennisClubduNivolet
Tennis Olympique Albertville | Albertville | tennis | P M Mo | Maxime Caron | 06 12 20 00 57 | maximecaron73@orange.fr | https://www.tennis-albertville.fr
Tennis Club La Ravoire | La Ravoire | tennis | P M Mo A | Olivier Varaud | 06 11 75 30 58 | tclaravoire@fft.fr | https://tclaravoire.com/
Albertville Tennis de Table | Albertville | tennis de table | P M Mo A | Daniel Maupuy | 06 81 60 27 20 | danielmaupuy@sfr.fr | https://tt-albertville.fr/
1ère compagnie de tir à l'arc d'Aix-les-Bains | Aix-les-Bains | tir à l'arc | Mo | Jean-Daniel Chalot | 06 11 78 52 04 | jdchalot@orange.fr | http://aixtiralarc.net
Les Archers du Roc Noir | Challes-les-Eaux | tir à l'arc | P M Mo | Muriel Lherminier | 06 18 17 06 84 | arcrocnoir73@gmail.com | https://www.arcrocnoir.onlc.fr
Club Nautique Voile d'Aix les Bains | Aix-les-Bains | voile | P M Mo V A | Alexis Littoz | 04 79 34 10 74 | directeur@cnva.com | https://www.cnva.com
Yacht Club Chambéry Le Bourget du Lac | Le Bourget-du-Lac | voile | P M Mo V A | Maud Archer | 04 79 25 21 66 | info@ycbl.fr | https://www.ycbl.fr
"""


def fiches():
    for ligne in LIVRET.strip().splitlines():
        nom, ville, sports, pictos, referent, tel, mail, site = [c.strip() for c in ligne.split("|")]
        h = [H[p] for p in ("Mo", "V", "A", "M", "P") if p in pictos.split()]
        physique = any(x in h for x in ("moteur", "visuel", "auditif"))
        adapte = any(x in h for x in ("mental", "psychique"))
        yield {
            "sport": ", ".join(normaliser_sports(sports)), "nom": nom, "code_postal": "73", "ville": ville,
            "handicaps": ", ".join(h),
            "pratique": "les deux" if physique and adapte else "sport adapte" if adapte else "handisport" if physique else "",
            "telephone": tel, "email": mail_du_club(mail, nom, referent), "site": site,
            "label": "Label « Pour un sport ensemble » (Savoie)", "source": SOURCE,
        }


if __name__ == "__main__":
    print(requete(list(fiches()), SOURCE), end="")
