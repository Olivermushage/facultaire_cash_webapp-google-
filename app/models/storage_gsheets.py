import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

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
# INITIALISATION DES FEUILLES
# ============================

REQUIRED_SHEETS = [
    "etudiants",
    "Classes",
    "Paiements",
    "Depenses",
    "Depenses_travaux",
    "audit",
    "parametres",
    "Caisse",
    "Cours",
    "CategoriesDepense",
    "CategoriesPaiement",
    "Commententaires",
    "cours_par_classe",
    "recettes",
    "Autres_recettes",
    "users",
]

def init_all_files():
    existing_sheets = [ws.title.strip().lower() for ws in sh.worksheets()]
    for sheet_name in REQUIRED_SHEETS:
        sheet_name_clean = sheet_name.strip()
        if sheet_name_clean.lower() not in existing_sheets:
            try:
                print(f"✅ Création de la feuille '{sheet_name_clean}'")
                sh.add_worksheet(title=sheet_name_clean, rows="1000", cols="20")
            except Exception as e:
                print(f"⚠️ Impossible de créer la feuille '{sheet_name_clean}': {e}")
        else:
            print(f"ℹ️ La feuille '{sheet_name_clean}' existe déjà.")

# ============================
# UTILITAIRES
# ============================
# storage_gsheet.py doit déjà être importé là où tu appelles cette fonction
import datetime

def enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement, utilisateur):
    try:
        montant = float(montant)
    except ValueError:
        raise ValueError("Le montant doit être un nombre valide")

    if montant < 0:
        raise ValueError("Le montant doit être positif")

    ws = sh.worksheet("Paiements")

    colonnes = ["ID", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"]

    header = ws.row_values(1)
    if not header:
        ws.append_row(colonnes, value_input_option="USER_ENTERED")
        header = colonnes

    all_values = ws.get_all_values()
    existing_ids = []
    for row in all_values[1:]:
        try:
            existing_ids.append(int(row[0]))
        except (ValueError, IndexError):
            continue
    next_id = max(existing_ids) + 1 if existing_ids else 1

    # Formatter le montant en chaîne avec deux décimales, pour éviter interprétation en date
    montant_str = "{:.2f}".format(montant)

    row = [
        next_id,
        nom_classe,
        etudiant,
        categorie,
        montant_str,
        date_paiement if date_paiement else datetime.date.today().isoformat()
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")



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
        df[id_col] = [
            i+1 if pd.isna(v) or v=="" else int(v)
            for i, v in enumerate(df[id_col])
        ]
    return df

# ============================
# CLASSES / COURS
# ============================

def lire_classes():
    df = read_sheet("Classes")
    if df.empty:
        return pd.DataFrame(columns=["NomClasse", "Etudiant"])

    # Nettoyage important
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["Etudiant"] = df["Etudiant"].astype(str).str.strip()

    # Supprimer les lignes sans étudiant
    df = df[df["Etudiant"] != ""]
    return df

def lire_cours():
    df = read_sheet("Cours")
    if df.empty:
        return pd.DataFrame(columns=["NomClasse", "NomCours", "DateDebut", "DateFin"])

    # Nettoyage
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["NomCours"] = df["NomCours"].astype(str).str.strip()
    return df

# ============================
# DEPENSES
# ============================

def lire_depenses():
    df = read_sheet("Depenses")
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID", "NomClasse", "NomCours", "DateExamen",
            "CategorieDepense", "Description", "Montant",
            "TypeDepense", "Commentaire", "DateDepense", "Utilisateur"
        ])
    else:
        df = ensure_ids(df, "ID")
    return df

def lire_depenses_travaux():
    df = read_sheet("Depenses_travaux")
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID", "NomClasse", "NomCours", "DateExamen",
            "CategorieDepense", "Description", "Montant",
            "TypeDepense", "Commentaire", "DateDepense"
        ])
    df = ensure_ids(df, "ID")
    return df

# ============================
# RECETTES / PAIEMENTS
# ============================

def lire_recettes():
    df = read_sheet("Recettes")
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID", "NomClasse", "Etudiant", "Type", "Montant",
            "Description", "Date", "Utilisateur"
        ])
    df = ensure_ids(df, "ID")
    return df

def lire_autres_recettes():
    df = read_sheet("Autres_recettes")
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID", "NomClasse", "Etudiant", "Type", "Montant",
            "Description", "Date", "Utilisateur"
        ])
    df = ensure_ids(df, "ID")
    return df

def lire_paiements():
    df = read_sheet("Paiements")
    if df.empty:
        df = pd.DataFrame(columns=[
            "ID", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Date"
        ])
    df = ensure_ids(df, "ID")

    # Nettoyage
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["Etudiant"] = df["Etudiant"].astype(str).str.strip()
    return df

# ============================
# CATEGORIES
# ============================

def lire_categories_depense():
    df = read_sheet("CategoriesDepense")
    if df.empty:
        df = pd.DataFrame(columns=["Categorie"])
    else:
        # Nettoyer et normaliser les noms de colonnes
        df.columns = df.columns.str.strip().str.normalize('NFKD') \
                                .str.encode('ascii', errors='ignore') \
                                .str.decode('utf-8')
        # Renommer toute colonne qui ressemble à "Categorie" ou "Catégorie"
        for col in df.columns:
            if col.lower() in ["categorie", "catégorie"]:
                df.rename(columns={col: "Categorie"}, inplace=True)
                break
        # S'assurer que la colonne existe
        if "Categorie" not in df.columns:
            df["Categorie"] = ""
    return df


def lire_categories_paiement():
    df = read_sheet("CategoriesPaiement")
    if df.empty:
        df = pd.DataFrame(columns=["Categorie"])
    else:
        df.columns = df.columns.str.strip().str.normalize('NFKD') \
                                .str.encode('ascii', errors='ignore') \
                                .str.decode('utf-8')
        for col in df.columns:
            if col.lower() in ["categorie", "catégorie"]:
                df.rename(columns={col: "Categorie"}, inplace=True)
                break
        if "Categorie" not in df.columns:
            df["Categorie"] = ""
    return df


# ============================
# UTILISATEURS
# ============================

def lire_users():
    df = read_sheet("users")
    if df.empty:
        df = pd.DataFrame(columns=["username", "password", "role"])
    return df

def ajouter_user(user_data):
    df = lire_users()
    df = pd.concat([df, pd.DataFrame([user_data])], ignore_index=True)
    write_sheet("users", df)

def create_admin_default():
    df = lire_users()
    if df.empty or not any(df['username'] == 'admin'):
        ajouter_user({'username':'admin','password':'admin','role':'admin'})

# ============================
# CATEGORIES
# ============================

def lire_categories_depense():
    df = read_sheet("CategoriesDepense")
    if df.empty:
        df = pd.DataFrame(columns=["Categorie"])
    else:
        # Nettoyer et normaliser les noms de colonnes
        df.columns = df.columns.str.strip().str.normalize('NFKD') \
                                .str.encode('ascii', errors='ignore') \
                                .str.decode('utf-8')
        # Renommer toute colonne qui ressemble à "Categorie" ou "Catégorie"
        for col in df.columns:
            if col.lower() in ["categorie", "catégorie"]:
                df.rename(columns={col: "Categorie"}, inplace=True)
                break
        if "Categorie" not in df.columns:
            df["Categorie"] = ""
    return df


def lire_categories_paiement():
    df = read_sheet("CategoriesPaiement")
    if df.empty:
        df = pd.DataFrame(columns=["Categorie"])
    else:
        df.columns = df.columns.str.strip().str.normalize('NFKD') \
                                .str.encode('ascii', errors='ignore') \
                                .str.decode('utf-8')
        for col in df.columns:
            if col.lower() in ["categorie", "catégorie"]:
                df.rename(columns={col: "Categorie"}, inplace=True)
                break
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


def enregistrer_classe_etudiants(nom_classe, etudiants):
    """
    Ajoute ou met à jour les étudiants d'une classe donnée dans la feuille 'Classes'.
    Chaque étudiant est stocké sur une ligne avec son NomClasse associé.
    """
    df = lire_classes()

    # Supprimer les anciens étudiants de cette classe
    df = df[df["NomClasse"] != nom_classe]

    # Ajouter les nouveaux étudiants
    nouvelles_lignes = pd.DataFrame({
        "NomClasse": [nom_classe] * len(etudiants),
        "Etudiant": etudiants
    })

    df = pd.concat([df, nouvelles_lignes], ignore_index=True)

    # Sauvegarder dans la feuille
    write_sheet("Classes", df)
    return df
