import pandas as pd
import logging
from datetime import datetime
from flask import session
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

# ==============================
# Configuration Google Sheets
# ==============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("facultairecashwebapp-5b853b8f0832.json", scopes=SCOPES)
client = gspread.authorize(creds)

# L’ID du Google Sheet (mettre dans Config si tu veux centraliser)
GOOGLE_SHEET_ID = "T1zmemDQexKAiaVCJkv_TttssWAr7nQOtHX57clnbXP_Q"

# Mapping des fichiers Excel -> noms des onglets Google Sheets
SHEETS_MAP = {
    "caisse": "Caisse",
    "classes": "Classes",
    "paiements": "Paiements",
    "depenses": "Depenses",
    "cours": "Cours",
    "comments": "Commentaires",
    "depenses_travaux": "DepensesTravaux",
    "categories_paiement": "CategoriesPaiement",
    "categories_depense": "CategoriesDepense",
    "autres_recettes": "AutresRecettes",
    "recettes": "Recettes"
}

# ==============================
# Fonctions utilitaires
# ==============================
def lire_sheet(sheet_name):
    """Lit une feuille Google Sheets et retourne un DataFrame."""
    try:
        worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Erreur lecture sheet {sheet_name}: {e}")
        return pd.DataFrame()

def sauvegarder_sheet(df, sheet_name):
    """Écrase une feuille Google Sheets avec le contenu du DataFrame."""
    try:
        worksheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(sheet_name)
        worksheet.clear()
        if not df.empty:
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        logging.error(f"Erreur sauvegarde sheet {sheet_name}: {e}")

def ajouter_ligne(sheet_name, data, colonnes):
    """Ajoute une ligne à une feuille Google Sheets."""
    df = lire_sheet(sheet_name)
    for col in colonnes:
        if col not in data:
            data[col] = None
    df = pd.concat([df, pd.DataFrame([{col: data.get(col) for col in colonnes}])], ignore_index=True)
    sauvegarder_sheet(df, sheet_name)

# ==============================
# Caisse
# ==============================
COLONNES_CAISSE = ["Date", "Nom", "Type", "Montant", "Description", "utilisateur", "date_heure"]

def lire_caisse():
    df = lire_sheet(SHEETS_MAP["caisse"])
    for col in COLONNES_CAISSE:
        if col not in df.columns:
            df[col] = np.nan
    return df[COLONNES_CAISSE]

def enregistrer_operation(data):
    if float(data.get("Montant", 0)) < 0:
        raise ValueError("Le montant doit être positif")
    data["utilisateur"] = session.get("user", "inconnu")
    data["date_heure"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ajouter_ligne(SHEETS_MAP["caisse"], data, COLONNES_CAISSE)

# ==============================
# Classes & Étudiants
# ==============================
def lire_classes():
    return lire_sheet(SHEETS_MAP["classes"])

def enregistrer_classe_etudiants(nom_classe, liste_etudiants):
    df = lire_classes()
    nouvelles = pd.DataFrame({"NomClasse": [nom_classe]*len(liste_etudiants), "Etudiant": liste_etudiants})
    df = pd.concat([df, nouvelles], ignore_index=True)
    sauvegarder_sheet(df, SHEETS_MAP["classes"])

# ==============================
# Paiements
# ==============================
def lire_paiements():
    return lire_sheet(SHEETS_MAP["paiements"])

def enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement):
    if montant < 0:
        raise ValueError("Le montant doit être positif")
    ajouter_ligne(SHEETS_MAP["paiements"], {
        "NomClasse": nom_classe,
        "Etudiant": etudiant,
        "CategoriePaiement": categorie,
        "Montant": montant,
        "DatePaiement": date_paiement
    }, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"])

# ==============================
# Dépenses
# ==============================
def lire_depenses():
    df = lire_sheet(SHEETS_MAP["depenses"])
    colonnes = ["NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"]
    for col in colonnes:
        if col not in df.columns:
            df[col] = None
    df["Montant"] = pd.to_numeric(df["Montant"], errors="coerce").fillna(0)
    return df

def enregistrer_depense(data):
    if float(data.get("Montant", 0)) < 0:
        raise ValueError("Le montant doit être positif")
    ajouter_ligne(SHEETS_MAP["depenses"], data,
                  ["NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"])

# ==============================
# Cours
# ==============================
def lire_cours():
    return lire_sheet(SHEETS_MAP["cours"])

def enregistrer_cours(nom_classe, nom_cours):
    df = lire_cours()
    if not ((df["NomClasse"] == nom_classe) & (df["NomCours"] == nom_cours)).any():
        ajouter_ligne(SHEETS_MAP["cours"], {"NomClasse": nom_classe, "NomCours": nom_cours}, ["NomClasse", "NomCours"])

# ==============================
# Commentaires
# ==============================
def lire_comments():
    return lire_sheet(SHEETS_MAP["comments"])

def enregistrer_commentaire(nom_classe, etudiant, commentaire, auteur=None):
    df = lire_comments()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    condition = (df["NomClasse"] == nom_classe) & (df["Etudiant"] == etudiant)
    if condition.any():
        idx = df.index[condition][0]
        df.at[idx, "Commentaire"] = commentaire
        df.at[idx, "Date"] = now_str
        df.at[idx, "Auteur"] = auteur or ""
        sauvegarder_sheet(df, SHEETS_MAP["comments"])
    else:
        ajouter_ligne(SHEETS_MAP["comments"], {
            "NomClasse": nom_classe,
            "Etudiant": etudiant,
            "Commentaire": commentaire,
            "Auteur": auteur or "",
            "Date": now_str
        }, ["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"])

# ==============================
# Catégories
# ==============================
def lire_categories_paiement():
    return lire_sheet(SHEETS_MAP["categories_paiement"])

def lire_categories_depense():
    return lire_sheet(SHEETS_MAP["categories_depense"])

def ajouter_categorie_paiement(nouvelle):
    df = lire_categories_paiement()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    ajouter_ligne(SHEETS_MAP["categories_paiement"], {"Categorie": nouvelle}, ["Categorie"])

def supprimer_categorie_paiement(categorie):
    df = lire_categories_paiement()
    df = df[df["Categorie"] != categorie]
    sauvegarder_sheet(df, SHEETS_MAP["categories_paiement"])

def modifier_categorie_paiement(ancienne, nouvelle):
    df = lire_categories_paiement()
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    sauvegarder_sheet(df, SHEETS_MAP["categories_paiement"])

def ajouter_categorie_depense(nouvelle):
    df = lire_categories_depense()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    ajouter_ligne(SHEETS_MAP["categories_depense"], {"Categorie": nouvelle}, ["Categorie"])

def supprimer_categorie_depense(categorie):
    df = lire_categories_depense()
    df = df[df["Categorie"] != categorie]
    sauvegarder_sheet(df, SHEETS_MAP["categories_depense"])

def modifier_categorie_depense(ancienne, nouvelle):
    df = lire_categories_depense()
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    sauvegarder_sheet(df, SHEETS_MAP["categories_depense"])
