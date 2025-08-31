import gspread
import pandas as pd
import logging
import datetime
import time
import random
from threading import Lock
from gspread.exceptions import APIError

# ============================
# CONFIGURATION GOOGLE SHEETS
# ============================

CREDENTIALS_FILE = 'facultairecashwebapp-5b853b8f0832.json'
SPREADSHEET_NAME = 'ULGLP_Caisse'

gc = gspread.service_account(filename=CREDENTIALS_FILE)
try:
    sh = gc.open(SPREADSHEET_NAME)
except gspread.SpreadsheetNotFound:
    sh = gc.create(SPREADSHEET_NAME)
    sh.share('', perm_type='anyone', role='reader')

# ============================
# FEUILLES REQUISES ET COLONNES
# ============================

REQUIRED_SHEETS = {
    "etudiants": ["ID", "Nom", "Prenom", "Classe"],
    "Classes": ["NomClasse", "Etudiant"],
    "Paiements": ["ID", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"],
    "Depenses": ["ID", "NomCours", "CategorieDepense", "Description", "Montant", "NomClasse",  "TypeDepense", "Commentaire", "DateDepense", "Utilisateur"],
    "Depenses_travaux": ["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "DateDepense"],
    "audit": ["Date", "Utilisateur", "Action", "Table", "Detail"],
    "parametres": ["NomParam", "Valeur"],
    "Caisse": ["Date", "Nom", "Type", "Montant", "Description"],
    "Cours": ["NomClasse", "NomCours"],
    "CategoriesDepense": ["Categorie"],
    "CategoriesPaiement": ["Categorie"],
    "Commententaires": ["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"],
    "cours_par_classe": ["NomClasse", "NomCours"],
    "Recettes": ["Date", "Source", "Type", "Description", "Montant", "NomClasse", "Etudiant", "Utilisateur"],
    "Autres_recettes": ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Description", "Utilisateur"],
    "users": ["username", "password_hash", "role"]
}

# ============================
# INIT FLAG ET LOCK
# ============================

_init_done = False
_init_lock = Lock()

# ============================
# UTILITAIRES QUOTA API
# ============================

def safe_call(func, *args, **kwargs):
    """Appel sécurisé avec retry en cas de quota dépassé (429)."""
    for attempt in range(5):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            if "429" in str(e):
                wait = (2 ** attempt) + random.random()
                logging.warning(f"⏳ Quota dépassé, retry dans {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Échec après plusieurs tentatives à cause du quota Sheets API.")

# ============================
# INITIALISATION DES FEUILLES
# ============================

def init_all_files():
    global _init_done
    with _init_lock:
        if _init_done:
            logging.info("ℹ️ Les feuilles sont déjà initialisées, on saute l'init.")
            return
        try:
            existing_ws = {ws.title.strip().lower(): ws for ws in safe_call(sh.worksheets)}
            for sheet_name, cols in REQUIRED_SHEETS.items():
                sheet_name_clean = sheet_name.strip()
                sheet_name_lower = sheet_name_clean.lower()
                if sheet_name_lower in existing_ws:
                    continue
                ws = safe_call(sh.add_worksheet, title=sheet_name_clean, rows="1000", cols=str(max(len(cols), 10)))
                safe_call(ws.append_row, cols)
            _init_done = True
            logging.info("✅ Initialisation des feuilles terminée.")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation des fichiers : {e}")
            raise

# ============================
# FONCTIONS DE BASE SHEETS
# ============================

def get_sheet(sheet_name, columns=None):
    sheet_name = sheet_name.strip()
    try:
        ws = sh.worksheet(sheet_name)
        if columns and not ws.row_values(1):
            ws.insert_row(columns, index=1)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows="1000", cols=str(len(columns) if columns else 20))
        if columns:
            ws.insert_row(columns, index=1)
    return ws

def read_sheet(sheet_name):
    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

def write_sheet(sheet_name, df):
    ws = sh.worksheet(sheet_name)
    ws.clear()
    if not df.empty:
        ws.update([df.columns.tolist()] + df.values.tolist())

def ensure_ids(df, id_col="ID"):
    if id_col not in df.columns:
        df[id_col] = range(1, len(df) + 1)
    else:
        df[id_col] = [i+1 if pd.isna(v) or v=="" else int(v) for i, v in enumerate(df[id_col])]
    return df

# ============================
# CLASSES ET COURS
# ============================

def lire_classes():
    df = read_sheet("Classes")
    if df.empty:
        return pd.DataFrame(columns=["NomClasse", "Etudiant"])
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["Etudiant"] = df["Etudiant"].astype(str).str.strip()
    df = df[df["Etudiant"] != ""]
    return df

def lire_cours():
    df = read_sheet("Cours")
    if df.empty:
        return pd.DataFrame(columns=["NomClasse", "NomCours"])
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["NomCours"] = df["NomCours"].astype(str).str.strip()
    return df

# ============================
# DEPENSES
# ============================

def lire_depenses():
    df = read_sheet("Depenses")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["Depenses"])
    else:
        df = ensure_ids(df, "ID")
    return df

def lire_depenses_travaux():
    df = read_sheet("Depenses_travaux")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["Depenses_travaux"])
    df = ensure_ids(df, "ID")
    return df

def enregistrer_depense_autres(data: dict):
    ws = get_sheet("Depenses", REQUIRED_SHEETS["Depenses"])
    ligne = [
        "",  # ID
        "",  # NomCours
        "Autres",  # Catégorie
        data.get("Description", ""),
        float(data.get("Montant", 0.0)),
        "",  # NomClasse
        "Autre",  # TypeDepense
        "",  # Commentaire
        data.get("DateDepense", ""),
        "",  # Utilisateur
    ]
    ws.append_row(ligne, value_input_option="USER_ENTERED")

def enregistrer_depense_travaux(data: dict):
    ws = get_sheet("Depenses_travaux", REQUIRED_SHEETS["Depenses_travaux"])
    ligne = [
        data.get("NomClasse", ""),
        data.get("Etudiant", ""),
        data.get("CategorieTravail", ""),
        data.get("TypeDepense", ""),
        data.get("Commentaire", ""),
        data.get("DateDepense", "")
    ]
    ws.append_row(ligne, value_input_option="USER_ENTERED")

def enregistrer_depense_examen(data: dict):
    ws = get_sheet("Depenses", REQUIRED_SHEETS["Depenses"])
    ligne = [
        "",  # ID
        "",  # NomCours
        data.get("CategorieDepense", ""),
        "",  # Description
        0.0,  # Montant
        data.get("NomClasse", ""),
        data.get("TypeDepense", ""),
        data.get("Commentaire", ""),
        data.get("DateDepense", ""),
        ""  # Utilisateur
    ]
    ws.append_row(ligne, value_input_option="USER_ENTERED")

# ============================
# RECETTES / PAIEMENTS
# ============================

def lire_recettes():
    df = read_sheet("Recettes")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["Recettes"])
    df = ensure_ids(df, "ID")
    return df

def lire_autres_recettes():
    df = read_sheet("Autres_recettes")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["Autres_recettes"])
    df = ensure_ids(df, "ID")
    return df

def lire_paiements():
    df = read_sheet("Paiements")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["Paiements"])
    df = ensure_ids(df, "ID")
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["Etudiant"] = df["Etudiant"].astype(str).str.strip()
    return df

def enregistrer_autre_recette(nom_classe, etudiant, type_recette, montant, description, date, utilisateur):
    columns = REQUIRED_SHEETS["Recettes"]
    ws = get_sheet("Recettes", columns=columns)
    try:
        montant_val = float(montant)
    except (ValueError, TypeError):
        montant_val = 0.0
        logging.warning(f"⚠️ Montant invalide reçu : {montant} – remplacé par 0.0")
    ligne = [
        date,
        type_recette,
        '',  # Source/Type supplémentaire
        description,
        montant_val,
        nom_classe or '',
        etudiant or '',
        utilisateur or ''
    ]
    ws.append_row(ligne, value_input_option="USER_ENTERED")

# ============================
# CATEGORIES
# ============================

def lire_categories_depense():
    df = read_sheet("CategoriesDepense")
    if df.empty:
        df = pd.DataFrame(columns=["Categorie"])
    else:
        df.columns = df.columns.str.strip()
        if "Categorie" not in df.columns:
            df["Categorie"] = ""
    return df

def lire_categories_paiement():
    df = read_sheet("CategoriesPaiement")
    if df.empty:
        df = pd.DataFrame(columns=["Categorie"])
    else:
        df.columns = df.columns.str.strip()
        if "Categorie" not in df.columns:
            df["Categorie"] = ""
    return df

def ajouter_categorie_paiement(nouvelle):
    df = lire_categories_paiement()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle}])], ignore_index=True)
    write_sheet("CategoriesPaiement", df)

def supprimer_categorie_paiement(categorie):
    df = lire_categories_paiement()
    df = df[df["Categorie"] != categorie]
    write_sheet("CategoriesPaiement", df)

def modifier_categorie_paiement(ancienne, nouvelle):
    df = lire_categories_paiement()
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    write_sheet("CategoriesPaiement", df)

def ajouter_categorie_depense(nouvelle):
    df = lire_categories_depense()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle}])], ignore_index=True)
    write_sheet("CategoriesDepense", df)

def supprimer_categorie_depense(categorie):
    df = lire_categories_depense()
    df = df[df["Categorie"] != categorie]
    write_sheet("CategoriesDepense", df)

def modifier_categorie_depense(ancienne, nouvelle):
    df = lire_categories_depense()
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    write_sheet("CategoriesDepense", df)

# ============================
# AUDIT LOGS
# ============================

def log_action(utilisateur, action, table, detail):
    ws = get_sheet("audit", REQUIRED_SHEETS["audit"])
    ligne = [
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        utilisateur,
        action,
        table,
        detail
    ]
    ws.append_row(ligne, value_input_option="USER_ENTERED")

# ============================
# UTILISATEURS
# ============================

def lire_users():
    df = read_sheet("users")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["users"])
    return df

def ajouter_user(username, password_hash, role="user"):
    df = lire_users()
    if username in df["username"].values:
        raise ValueError("Utilisateur déjà existant")
    df = pd.concat([df, pd.DataFrame([{
        "username": username,
        "password_hash": password_hash,
        "role": role
    }])], ignore_index=True)
    write_sheet("users", df)

def supprimer_user(username):
    df = lire_users()
    df = df[df["username"] != username]
    write_sheet("users", df)

def modifier_user(username, password_hash=None, role=None):
    df = lire_users()
    if username not in df["username"].values:
        raise ValueError("Utilisateur introuvable")
    if password_hash:
        df.loc[df["username"] == username, "password_hash"] = password_hash
    if role:
        df.loc[df["username"] == username, "role"] = role
    write_sheet("users", df)

# ============================
# COMMENTAIRES
# ============================

def lire_commentaires():
    df = read_sheet("Commententaires")
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_SHEETS["Commententaires"])
    return df

def ajouter_commentaire(nom_classe, etudiant, commentaire, auteur):
    ws = get_sheet("Commententaires", REQUIRED_SHEETS["Commententaires"])
    ligne = [
        nom_classe,
        etudiant,
        str(commentaire),
        auteur,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    ws.append_row(ligne, value_input_option="USER_ENTERED")

# ============================
# INITIALISATION AUTOMATIQUE AU DEMARRAGE
# ============================

try:
    init_all_files()
except Exception as e:
    logging.error(f"Erreur lors de l'initialisation des fichiers : {e}")
