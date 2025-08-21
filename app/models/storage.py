import os
import pandas as pd
from datetime import datetime
from ..config import Config
import logging
from flask import session
import numpy as np

# === Dossier principal des données ===
DATA_FOLDER = Config.DATA_FOLDER
os.makedirs(DATA_FOLDER, exist_ok=True)

# === Fichiers Excel ===
FICHIER_CAISSE = os.path.join(DATA_FOLDER, "caisse.xlsx")
CLASSES_FILE = os.path.join(DATA_FOLDER, "classes.xlsx")
PAIEMENTS_FILE = os.path.join(DATA_FOLDER, "paiements.xlsx")
DEPENSES_FILE = os.path.join(DATA_FOLDER, "depenses.xlsx")
COURS_FILE = os.path.join(DATA_FOLDER, "cours_par_classe.xlsx")
COMMENTS_FILE = os.path.join(DATA_FOLDER, "comments.xlsx")
TRAVAUX_DEPENSES_FILE = os.path.join(DATA_FOLDER, "depenses_travaux.xlsx")
CATEGORIES_PAIEMENT_FILE = os.path.join(DATA_FOLDER, "categories_paiement.xlsx")
CATEGORIES_DEPENSE_FILE = os.path.join(DATA_FOLDER, "categories_depense.xlsx")
AUTRES_RECETTES_FILE = os.path.join(DATA_FOLDER, "autres_recettes.xlsx")
RECETTES_FILE = os.path.join(DATA_FOLDER, "recettes.xlsx")


# === Helpers ===
def _ensure_file(path, columns):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_excel(path, index=False)


def ajouter_ligne(path, data, colonnes):
    df = lire_excel(path)
    for col in colonnes:
        if col not in data:
            data[col] = None
    df = pd.concat([df, pd.DataFrame([{col: data.get(col) for col in colonnes}])], ignore_index=True)
    df.to_excel(path, index=False)


def lire_excel(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_excel(path)
    except Exception as e:
        logging.error(f"Erreur lecture fichier {path}: {e}")
        return pd.DataFrame()


# === Initialisation ===
def init_all_files():
    _ensure_file(FICHIER_CAISSE, ["Date", "Nom", "Type", "Montant", "Description"])
    _ensure_file(CLASSES_FILE, ["NomClasse", "Etudiant"])
    _ensure_file(PAIEMENTS_FILE, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"])
    _ensure_file(DEPENSES_FILE, ["NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"])
    _ensure_file(COURS_FILE, ["NomClasse", "NomCours"])
    _ensure_file(COMMENTS_FILE, ["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"])
    _ensure_file(TRAVAUX_DEPENSES_FILE, ["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "Montant", "DateDepense"])
    _ensure_file(CATEGORIES_PAIEMENT_FILE, ["Categorie"])
    _ensure_file(CATEGORIES_DEPENSE_FILE, ["Categorie"])
    _ensure_file(AUTRES_RECETTES_FILE, ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Description", "utilisateur"])
    _ensure_file(RECETTES_FILE, ["Date", "Source", "Type", "Description", "Montant"])


# === Caisse ===
COLONNES_CAISSE = ["Date", "Nom", "Type", "Montant", "Description", "utilisateur", "date_heure"]

def lire_caisse():
    df = lire_excel(FICHIER_CAISSE)
    for col in COLONNES_CAISSE:
        if col not in df.columns:
            df[col] = np.nan
    return df[COLONNES_CAISSE]

def enregistrer_operation(data):
    if float(data.get("Montant", 0)) < 0:
        raise ValueError("Le montant doit être positif")
    data["utilisateur"] = session.get("user", "inconnu")
    data["date_heure"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ajouter_ligne(FICHIER_CAISSE, data, COLONNES_CAISSE)


# === Classes & Étudiants ===
def lire_classes():
    return lire_excel(CLASSES_FILE)

def enregistrer_classe_etudiants(nom_classe, liste_etudiants):
    df = lire_classes()
    nouvelles = pd.DataFrame({"NomClasse": [nom_classe]*len(liste_etudiants), "Etudiant": liste_etudiants})
    df = pd.concat([df, nouvelles], ignore_index=True)
    df.to_excel(CLASSES_FILE, index=False)


# === Paiements ===
def lire_paiements():
    return lire_excel(PAIEMENTS_FILE)

def enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement):
    if montant < 0:
        raise ValueError("Le montant doit être positif")
    ajouter_ligne(PAIEMENTS_FILE, {
        "NomClasse": nom_classe,
        "Etudiant": etudiant,
        "CategoriePaiement": categorie,
        "Montant": montant,
        "DatePaiement": date_paiement
    }, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"])


# === Dépenses ===
def lire_depenses():
    df = lire_excel(DEPENSES_FILE)
    colonnes = ["NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"]
    for col in colonnes:
        if col not in df.columns:
            df[col] = None
    df["Montant"] = pd.to_numeric(df["Montant"], errors="coerce").fillna(0)
    return df

def enregistrer_depense(data):
    if float(data.get("Montant", 0)) < 0:
        raise ValueError("Le montant doit être positif")
    ajouter_ligne(DEPENSES_FILE, data, ["NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"])


# === Cours ===
def lire_cours():
    return lire_excel(COURS_FILE)

def enregistrer_cours(nom_classe, nom_cours):
    df = lire_cours()
    if not ((df["NomClasse"] == nom_classe) & (df["NomCours"] == nom_cours)).any():
        ajouter_ligne(COURS_FILE, {"NomClasse": nom_classe, "NomCours": nom_cours}, ["NomClasse", "NomCours"])


# === Commentaires ===
def lire_comments():
    return lire_excel(COMMENTS_FILE)

def enregistrer_commentaire(nom_classe, etudiant, commentaire, auteur=None):
    df = lire_comments()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    condition = (df["NomClasse"] == nom_classe) & (df["Etudiant"] == etudiant)
    if condition.any():
        idx = df.index[condition][0]
        df.at[idx, "Commentaire"] = commentaire
        df.at[idx, "Date"] = now_str
        df.at[idx, "Auteur"] = auteur or ""
    else:
        ajouter_ligne(COMMENTS_FILE, {
            "NomClasse": nom_classe,
            "Etudiant": etudiant,
            "Commentaire": commentaire,
            "Auteur": auteur or "",
            "Date": now_str
        }, ["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"])


# === Recettes ===
def lire_autres_recettes():
    df = lire_excel(AUTRES_RECETTES_FILE)
    colonnes = ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Description", "utilisateur"]
    for col in colonnes:
        if col not in df.columns:
            df[col] = None
    df["Montant"] = pd.to_numeric(df.get("Montant", pd.Series()), errors="coerce").fillna(0)
    return df

def enregistrer_autre_recette(nom_classe, etudiant, categorie_paiement, montant, description, date, utilisateur):
    if montant < 0:
        raise ValueError("Le montant doit être positif")
    ajouter_ligne(AUTRES_RECETTES_FILE, {
        "Date": date,
        "NomClasse": nom_classe,
        "Etudiant": etudiant,
        "CategoriePaiement": categorie_paiement,
        "Montant": montant,
        "Description": description,
        "utilisateur": utilisateur
    }, ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Description", "utilisateur"])

def lire_recettes():
    """
    Lit toutes les recettes à afficher dans la liste,
    en combinant RECETTES_FILE et AUTRES_RECETTES_FILE.
    Renvoie un DataFrame avec colonnes : Date, Type, Description, Montant, Source, Utilisateur
    """
    # Recettes existantes
    df1 = lire_excel(RECETTES_FILE)
    for col in ["Date", "Source", "Type", "Description", "Montant"]:
        if col not in df1.columns:
            df1[col] = None
    df1["Utilisateur"] = df1.get("Utilisateur", "")

    # Autres recettes
    df2 = lire_autres_recettes()
    if not df2.empty:
        df2_display = pd.DataFrame()
        df2_display["Date"] = df2["Date"]
        df2_display["Type"] = df2["CategoriePaiement"].fillna("manuelle")
        df2_display["Description"] = df2["Description"]
        df2_display["Montant"] = df2["Montant"]
        df2_display["Source"] = df2["NomClasse"] + (" - " + df2["Etudiant"].fillna("") if "Etudiant" in df2.columns else "")
        df2_display["Utilisateur"] = df2["utilisateur"].fillna("")
    else:
        df2_display = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Source", "Utilisateur"])

    df_final = pd.concat([df1[["Date", "Type", "Description", "Montant", "Source", "Utilisateur"]], 
                          df2_display], ignore_index=True)
    return df_final


# === Dépenses Travaux ===
def lire_depenses_travaux():
    df = lire_excel(TRAVAUX_DEPENSES_FILE)
    colonnes = ["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "Montant", "DateDepense"]
    for col in colonnes:
        if col not in df.columns:
            df[col] = None
    df["Montant"] = pd.to_numeric(df.get("Montant", pd.Series()), errors="coerce").fillna(0)
    return df

def enregistrer_depense_travail(data):
    if float(data.get("Montant", 0)) < 0:
        raise ValueError("Le montant doit être positif")
    ajouter_ligne(TRAVAUX_DEPENSES_FILE, data, ["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "Montant", "DateDepense"])


# === Catégories Paiement & Dépense ===
def lire_categories_paiement():
    return lire_excel(CATEGORIES_PAIEMENT_FILE)

def lire_categories_depense():
    return lire_excel(CATEGORIES_DEPENSE_FILE)

def ajouter_categorie_paiement(nouvelle):
    df = lire_categories_paiement()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    ajouter_ligne(CATEGORIES_PAIEMENT_FILE, {"Categorie": nouvelle}, ["Categorie"])

def supprimer_categorie_paiement(categorie):
    df = lire_categories_paiement()
    df = df[df["Categorie"] != categorie]
    df.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)

def modifier_categorie_paiement(ancienne, nouvelle):
    df = lire_categories_paiement()
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    df.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)

def ajouter_categorie_depense(nouvelle):
    df = lire_categories_depense()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    ajouter_ligne(CATEGORIES_DEPENSE_FILE, {"Categorie": nouvelle}, ["Categorie"])

def supprimer_categorie_depense(categorie):
    df = lire_categories_depense()
    df = df[df["Categorie"] != categorie]
    df.to_excel(CATEGORIES_DEPENSE_FILE, index=False)

def modifier_categorie_depense(ancienne, nouvelle):
    df = lire_categories_depense()
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    df.to_excel(CATEGORIES_DEPENSE_FILE, index=False)
