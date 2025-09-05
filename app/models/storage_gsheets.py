import gspread
import pandas as pd
from datetime import datetime
import logging
import random
import time
from threading import Lock
from gspread.exceptions import APIError, WorksheetNotFound
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from threading import Lock
from gspread_dataframe import get_as_dataframe

_init_lock = Lock()
_init_done = False  # Flag pour éviter les réinitialisations multiples


# CONFIGURATION GOOGLE SHEETS
CREDENTIALS_FILE = 'facultairecashwebapp-5b853b8f0832.json'
SPREADSHEET_NAME = 'ULGLP_Caisse'

# Authentification et ouverture du spreadsheet
gc = gspread.service_account(filename=CREDENTIALS_FILE)
try:
    sh = gc.open(SPREADSHEET_NAME)
except gspread.SpreadsheetNotFound:
    sh = gc.create(SPREADSHEET_NAME)
    sh.share('', perm_type='anyone', role='reader')

REQUIRED_SHEETS = {
    "Classes": ["NomClasse", "Etudiant"],
    "Paiements": ["ID", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"],
    "Paiements_Inscriptions": ["NomClasse", "Etudiant", "TypeInscription", "StatutPaiement", "Montant", "DatePaiement"],
    "Paiements_Travaux": ["NomClasse", "Etudiant", "TypeTravail", "StatutPaiement", "Montant", "DatePaiement"],
    "Depenses": ["ID", "NomCours", "CategorieDepense", "Description", "Montant", "NomClasse", 
                "TypeDepense", "Commentaire", "DateDepense", "Utilisateur"],
    "Depenses_travaux": ["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "DateDepense"],
    "Caisse": ["Date", "Nom", "Type", "Montant", "Description"],
    "Cours": ["NomClasse", "NomCours"],
    "CategoriesDepense": ["Categorie"],
    "CategoriesPaiement": ["Categorie"],
    "Recettes": ["Date", "Source", "Type", "Description", "Montant", "NomClasse", "Etudiant", "Utilisateur"],
    "Autres_recettes": ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Description", "Utilisateur"]
}

_cached_existing_ws = None
_cache_expiration = 60  # secondes
_cache_time = 0

def init_all_files():
    global _init_done, _cached_existing_ws, _cache_time
    with _init_lock:
        now = time.time()
        if _init_done:
            logging.info("ℹ️ Les feuilles sont déjà initialisées, on saute l'init.")
            return
        # Rafraîchir cache après expiration
        if not _cached_existing_ws or now - _cache_time > _cache_expiration:
            _cached_existing_ws = {ws.title.strip().lower(): ws for ws in safe_call(sh.worksheets)}
            _cache_time = now

        try:
            for sheet_name, cols in REQUIRED_SHEETS.items():
                sheet_name_clean = sheet_name.strip()
                sheet_name_lower = sheet_name_clean.lower()
                if sheet_name_lower in _cached_existing_ws:
                    continue
                ws = safe_call(sh.add_worksheet, title=sheet_name_clean, rows="1000", cols=str(max(len(cols), 10)))
                safe_call(ws.append_row, cols)
                # Mettre à jour cache local après ajout
                _cached_existing_ws[sheet_name_lower] = ws

            _init_done = True
            logging.info("✅ Initialisation des feuilles terminée.")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation des fichiers : {e}")
            raise



# Fonction utilitaire pour appel sécurisé à l'API avec retry
def safe_call(func, *args, **kwargs):
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


def get_sheet(sheet_name, columns=None):
    sheet_name = sheet_name.strip()
    try:
        ws = sh.worksheet(sheet_name)
        if columns and not ws.row_values(1):
            ws.insert_row(columns, index=1)
    except WorksheetNotFound:
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


def get_or_create_inscriptions_sheet():
    """
    Récupère ou crée la feuille 'Paiements_Inscriptions' avec colonnes initiales.
    """
    try:
        worksheet = sh.worksheet('Paiements_Inscriptions')
    except WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Paiements_Inscriptions', rows='1000', cols='10')
        headers = ['NomClasse', 'Etudiant', 'TypeInscription', 'StatutPaiement', 'Montant', 'DatePaiement']
        worksheet.append_row(headers)
    return worksheet

def lire_classes():
    """
    Lit la feuille 'Classes' du Google Sheets et retourne un DataFrame pandas.
    """
    try:
        ws = sh.worksheet('Classes')
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # Nettoyer les noms de colonnes
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"[Erreur lire_classes] {e}")
        return pd.DataFrame()


# Assurez-vous que cette variable globale sh pointe vers votre spreadsheet ouvert
# Par exemple :
# gc = gspread.service_account(filename='credentials.json')
# sh = gc.open('ULPGL_Caisse')

def read_sheet(sheet_name):
    """Lit une feuille Google Sheets et retourne un DataFrame pandas."""
    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"[Erreur read_sheet {sheet_name}] {e}")
        return pd.DataFrame()


def lire_classes():
    """Lit la feuille 'Classes'."""
    return read_sheet("Classes")


def lire_recettes():
    """Lit la feuille 'Recettes'."""
    return read_sheet("Recettes")


def lire_paiements():
    """Lit la feuille 'Paiements'."""
    return read_sheet("Paiements")


def lire_autres_recettes():
    """Lit la feuille 'Autres_recettes'."""
    return read_sheet("Autres_recettes")

def lire_depenses():
    return read_sheet('Depenses')
# Vous pouvez définir plus de fonctions similaires suivant les feuilles à lire



def update_student_payment(nom_classe, etudiant, type_inscription, montant=10.0):
    worksheet = get_or_create_inscriptions_sheet()
    records = worksheet.get_all_records()
    cell_to_update = None

    for i, row in enumerate(records, start=2):  # 1-based Excel rows, header is 1
        if (row.get("NomClasse") == nom_classe and
            row.get("Etudiant") == etudiant and
            row.get("TypeTravail") == type_inscription):
            cell_to_update = i
            break

    if cell_to_update is None:
        new_row = [nom_classe, etudiant, type_inscription, "Payé", montant, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        worksheet.append_row(new_row)
    else:
        statut_cell = f'D{cell_to_update}'  # StatutPaiement col
        montant_cell = f'E{cell_to_update}'  # Montant col
        date_cell = f'F{cell_to_update}'  # DatePaiement col

        worksheet.update(statut_cell, "Payé")

        current_montant = worksheet.acell(montant_cell).value
        total_montant = montant
        if current_montant:
            try:
                total_montant += float(current_montant)
            except ValueError:
                pass
        worksheet.update(montant_cell, total_montant)
        worksheet.update(date_cell, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def get_students_for_class(nom_classe):
    """
    Récupère la liste des étudiants pour une classe donnée depuis la feuille 'Classes'.
    Retourne une liste triée et sans doublons de noms d’étudiants.
    """
    try:
        sheet = get_sheet("Classes")
        records = sheet.get_all_records()
        students = [row.get("Etudiant").strip() for row in records if row.get("NomClasse") == nom_classe and row.get("Etudiant")]
        return sorted(set(students))
    except Exception as e:
        print(f"[Erreur get_students_for_class] {e}")
        return []


def get_payment_status(nom_classe, etudiant, type_inscription):
    """
    Retourne le statut du paiement (ex: "Payé" ou "Non payé") 
    pour un étudiant, classe et type d'inscription donné.
    """
    try:
        sheet = get_sheet("Paiements_Inscriptions")  # ou "Paiements" selon votre usage
        records = sheet.get_all_records()
        for row in records:
            if (row.get("NomClasse") == nom_classe and
                row.get("Etudiant") == etudiant and
                row.get("TypeInscription") == type_inscription):
                return row.get("StatutPaiement", "Non payé")
        return "Non payé"
    except Exception as e:
        print(f"[Erreur get_payment_status] {e}")
        return "Non payé"


def get_payment_summary(nom_classe, type_inscription):
    worksheet = get_or_create_inscriptions_sheet()
    records = worksheet.get_all_records()
    payes, non_payes, total_recettes = 0, 0, 0.0
    detail = {}

    for row in records:
        if row.get("NomClasse") == nom_classe and row.get("TypeInscription") == type_inscription:
            etudiant = row.get("Etudiant")
            statut = row.get("StatutPaiement", "Non payé")
            montant = float(row.get("Montant", 0))
            detail[etudiant] = statut
            if statut == "Payé":
                payes += 1
                total_recettes += montant
            else:
                non_payes += 1

    return {
        'payes': payes,
        'non_payes': non_payes,
        'total_recettes': total_recettes,
        'detail': detail
    }

import unicodedata

def normalize_str(s):
    if s is None:
        return ""
    s = str(s)

    # Unifier tirets et espaces
    s = s.replace('\u00A0', ' ')   # espace insécable -> espace normal
    s = s.replace('–', '-')        # EN DASH -> tiret normal
    s = s.replace('—', '-')        # EM DASH -> tiret normal

    # Supprimer espaces multiples
    s = " ".join(s.split())

    # Dé-accentuation
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))

    return s.lower().strip()


def get_payment_summary_travaux(nom_classe, type_travail):
    worksheet = get_or_create_travaux_sheet()  # à adapter à ton code gspread
    records = worksheet.get_all_records()

    nom_classe_norm = normalize_str(nom_classe)
    type_travail_norm = normalize_str(type_travail)

    print(f"[Travaux] Classe demandée : {nom_classe} -> {nom_classe_norm}")
    print(f"[Travaux] Travail demandé : {type_travail} -> {type_travail_norm}")
    print(f"[Travaux] Nb lignes lues depuis Google Sheet : {len(records)}")

    payes, non_payes, total_recettes = 0, 0, 0.0
    detail = {}

    for i, row in enumerate(records, 1):
        classe_raw = row.get("NomClasse", "")
        travail_raw = row.get("TypeTravail", "")
        etudiant_raw = row.get("Etudiant", "")
        statut_raw = row.get("StatutPaiement", "")
        montant_raw = row.get("Montant", 0)

        # Normalisation
        classe = normalize_str(classe_raw)
        travail = normalize_str(travail_raw)
        etudiant = str(etudiant_raw).strip()
        statut = str(statut_raw).strip()
        montant_str = str(montant_raw).strip()

        if classe != nom_classe_norm or travail != type_travail_norm:
            # Ligne ignorée (ne correspond pas aux filtres)
            if i <= 10:  # éviter trop de logs
                print(f"[Travaux][Row {i}] Ignorée: Classe='{classe_raw}' ({classe}) | "
                      f"Travail='{travail_raw}' ({travail})")
            continue

        try:
            montant = float(montant_str.replace(",", "."))
        except ValueError:
            montant = 0.0

        detail[etudiant] = {
            "type_travail": travail_raw,
            "statut": statut,
            "montant": montant,
        }

        if normalize_str(statut) == "paye":  # "Payé" normalisé -> "paye"
            payes += 1
            total_recettes += montant
        else:
            non_payes += 1

    summary = {
        "payes": payes,
        "non_payes": non_payes,
        "total_recettes": round(total_recettes, 2),
        "detail": detail,
    }

    print(f"[Travaux] Résumé final: {summary}")
    return summary



def get_or_create_travaux_sheet():
    """
    Récupère ou crée la feuille 'Travaux' avec colonnes initiales.
    """
    try:
        worksheet = sh.worksheet('Travaux')
    except WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Travaux', rows='1000', cols='10')
        headers = ['NomClasse', 'Etudiant', 'TypeTravail', 'StatutPaiement', 'Montant', 'DatePaiement']
        worksheet.append_row(headers)
    return worksheet


# Fonctions complémentaires que vous aviez précédemment, à maintenir ou adapter selon contexte

def ensure_ids(df, id_col="ID"):
    def safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    ids = []
    for i, v in enumerate(df[id_col]):
        iv = safe_int(v)
        if iv is None:
            iv = i + 1
        ids.append(iv)

    df[id_col] = ids
    return df


# Ajoutez ici les autres fonctions nécessaires pour votre projet...

# Exemple : génération PDF
def generate_summary_pdf(summary_data, nom_classe, type_inscription):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, f"Résumé des paiements - {nom_classe} - {type_inscription}")
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(margin, y, f"Étudiants payés : {summary_data['payes']}")
    y -= 20
    c.drawString(margin, y, f"Étudiants non payés : {summary_data['non_payes']}")
    y -= 20
    c.drawString(margin, y, f"Total des recettes : {summary_data['total_recettes']:.2f} USD")
    y -= 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Détail des paiements :")
    y -= 20

    c.setFont("Helvetica", 10)
    for etudiant, statut in summary_data['detail'].items():
        if y < margin:
            c.showPage()
            y = height - margin
            c.setFont("Helvetica", 10)
        c.drawString(margin, y, f"{etudiant}: {statut}")
        y -= 15

    c.save()
    buffer.seek(0)
    return buffer


def generate_summary_pdf_travaux(summary_data, nom_classe, type_travail):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    # Titre
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, f"Résumé des paiements - {nom_classe} - {type_travail}")
    y -= 30

    # Résumé global
    c.setFont("Helvetica", 12)
    c.drawString(margin, y, f"Étudiants payés : {summary_data['payes']}")
    y -= 20
    c.drawString(margin, y, f"Étudiants non payés : {summary_data['non_payes']}")
    y -= 20
    c.drawString(margin, y, f"Total des recettes : {summary_data['total_recettes']:.2f} USD")
    y -= 40

    # Détails
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Détail des paiements :")
    y -= 20

    c.setFont("Helvetica", 10)
    for etudiant, infos in summary_data['detail'].items():
        # infos doit contenir {'type_travail': ..., 'statut': ..., 'montant': ...}
        if y < margin:
            c.showPage()
            y = height - margin
            c.setFont("Helvetica", 10)

        ligne = (f"{etudiant} | Travail: {infos['type_travail']} | "
                 f"Statut: {infos['statut']} | Montant: {infos['montant']:.2f} USD")
        c.drawString(margin, y, ligne)
        y -= 15

    c.save()
    buffer.seek(0)
    return buffer


def lire_categories_paiement():
    """
    Lit la feuille 'CategoriesPaiement' et retourne un DataFrame avec les catégories.
    Si la feuille est vide, retourne un DataFrame avec la colonne 'Categorie' vide.
    """
    try:
        df = read_sheet("CategoriesPaiement")
        if df.empty:
            df = pd.DataFrame(columns=["Categorie"])
        else:
            df.columns = df.columns.str.strip()
            if "Categorie" not in df.columns:
                df["Categorie"] = ""
        return df
    except Exception as e:
        print(f"[Erreur lire_categories_paiement] {e}")
        return pd.DataFrame(columns=["Categorie"])

def lire_categories_depense():
    """
    Lit la feuille 'CategoriesDepense' et retourne un DataFrame avec les catégories.
    Si la feuille est vide, retourne un DataFrame avec la colonne 'Categorie' vide.
    """
    try:
        df = read_sheet("CategoriesDepense")
        if df.empty:
            df = pd.DataFrame(columns=["Categorie"])
        else:
            df.columns = df.columns.str.strip()
            if "Categorie" not in df.columns:
                df["Categorie"] = ""
        return df
    except Exception as e:
        print(f"[Erreur lire_categories_depense] {e}")
        return pd.DataFrame(columns=["Categorie"])
    
def write_sheet(sheet_name, df):
    """
    Écrit entièrement le DataFrame df dans la feuille sheet_name.
    Efface tout le contenu précédent.
    """
    ws = sh.worksheet(sheet_name)
    ws.clear()
    if df.empty:
        return
    values = [df.columns.tolist()] + df.values.tolist()
    ws.update(values)

def lire_cours():
    """
    Lit la feuille 'Cours' dans Google Sheets et renvoie un DataFrame pandas.
    """
    try:
        ws = sh.worksheet('Cours')
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        print(f"[Erreur lire_cours] {e}")
        return pd.DataFrame()


def lire_paiements_inscriptions():
    """Lit la feuille Paiements_Inscriptions et retourne un DataFrame."""
    try:
        ws = sh.worksheet('Paiements_Inscriptions')
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        print(f"Erreur lecture Paiements_Inscriptions: {e}")
        return pd.DataFrame()


def calcul_solde():
    """Calcule la somme des Montants dans Paiements_Inscriptions."""
    df_paiements = lire_paiements_inscriptions()
    if not df_paiements.empty and 'Montant' in df_paiements.columns:
        return df_paiements['Montant'].sum()
    else:
        return 0

#



def enregistrer_paiement_google(nom_classe, etudiant, type_inscription, montant=10.0):
    """
    Enregistre un paiement formaté dans la feuille Paiements_Inscriptions.
    :param nom_classe: str
    :param etudiant: str
    :param type_inscription: str
    :param montant: float (par défaut 10)
    :return: bool succès
    """
    try:
        ws = sh.worksheet('Paiements_Inscriptions')  # nom exact de la feuille
        date_paiement = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        ligne = [
            nom_classe,
            etudiant,
            type_inscription,
            "Payé",          # StatutPaiement fixe ici
            montant,
            date_paiement
        ]
        
        ws.append_row(ligne, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        print(f"Erreur lors de l'enregistrement paiement sur Google Sheets : {e}")
        return False




#



def enregistrer_paiement(date_paiement, montant, details=None):
    """
    Enregistre un nouveau paiement dans la feuille Paiements_Inscriptions.
    :param date_paiement: str, format 'YYYY-MM-DD' ou autre selon feuille
    :param montant: float, montant payé
    :param details: dict optionnel, autres informations à enregistrer
    """
    try:
        ws = sh.worksheet('Paiements_Inscriptions')
        # Construire une ligne de données dans l'ordre des colonnes
        ligne = [date_paiement, montant]
        if details:
            # Ajoutez d'autres colonnes depuis details
            for key in ['classe', 'etudiant', 'commentaire']:
                ligne.append(details.get(key, ''))
        ws.append_row(ligne, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        print(f"Erreur enregistrement paiement: {e}")
        return False


def ajouter_categorie_paiement(nouvelle):
    """
    Ajoute une nouvelle catégorie de paiement dans la feuille 'CategoriesPaiement'.
    Lève une exception si la catégorie existe déjà.
    """
    df = lire_categories_paiement()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle}])], ignore_index=True)
    write_sheet("CategoriesPaiement", df)

def ajouter_categorie_depense(nouvelle):
    """
    Ajoute une nouvelle catégorie dans la feuille 'CategoriesDepense'.
    Lève une exception si la catégorie existe déjà.
    """
    df = lire_categories_depense()
    if nouvelle in df["Categorie"].values:
        raise ValueError("La catégorie existe déjà")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle}])], ignore_index=True)
    write_sheet("CategoriesDepense", df)


def modifier_categorie_paiement(ancienne, nouvelle):
    """
    Modifie une catégorie existante dans 'CategoriesPaiement'.
    Remplace l'ancienne par la nouvelle dans la feuille.
    """
    df = lire_categories_paiement()
    if ancienne not in df["Categorie"].values:
        raise ValueError("La catégorie à modifier n'existe pas")
    if nouvelle in df["Categorie"].values:
        raise ValueError("La nouvelle catégorie existe déjà")
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    write_sheet("CategoriesPaiement", df)


def modifier_categorie_depense(ancienne, nouvelle):
    """
    Modifie une catégorie existante dans 'CategoriesDepense'.
    Remplace l'ancienne par la nouvelle dans la feuille.
    """
    df = lire_categories_depense()
    if ancienne not in df["Categorie"].values:
        raise ValueError("La catégorie à modifier n'existe pas")
    if nouvelle in df["Categorie"].values:
        raise ValueError("La nouvelle catégorie existe déjà")
    df.loc[df["Categorie"] == ancienne, "Categorie"] = nouvelle
    write_sheet("CategoriesDepense", df)


def supprimer_categorie_paiement(categorie):
    """
    Supprime une catégorie donnée de 'CategoriesPaiement'.
    """
    df = lire_categories_paiement()
    if categorie not in df["Categorie"].values:
        raise ValueError("La catégorie à supprimer n'existe pas")
    df = df[df["Categorie"] != categorie]
    write_sheet("CategoriesPaiement", df)


def supprimer_categorie_depense(categorie):
    """
    Supprime une catégorie donnée de 'CategoriesDepense'.
    """
    df = lire_categories_depense()
    if categorie not in df["Categorie"].values:
        raise ValueError("La catégorie à supprimer n'existe pas")
    df = df[df["Categorie"] != categorie]
    write_sheet("CategoriesDepense", df)


def enregistrer_paiement_travaux(nom_classe, etudiant, type_travail, montant):
    try:
        ws = sh.worksheet("Paiements_Travaux")
        date_paiement = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ligne = [nom_classe, etudiant, type_travail, "Payé", montant, date_paiement]
        ws.append_row(ligne, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du paiement travaux : {e}")
        return False



def assure_feuille_paiements_travaux():
    try:
        # Essayer de récupérer la feuille Paiements_Travaux
        ws_travaux = sh.worksheet("Paiements_Travaux")
    except gspread.exceptions.WorksheetNotFound:
        # La feuille n'existe pas, la créer avec les colonnes comme Paiements_Inscriptions

        # Récupérer la feuille Paiements_Inscriptions pour copier les colonnes
        try:
            ws_inscriptions = sh.worksheet("Paiements_Inscriptions")
            valeurs_entetes = ws_inscriptions.row_values(1)  # Première ligne, titres colonnes
        except gspread.exceptions.WorksheetNotFound:
            # Si la feuille inscriptions n'existe pas, définir colonnes par défaut
            valeurs_entetes = ["NomClasse", "Etudiant", "TypeTravail", "StatutPaiement", "Montant", "DatePaiement"]

        # Nombre de colonnes
        nb_colonnes = len(valeurs_entetes)

        # Créer la feuille Paiements_Travaux avec 100 lignes par défaut
        ws_travaux = sh.add_worksheet(title="Paiements_Travaux", rows="100", cols=str(nb_colonnes))

        # Écrire la ligne d'entête avec les colonnes copiées
        ws_travaux.append_row(valeurs_entetes, value_input_option="USER_ENTERED")

    return ws_travaux



# --- Lecture des paiements travaux depuis Google Sheets ---

def lire_paiements_travaux():
    ws = assure_feuille_paiements_travaux()  # Appel à la fonction qui crée si nécessaire
    data = ws.get_all_records()
    if data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=["NomClasse", "Etudiant", "TypeTravail", "StatutPaiement", "Montant", "DatePaiement"])
    return df


# --- Vérifie le statut de paiement d'un étudiant pour un type de travail donné ---

def get_payment_status_travaux(nom_classe, etudiant, type_travail):
    df = lire_paiements_travaux()
    filtre = (
        (df["NomClasse"] == nom_classe) &
        (df["Etudiant"] == etudiant) &
        (df["TypeTravail"] == type_travail) &
        (df["StatutPaiement"] == "Payé")
    )
    return "Payé" if not df[filtre].empty else None

# --- Enregistre un paiement dans la feuille Paiements_Travaux ---



# --- Met à jour le paiement pour un étudiant (sert dans liste et enregistrement) ---

def update_student_payment_travaux(nom_classe, etudiant, type_travail, montant):
    # Pour simplifier ici, on appelle directement enregistrer_paiement_travaux
    # Vous pouvez étendre pour supporter mise à jour existante
    return enregistrer_paiement_travaux(nom_classe, etudiant, type_travail, montant)

def total_paiements_travaux():
    df = lire_paiements_travaux()
    if df.empty:
        return 0.0
    return df['Montant'].sum()

def get_payment_status_inscription(nom_classe, etudiant, type_inscription):
    """
    Retourne le statut de paiement de l'étudiant pour une classe et type d'inscription donnés.
    Renvoie 'Payé' ou 'Non payé'.
    """
    df = lire_paiements_inscriptions()  # fonction à adapter pour charger la feuille inscriptions

    # Nettoyer les noms de colonnes
    df.columns = df.columns.str.strip()

    # Filtrer par classe, étudiant et type inscription
    filt = (
        (df['NomClasse'] == nom_classe) &
        (df['Etudiant'] == etudiant) &
        (df['TypeInscription'] == type_inscription)
    )

    ligne = df[filt]
    if not ligne.empty:
        statut = ligne.iloc[0]['StatutPaiement']
        if statut and statut.lower() == 'payé':
            return "Payé"

    return "Non payé"





# Variables globales configuration (adapter si besoin)
CREDENTIALS_FILE = 'facultairecashwebapp-5b853b8f0832.json'
SPREADSHEET_NAME = 'ULGLP_Caisse'

# Initialiser la connexion Google Sheets (faire une seule fois)
gc = gspread.service_account(filename=CREDENTIALS_FILE)
sh = gc.open(SPREADSHEET_NAME)

def get_sheet_dataframe(sheet_title):
    try:
        worksheet = sh.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        # Si la feuille n'existe pas, retourne DataFrame vide
        return pd.DataFrame()
    df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)
    # Supprimer les lignes vides créées automatiquement en fin de sheet
    df.dropna(how='all', inplace=True)
    return df

def lire_inscriptions():
    """
    Lit toutes les données de la feuille inscriptions en DataFrame.
    """
    return get_sheet_dataframe('Paiements_Inscriptions')

def lire_paiements_travaux():
    """
    Lit toutes les données de la feuille paiements travaux en DataFrame.
    """
    return get_sheet_dataframe('Paiements_Travaux')
