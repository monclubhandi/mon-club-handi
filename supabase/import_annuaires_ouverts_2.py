"""Lot 2 : clubs repérés dans d'autres annuaires d'associations publiés en données ouvertes par des villes.

Sources (fiches lues une par une ; chaque association y décrit elle-même son activité) :
  - Ville de Lorient, « Annuaire local des associations » (opendata56.fr), Licence Ouverte 2.0, fiches mises à jour en 2026
  - Ville de Meudon, « Annuaire des associations - détails par activités » (data.meudon.fr), Licence Ouverte, 2026
  - Ville d'Issy-les-Moulineaux, « Associations sportives d'Issy-les-Moulineaux » (data.issy.com), Licence Ouverte, 2024

Ne sont retenues que les associations dont le texte dit proposer une pratique pour les personnes en situation de handicap.
À Issy, la case « sport handicap » cochée sans aucune description n'a pas suffi. Liens de site qui ne répondaient plus (vérifiés le 24/10/2026) non repris. Lieux de pratique repris quand
l'association les donne ; ni adresse de siège, ni nom de responsable, ni mail personnel.

Utilisation : python import_annuaires_ouverts_2.py > 16_import_annuaires_ouverts_2.sql
"""
from csv_vers_sql import requete

LORIENT = "Ville de Lorient, annuaire des associations (Licence Ouverte 2.0)"
MEUDON = "Ville de Meudon, annuaire des associations (Licence Ouverte)"
ISSY = "Ville d'Issy-les-Moulineaux, associations sportives (Licence Ouverte)"

CLUBS = [
    {"nom": "Association Lorient Handisport", "sport": "multisport", "code_postal": "56100", "ville": "Lorient",
     "handicaps": "moteur", "pratique": "handisport",
     "accessibilite": "Disciplines de la Fédération française handisport, personnes à mobilité réduite et valides ensemble. Lieu de pratique : gymnase de Kerolay, rue Moïse Le Bihan",
     "telephone": "06 60 91 30 74", "email": "lorienthandisport@gmail.com", "source": LORIENT},
    {"nom": "Association Sportive des Coureurs de l'Ouest en Fauteuil (ASCOF)", "sport": "athlétisme", "code_postal": "56100",
     "ville": "Lorient", "handicaps": "moteur", "pratique": "handisport", "accessibilite": "Course en fauteuil",
     "telephone": "06 61 34 05 42", "email": "contact@ascof.fr", "source": LORIENT},
    {"nom": "Athlétisme Pays de l'Orient", "sport": "athlétisme", "code_postal": "56100", "ville": "Lorient",
     "pratique": "handisport",
     "accessibilite": "Le club accueille les personnes en situation de handicap. Lieu de pratique : stade du Bois du Château",
     "telephone": "02 97 21 73 21", "email": "athlepaysdelorient@orange.fr", "site": "http://athlepaysdelorient.athle.org", "source": LORIENT},
    {"nom": "FAST – French Adaptive Surfer Tank", "sport": "surf", "code_postal": "56100", "ville": "Lorient",
     "accessibilite": "Surf pour les personnes en situation de handicap : initiation, matériel adapté, compétitions",
     "telephone": "06 30 85 13 25", "site": "https://fastsurf.fr", "source": LORIENT},
    {"nom": "Navisport Pays de Lorient", "sport": "voile", "code_postal": "56100", "ville": "Lorient",
     "accessibilite": "Voile et sports nautiques pour personnes handicapées et valides ensemble. Lieu de pratique : Lorient La Base",
     "telephone": "06 65 05 24 00", "email": "navisport56@gmail.com", "site": "https://www.navisport56.com/", "source": LORIENT},
    {"nom": "Association Sportive Meudonnaise – Handball", "sport": "handball", "adresse": "Gymnase Rabelais, 6 rue Georges Langrognet",
     "code_postal": "92190", "ville": "Meudon", "pratique": "handisport", "accessibilite": "Section handisport",
     "telephone": "01 71 10 57 77", "email": "asmeudonhandball92@gmail.com", "site": "https://www.asmeudonhandball.com/", "source": MEUDON},
    {"nom": "Entente Pongiste Isséenne", "sport": "tennis de table", "adresse": "Complexe sportif Alain Mimoun",
     "code_postal": "92130", "ville": "Issy-les-Moulineaux", "handicaps": "moteur, mental", "pratique": "les deux",
     "creneaux": "Lundi et mercredi à 20h30", "accessibilite": "Pongistes en situation de handicap physique ou intellectuel, séances encadrées",
     "telephone": "06 42 26 80 12", "site": "http://www.epiclub.com", "source": ISSY},
    {"nom": "Avia Club Athlétisme", "sport": "athlétisme", "adresse": "Halle Christiane Guillaume, 2 rue du Bateau Lavoir",
     "code_postal": "92130", "ville": "Issy-les-Moulineaux", "pratique": "handisport", "accessibilite": "Section handisport",
     "telephone": "01 46 42 53 55", "email": "aviaclub1@gmail.com", "site": "http://aviaclubathletisme.fr", "source": ISSY},
]

if __name__ == "__main__":
    print(requete(CLUBS, "annuaires d'associations ouverts (Lorient, Meudon, Issy-les-Moulineaux)"), end="")
