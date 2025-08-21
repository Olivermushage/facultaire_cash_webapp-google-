from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import os
from fpdf import FPDF
import io
from datetime import datetime
import sys
import webbrowser
import threading
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.username

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

from flask_login import LoginManager, login_user, logout_user, login_required, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Nom de la route de la page de connexion

# Chargement d’un utilisateur par ID (ici username)
@login_manager.user_loader
def load_user(username):
    # Charger l’utilisateur depuis votre stockage (JSON, Excel, DB, etc)
    user_data = get_user_by_username(username)
    if user_data:
        return User(user_data['username'], user_data['password_hash'])
    return None



DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# Fichiers Excel utilisés par l'application
FICHIER_CAISSE = os.path.join(DATA_FOLDER, "caisse.xlsx")
CLASSES_FILE = os.path.join(DATA_FOLDER, "classes.xlsx")
PAIEMENTS_FILE = os.path.join(DATA_FOLDER, "paiements.xlsx")
DEPENSES_FILE = os.path.join(DATA_FOLDER, "depenses.xlsx")
COURS_FILE = os.path.join(DATA_FOLDER, "cours_par_classe.xlsx")
COMMENTS_DIR = "data"
COMMENTS_FILE = os.path.join(COMMENTS_DIR, "comments.xlsx")
TRAVAUX_DEPENSES_FILE = os.path.join(DATA_FOLDER, "depenses_travaux.xlsx")

def init_depenses_travaux_excel():
    if not os.path.exists(TRAVAUX_DEPENSES_FILE):
        df = pd.DataFrame(columns=["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "Montant", "DateDepense"])
        df.to_excel(TRAVAUX_DEPENSES_FILE, index=False)

def lire_depenses_travaux():
    if not os.path.exists(TRAVAUX_DEPENSES_FILE):
        init_depenses_travaux_excel()
    return pd.read_excel(TRAVAUX_DEPENSES_FILE)

def enregistrer_depense_travail(data):
    df = lire_depenses_travaux()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_excel(TRAVAUX_DEPENSES_FILE, index=False)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=resource_path('static'))
app.secret_key = "gN9v!2mLzXqPp7&4sRfT"  # Exemple de chaîne complexe, unique et aléatoire

# Si vous chargez d’autres fichiers (Excel etc), utilisez resource_path pour les chemins
DATA_FOLDER = resource_path('data')

# Ajoutez ici si besoin d'autres fichiers spécifiques, par ex :
AUTRES_RECETTES_FILE = os.path.join(DATA_FOLDER, "autres_recettes.xlsx")

def init_excel():
    if not os.path.exists(FICHIER_CAISSE):
        df = pd.DataFrame(columns=["Date", "Nom", "Type", "Montant", "Description"])
        df.to_excel(FICHIER_CAISSE, index=False)

def lire_caisse():
    return pd.read_excel(FICHIER_CAISSE)

def init_classes_excel():
    if not os.path.exists(CLASSES_FILE):
        df = pd.DataFrame(columns=["NomClasse", "Etudiant"])
        df.to_excel(CLASSES_FILE, index=False)

def lire_classes():
    return pd.read_excel(CLASSES_FILE)

def init_paiements_excel():
    if not os.path.exists(PAIEMENTS_FILE):
        df = pd.DataFrame(columns=["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"])
        df.to_excel(PAIEMENTS_FILE, index=False)



def lire_recettes():
    # Création du dossier data si nécessaire
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    # Lecture du fichier autres_recettes, ou création vide si absent
    if os.path.exists(AUTRES_RECETTES_FILE):
        df_autres = pd.read_excel(AUTRES_RECETTES_FILE)
    else:
        colonnes = ["Date", "Source", "Type", "Description", "Montant"]
        df_autres = pd.DataFrame(columns=colonnes)
        df_autres.to_excel(AUTRES_RECETTES_FILE, index=False)

    # Lecture du fichier paiements, ou création vide si absent
    if os.path.exists(PAIEMENTS_FILE):
        df_paiements = pd.read_excel(PAIEMENTS_FILE)
    else:
        # Colonnes minimales supposées dans paiements.xlsx (à adapter)
        colonnes_paiements = ["Date", "Source", "Type", "Description", "Montant"]
        df_paiements = pd.DataFrame(columns=colonnes_paiements)
        df_paiements.to_excel(PAIEMENTS_FILE, index=False)

    # Uniformiser les colonnes aux mêmes noms (si noms différents)
    # Ici on suppose qu'ils sont déjà cohérents; sinon adapter le renommage :
    # Exemple : df_paiements.rename(columns={"DatePaiement": "Date"}, inplace=True)

    # Concatène les deux DataFrames
    df_recettes = pd.concat([df_autres, df_paiements], ignore_index=True, sort=False)

    # S'assurer que la colonne Montant est bien numérique
    df_recettes["Montant"] = pd.to_numeric(df_recettes.get("Montant", pd.Series()), errors="coerce").fillna(0)

    # Remplir colonnes manquantes avec des valeurs vides si besoin
    colonnes_necessaires = ["Date", "Source", "Type", "Description", "Montant"]
    for col in colonnes_necessaires:
        if col not in df_recettes.columns:
            df_recettes[col] = ""

    # Optionnel : trier par date décroissante si la colonne Date est correcte 
    if "Date" in df_recettes.columns:
        try:
            df_recettes["Date"] = pd.to_datetime(df_recettes["Date"], errors="coerce")
            df_recettes = df_recettes.sort_values(by="Date", ascending=False)
        except Exception:
            pass

    return df_recettes.reset_index(drop=True)



def init_depenses_excel():
    if not os.path.exists(DEPENSES_FILE):
        df = pd.DataFrame(columns=["NomCours", "DateExamen", "CategorieDepense", "Description", "Montant"])
        df.to_excel(DEPENSES_FILE, index=False)



def lire_depenses():
    # Si le fichier n'existe pas, on le crée avec la structure adaptée
    if not os.path.exists(DEPENSES_FILE):
        colonnes = ["NomClasse", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"]
        # Init vide, colonnes adaptées pour les dépenses classiques et travaux
        df_vide = pd.DataFrame(columns=colonnes)
        df_vide.to_excel(DEPENSES_FILE, index=False)
        return df_vide
    
    # Lire le fichier Excel
    df = pd.read_excel(DEPENSES_FILE)

    # Vérifier colonnes attendues, et ajouter celles manquantes si besoin (au cas où)
    colonnes_necessaires = ["NomClasse", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"]

    for col in colonnes_necessaires:
        if col not in df.columns:
            df[col] = pd.NA  # Ajoute colonne vide si manquante

    # Optionnel : s’assurer que les types de colonnes sont corrects (ex: Montant en float)
    df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)

    return df


def init_cours_excel():
    if not os.path.exists(COURS_FILE):
        df = pd.DataFrame(columns=["NomClasse", "NomCours"])
        df.to_excel(COURS_FILE, index=False)

def lire_cours():
    return pd.read_excel(COURS_FILE)

def enregistrer_operation(data):
    df = lire_caisse()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_excel(FICHIER_CAISSE, index=False)

def enregistrer_classe_etudiants(nom_classe, liste_etudiants):
    df = lire_classes()
    nouvelles_entrees = pd.DataFrame({
        "NomClasse": [nom_classe]*len(liste_etudiants),
        "Etudiant": liste_etudiants
    })
    df = pd.concat([df, nouvelles_entrees], ignore_index=True)
    df.to_excel(CLASSES_FILE, index=False)

def enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement):
    df = lire_paiements()
    nouvelle_ligne = pd.DataFrame([{
        "NomClasse": nom_classe,
        "Etudiant": etudiant,
        "CategoriePaiement": categorie,
        "Montant": montant,
        "DatePaiement": date_paiement
    }])
    df = pd.concat([df, nouvelle_ligne], ignore_index=True)
    df.to_excel(PAIEMENTS_FILE, index=False)


def lire_autres_recettes():
    # Crée le dossier data s'il n'existe pas
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    # Colonnes attendues dans autres_recettes.xlsx (à adapter selon votre fichier)
    colonnes = ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant","Description"]

    # Si le fichier n'existe pas, le créer avec un DataFrame vide
    if not os.path.exists(AUTRES_RECETTES_FILE):
        df_vide = pd.DataFrame(columns=colonnes)
        df_vide.to_excel(AUTRES_RECETTES_FILE, index=False)
        return df_vide

    # Lire le fichier Excel existant
    df = pd.read_excel(AUTRES_RECETTES_FILE)

    # S'assurer que les colonnes nécessaires sont présentes
    for col in colonnes:
        if col not in df.columns:
            df[col] = ""

    # S'assurer que Montant est bien de type numérique
    df["Montant"] = pd.to_numeric(df.get("Montant", pd.Series()), errors="coerce").fillna(0)

    # Convertir la colonne Date en datetime si possible
    try:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    except Exception:
        pass

    return df


def enregistrer_autre_recette(nom_classe, etudiant, categorie_paiement, montant, description, date):
    df = lire_autres_recettes()
    nouvelle_ligne = pd.DataFrame([{
        "Date": date,
        "NomClasse": nom_classe,
        "Etudiant": etudiant,
        "CategoriePaiement": categorie_paiement,
        "Montant": montant,
        "Description": description
    }])
    df = pd.concat([df, nouvelle_ligne], ignore_index=True)
    df.to_excel(AUTRES_RECETTES_FILE, index=False)


def enregistrer_depense(data):
    # Lire le DataFrame actuel
    df = lire_depenses()

    # Colonnes attendues dans le fichier
    colonnes_necessaires = [
        "NomClasse",
        "DateExamen",
        "CategorieDepense",
        "Description",
        "Montant",
        "TypeDepense",
        "Commentaire",
        "DateDepense"
    ]

    # S’assurer que toutes les colonnes nécessaires sont présentes dans data
    # Si absentes, on les ajoute avec une valeur par défaut (vide ou None)
    for col in colonnes_necessaires:
        if col not in data:
            # Assignation cohérente selon type attendu ; ici None ou vide string
            data[col] = None if col not in ["Montant"] else 0

    # Créer un nouveau DataFrame ligne avec toutes les colonnes dans l'ordre
    new_row_df = pd.DataFrame([{col: data.get(col, None) for col in colonnes_necessaires}])

    # Ajouter la nouvelle ligne au DataFrame existant
    df = pd.concat([df, new_row_df], ignore_index=True)

    # Sauvegarder dans le fichier Excel
    df.to_excel(DEPENSES_FILE, index=False)

def enregistrer_cours(nom_classe, nom_cours):
    df = lire_cours()
    if not ((df["NomClasse"] == nom_classe) & (df["NomCours"] == nom_cours)).any():
        nouvelle_ligne = pd.DataFrame([{"NomClasse": nom_classe, "NomCours": nom_cours}])
        df = pd.concat([df, nouvelle_ligne], ignore_index=True)
        df.to_excel(COURS_FILE, index=False)

def lire_paiements():
    return pd.read_excel(PAIEMENTS_FILE)

RECETTES_FILE = os.path.join(DATA_FOLDER, "recettes.xlsx")

def lire_recettes():
    # Crée le dossier data s'il n'existe pas
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    
    # Si le fichier n'existe pas, on crée un DataFrame vide avec les colonnes attendues
    if not os.path.exists(RECETTES_FILE):
        colonnes = ["Date", "Source", "Type", "Description", "Montant"]
        df_vide = pd.DataFrame(columns=colonnes)
        df_vide.to_excel(RECETTES_FILE, index=False)
        return df_vide

    # Sinon on charge le fichier existant
    df = pd.read_excel(RECETTES_FILE)
    # Assurer que Montant est numeric pour éviter erreur sommaire
    df["Montant"] = pd.to_numeric(df.get("Montant", pd.Series()), errors="coerce").fillna(0)
    return df



@app.route("/")
def index():
    df_paiements = lire_paiements()           # Paiements classiques
    df_autres_recettes = lire_autres_recettes()  # Recettes manuelles ou autres recettes spéciales
    df_depenses = lire_depenses()
    df_classes = lire_classes()

    # Concaténer les deux DataFrames recettes
    df_paiements_complets = pd.concat([df_paiements, df_autres_recettes], ignore_index=True)

    # Liste de catégories présentes (utile si vous souhaitez filtrer)
    categories_validees = df_paiements_complets["CategoriePaiement"].unique().tolist()

    # S'assurer que "Recette manuelle" est prise en compte (au cas où)
    if "Recette manuelle" not in categories_validees:
        categories_validees.append("Recette manuelle")

    # Filtrer les paiements/recettes selon ces catégories (par défaut tout)
    paiements_pertinents = df_paiements_complets[df_paiements_complets["CategoriePaiement"].isin(categories_validees)]

    # Calcul des totaux
    total_paiements = paiements_pertinents["Montant"].sum()
    total_depenses = df_depenses["Montant"].sum()
    solde = total_paiements - total_depenses

    # Dépenses examens / autres
    depenses_examen = df_depenses[df_depenses["NomCours"].notna() & (df_depenses["NomCours"] != "")]
    total_depenses_examen = depenses_examen["Montant"].sum()

    depenses_autres = df_depenses[df_depenses["NomCours"].isna() | (df_depenses["NomCours"] == "")]
    total_depenses_autres = depenses_autres["Montant"].sum()

    # Informations par classe
    classes_info = []
    classes = df_classes["NomClasse"].drop_duplicates().tolist()
    for classe in classes:
        etudiants = df_classes[df_classes["NomClasse"] == classe]["Etudiant"].drop_duplicates().tolist()
        paiements_classe = df_paiements_complets[df_paiements_complets["NomClasse"] == classe]
        paiements_par_categorie = {}
        for cat in paiements_classe["CategoriePaiement"].drop_duplicates():
            nb_etudiants = len(paiements_classe[paiements_classe["CategoriePaiement"] == cat]["Etudiant"].drop_duplicates())
            paiements_par_categorie[cat] = nb_etudiants

        classes_info.append({
            "classe": classe,
            "total_etudiants": len(etudiants),
            "paiements_par_categorie": paiements_par_categorie
        })

    return render_template("index.html",
                           solde=round(solde, 2),
                           total_depenses_examen=round(total_depenses_examen, 2),
                           total_depenses_autres=round(total_depenses_autres, 2),
                           classes_info=classes_info)


@app.route("/historique")
def historique():
    # Lire les opérations en caisse
    df_caisse = lire_caisse()
    # Lire les dépenses (classiques + travaux dans depenses.xlsx)
    df_depenses = lire_depenses()
    # Lire les recettes (nouvelle source)
    df_recettes = lire_recettes()  # Assurez-vous que cette fonction est définie

    # Récupérer la recherche en minuscules
    recherche = request.args.get("recherche", "").strip().lower()

    # Filtrer df_caisse selon recherche sur tous les champs concaténés
    if recherche:
        df_caisse = df_caisse[df_caisse.apply(lambda row: recherche in " ".join(str(v).lower() for v in row), axis=1)]

    # Filtrer df_depenses selon même recherche
    if recherche:
        df_depenses = df_depenses[df_depenses.apply(lambda row: recherche in " ".join(str(v).lower() for v in row), axis=1)]

    # Filtrer df_recettes selon recherche aussi
    if recherche:
        df_recettes = df_recettes[df_recettes.apply(lambda row: recherche in " ".join(str(v).lower() for v in row), axis=1)]

    # Séparer les dépenses liées aux travaux et les autres dépenses
    df_travaux = df_depenses[df_depenses["CategorieDepense"].str.contains("Travail", na=False, case=False)]
    df_depenses_classiques = df_depenses[~df_depenses["CategorieDepense"].str.contains("Travail", na=False, case=False)]

    # Convertir en listes pour le template
    operations_caisse = df_caisse.to_dict(orient="records")
    depenses_classiques = df_depenses_classiques.to_dict(orient="records")
    depenses_travaux = df_travaux.to_dict(orient="records")
    recettes = df_recettes.to_dict(orient="records")

    # Pagination uniquement sur les opérations en caisse (à adapter si besoin)
    page = request.args.get("page", 1, type=int)
    per_page = 20
    total = len(operations_caisse)
    total_pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    operations_page = operations_caisse[start:end]

    # Calculs sommaires pour totaux et solde
    total_caisse = df_caisse["Montant"].sum()
    total_depenses_classiques = df_depenses_classiques["Montant"].sum()
    total_travaux = df_travaux["Montant"].sum()
    total_recettes = df_recettes["Montant"].sum()
    solde = total_caisse + total_recettes - (total_depenses_classiques + total_travaux)

    return render_template(
        "historique.html",
        operations=operations_page,
        depenses_classiques=depenses_classiques,
        depenses_travaux=depenses_travaux,
        recettes=recettes,
        page=page,
        total_pages=total_pages,
        total_caisse=total_caisse,
        total_depenses_classiques=total_depenses_classiques,
        total_travaux=total_travaux,
        total_recettes=total_recettes,
        solde=solde,
        recherche=recherche
    )




@app.route("/depenses/autres")
def liste_depenses_autres():
    df = lire_depenses()
    depenses_autres = df[df["NomCours"].isna() | (df["NomCours"] == "")]
    recherche = request.args.get("recherche", "").strip().lower()
    depenses_list = depenses_autres.to_dict(orient="records")
    if recherche:
        depenses_list = [d for d in depenses_list if recherche in (d.get('Description') or '').lower() or recherche in (d.get('CategorieDepense') or '').lower()]

    page = request.args.get("page", 1, type=int)
    per_page = 15
    total = len(depenses_list)
    total_pages = (total + per_page -1) // per_page
    if page <1:
        page=1
    elif page > total_pages and total_pages>0:
        page = total_pages
    start = (page-1)*per_page
    end = start + per_page
    depenses_page = depenses_list[start:end]

    return render_template("liste_depenses.html", depenses=depenses_page, titre="Autres dépenses", nom_classe=None, page=page, total_pages=total_pages)

@app.route("/depenses")
def depenses():
    # Exemple : si vous n’avez pas le contexte, on prend la première classe par défaut pour les liens
    df_classes = lire_classes()
    classes = df_classes["NomClasse"].drop_duplicates().tolist()
    premiere_classe = classes[0] if classes else "default-classe"

    return render_template("depenses.html", premiere_classe=premiere_classe)


@app.route("/classes")
def liste_classes():
    df = lire_classes()
    recherche = request.args.get("recherche", "").strip().lower()
    classes = df["NomClasse"].drop_duplicates()
    if recherche:
        classes = classes[classes.str.lower().str.contains(recherche)]
    classes = classes.tolist()

    page = request.args.get("page", 1, type=int)
    per_page = 15
    total = len(classes)
    total_pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    classes_page = classes[start:end]

    return render_template("liste_classes.html",
                           classes=classes_page,
                           page=page,
                           total_pages=total_pages)

@app.route("/classe/<nom_classe>")
def detail_classe(nom_classe):
    df_classes = lire_classes()
    df_paiements = lire_paiements()
    df_comments = lire_comments()
    df_cours = lire_cours()

    df_comments.columns = df_comments.columns.str.strip()

    # Extraction et tri alphabétique des étudiants
    etudiants_liste = sorted(df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"].unique().tolist())

    recherche = request.args.get("recherche", "").strip().lower()
    if recherche:
        etudiants_liste = [etu for etu in etudiants_liste if recherche in etu.lower()]

    page = request.args.get("page", 1, type=int)
    per_page = 15
    total = len(etudiants_liste)
    total_pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    etudiants_page = etudiants_liste[start:end]

    df_etudiants_page = pd.DataFrame({"Etudiant": etudiants_page})

    df_comments_classe = df_comments[df_comments["NomClasse"] == nom_classe][["Etudiant", "Commentaire"]]

    df_etudiants_page = df_etudiants_page.merge(df_comments_classe, how="left", on="Etudiant")
    df_etudiants_page["Commentaire"] = df_etudiants_page["Commentaire"].fillna("")

    paiements_dict = {}
    for etu in etudiants_page:
        paiements_etu = df_paiements[(df_paiements["NomClasse"] == nom_classe) & (df_paiements["Etudiant"] == etu)]
        paiements_dict[etu] = paiements_etu.to_dict(orient="records")

    cours_classe = df_cours[df_cours["NomClasse"] == nom_classe]["NomCours"].tolist()

    liste_etudiants = df_etudiants_page.to_dict(orient="records")

    return render_template(
        "detail_classe.html",
        nom_classe=nom_classe,
        etudiants=liste_etudiants,
        paiements=paiements_dict,
        cours_classe=cours_classe,
        page=page,
        total_pages=total_pages,
        per_page=per_page
    )

@app.route("/ajouter", methods=["GET", "POST"])
def ajouter():
    if request.method == "POST":
        try:
            data = {
                "Date": request.form["date"],
                "Nom": request.form["nom"],
                "Type": request.form["type"],
                "Montant": float(request.form["montant"]),
                "Description": request.form["description"]
            }
            if data["Montant"] <= 0:
                flash("Erreur : Le montant doit être supérieur à zéro.", "error")
                return redirect(url_for("ajouter"))
            enregistrer_operation(data)
            flash("Opération enregistrée avec succès !", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "error")
            return redirect(url_for("ajouter"))
    return render_template("ajouter.html")

@app.route("/creer_classe", methods=["GET", "POST"])
def creer_classe():
    if request.method == "POST":
        nom_classe = request.form["nom_classe"].strip()
        etudiants_brut = request.form["etudiants"]
        liste_etudiants = [e.strip() for e in etudiants_brut.split("\n") if e.strip()]
        if not nom_classe:
            flash("Le nom de la classe ne peut pas être vide.", "error")
            return redirect(url_for("creer_classe"))
        if not liste_etudiants:
            flash("La liste des étudiants ne peut pas être vide.", "error")
            return redirect(url_for("creer_classe"))
        enregistrer_classe_etudiants(nom_classe, liste_etudiants)
        flash(f"Classe '{nom_classe}' créée avec {len(liste_etudiants)} étudiants.", "success")
        return redirect(url_for("index"))
    return render_template("creer_classe.html")

@app.route("/classe/<nom_classe>/ajouter_cours", methods=["GET", "POST"])
def ajouter_cours(nom_classe):
    if request.method == "POST":
        cours_brut = request.form["cours"]
        liste_cours = [c.strip() for c in cours_brut.splitlines() if c.strip()]
        for c in liste_cours:
            enregistrer_cours(nom_classe, c)
        flash(f"{len(liste_cours)} cours ajoutés à la classe {nom_classe}.", "success")
        return redirect(url_for("detail_classe", nom_classe=nom_classe))
    return render_template("ajouter_cours.html", nom_classe=nom_classe)

@app.route("/classe/<nom_classe>/etudiant/<etudiant>/ajouter_paiement", methods=["GET", "POST"])
def ajouter_paiement(nom_classe, etudiant):
    # Lecture dynamique des catégories depuis le fichier categories_paiement.xlsx
    df_cats = lire_categories_paiement()
    categories = df_cats['Categorie'].dropna().tolist()  # Supprime les valeurs nulles au cas où

    if request.method == "POST":
        try:
            categorie = request.form.get("categorie")
            montant_raw = request.form.get("montant", "0").strip()
            date_paiement = request.form.get("date_paiement")

            # Validation du montant
            try:
                montant = float(montant_raw)
            except ValueError:
                flash("Le montant doit être un nombre valide.", "error")
                return redirect(url_for("ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))

            if montant <= 0:
                flash("Erreur : Le montant doit être supérieur à zéro.", "error")
                return redirect(url_for("ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))

            if categorie not in categories:
                flash("La catégorie sélectionnée est invalide.", "error")
                return redirect(url_for("ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))

            if not date_paiement:
                # Optionnel : vous pouvez remplir date_paiement automatiquement ici ou forcer la saisie
                date_paiement = datetime.now().strftime("%Y-%m-%d")

            # Enregistrement du paiement
            enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement)
            flash(f"Paiement ajouté pour {etudiant} ({categorie})", "success")
            return redirect(url_for("detail_classe", nom_classe=nom_classe))
        except Exception as e:
            flash(f"Erreur lors de l'ajout du paiement : {str(e)}", "error")
            return redirect(url_for("ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))

    # En GET, envoi des catégories dynamiques au template
    return render_template("ajouter_paiement.html", nom_classe=nom_classe, etudiant=etudiant, categories=categories)



@app.route("/classe/<nom_classe>/generer_pdf_categorie/<categorie>")
def generer_pdf_categorie(nom_classe, categorie):
    df_paiements = lire_paiements()
    df_classes = lire_classes()
    
    # Liste complète des étudiants de la classe (unique)
    etudiants_classe = df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"].drop_duplicates().reset_index(drop=True)
    
    # Filtrer paiements selon classe et catégorie
    if categorie == "Toutes":
        paiements_filtrés = df_paiements[df_paiements["NomClasse"] == nom_classe]
    else:
        paiements_filtrés = df_paiements[
            (df_paiements["NomClasse"] == nom_classe) &
            (df_paiements["CategoriePaiement"] == categorie)
        ]
    
    # Construire DataFrame avec tous les étudiants et leur paiement s'il existe
    # left merge sur "Etudiant"
    df_complet = etudiants_classe.to_frame().merge(
        paiements_filtrés[["Etudiant", "Montant", "DatePaiement", "CategoriePaiement"]],
        on="Etudiant",
        how="left"
    )
    
    # Remplacer les valeurs manquantes de paiement par valeurs par défaut
    df_complet["Montant"] = df_complet["Montant"].fillna(0)
    df_complet["DatePaiement"] = df_complet["DatePaiement"].fillna("-")
    df_complet["CategoriePaiement"] = df_complet["CategoriePaiement"].fillna("Aucun paiement")
    
    if df_complet.empty:
        flash(f"Aucun étudiant trouvé pour la classe '{nom_classe}'.", "warning")
        return redirect(url_for("detail_classe", nom_classe=nom_classe))
    
    # Initialiser le PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    titre_pdf = f"Paiements - Classe {nom_classe}"
    if categorie != "Toutes":
        titre_pdf += f" - Catégorie {categorie}"
    pdf.cell(0, 10, titre_pdf, ln=1, align="C")
    pdf.ln(5)
    
    # En-tête du tableau
    col_widths = [70, 40, 50]  # Étudiant, Montant, Date paiement
    headers = ["Étudiant", "Montant (USD)", "Date Paiement"]
    
    def dessiner_entete():
        pdf.set_font("Arial", "B", 12)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, border=1, align="C")
        pdf.ln()
    
    def dessiner_ligne(etudiant, montant, date_paiement):
        pdf.set_font("Arial", "", 12)
        pdf.cell(col_widths[0], 10, str(etudiant), border=1)
        pdf.cell(col_widths[1], 10, f"{montant:.2f} USD", border=1, align="R")
        pdf.cell(col_widths[2], 10, str(date_paiement), border=1)
        pdf.ln()
    
    dessiner_entete()
    for _, row in df_complet.iterrows():
        if pdf.get_y() > 265:
            pdf.add_page()
            dessiner_entete()
        dessiner_ligne(row["Etudiant"], row["Montant"], row["DatePaiement"])
    
    pdf_output = pdf.output(dest='S').encode('latin1', errors='replace')
    mem_pdf = io.BytesIO(pdf_output)
    mem_pdf.seek(0)
    
    return send_file(mem_pdf,
                     download_name=f"Paiements_{nom_classe}_{categorie}.pdf",
                     as_attachment=True)


@app.route("/depenses/ajouter_examen/<nom_classe>", methods=["GET", "POST"])
def ajouter_depense_examen(nom_classe):
    categories = [
        "Paiement surveillance",
        "Paiement correction",
        "Paiement envoi copie",
        "Autre"
    ]
    df_cours = lire_cours()
    cours_classe = df_cours[df_cours["NomClasse"] == nom_classe]["NomCours"].tolist()

    if request.method == "POST":
        cat = request.form.get("categorie", "").strip()
        categorie_autre = request.form.get("categorie_autre", "").strip()
        nom_cours = request.form.get("nom_cours", "").strip()
        date_examen = request.form.get("date_examen", "").strip()
        description = request.form.get("description", "").strip()
        montant_raw = request.form.get("montant", "").strip()

        erreurs = []

        # Validation du cours sélectionné
        if not nom_cours:
            erreurs.append("Le cours est obligatoire.")
        elif nom_cours not in cours_classe:
            erreurs.append("Le cours sélectionné est invalide.")

        # Validation catégorie
        if not cat:
            erreurs.append("La catégorie de dépense est obligatoire.")
        elif cat == "Autre":
            if not categorie_autre:
                erreurs.append("Merci de préciser la catégorie 'Autre'.")
            else:
                cat = categorie_autre  # remplacer par catégorie personnalisée

        # Validation date
        if not date_examen:
            erreurs.append("La date de l'examen est obligatoire.")

        # Validation montant
        try:
            montant = float(montant_raw)
            if montant <= 0:
                erreurs.append("Le montant doit être supérieur à zéro.")
        except ValueError:
            erreurs.append("Le montant est invalide.")

        if erreurs:
            for err in erreurs:
                flash(err, "error")
            # En cas d'erreurs, ne pas faire de redirect, mais rendre le formulaire avec les données saisies
            return render_template(
                "ajouter_depense_examen.html",
                categories=categories,
                nom_classe=nom_classe,
                cours_classe=cours_classe,
                categorie_selectionnee=cat,
                categorie_autre_valeur=categorie_autre,
                nom_cours_selectionne=nom_cours,
                date_examen_valeur=date_examen,
                description_valeur=description,
                montant_valeur=montant_raw
            )

        # Préparer les données à sauvegarder
        data = {
            "NomCours": nom_cours,
            "DateExamen": date_examen,
            "CategorieDepense": cat,
            "Description": description,
            "Montant": montant
        }

        try:
            enregistrer_depense(data)
            flash("Dépense liée à un examen enregistrée !", "success")
            return redirect(url_for("liste_depenses_examen", nom_classe=nom_classe))
        except Exception as e:
            flash(f"Erreur lors de l'enregistrement de la dépense : {str(e)}", "error")
            return render_template(
                "ajouter_depense_examen.html",
                categories=categories,
                nom_classe=nom_classe,
                cours_classe=cours_classe,
                categorie_selectionnee=cat,
                categorie_autre_valeur=categorie_autre,
                nom_cours_selectionne=nom_cours,
                date_examen_valeur=date_examen,
                description_valeur=description,
                montant_valeur=montant_raw
            )

    # En GET, affichage du formulaire simple
    return render_template(
        "ajouter_depense_examen.html",
        categories=categories,
        nom_classe=nom_classe,
        cours_classe=cours_classe
    )


@app.route("/depenses/ajouter_autres", methods=["GET", "POST"])
def ajouter_depense_autres():
    categories = [
        "Achat fournitures",
        "Paiement primes",
        "Autre"
    ]
    if request.method == "POST":
        cat = request.form["categorie"]
        if cat == "Autre":
            cat = request.form.get("categorie_autre", "").strip() or "Autre"
        try:
            data = {
                "NomCours": "",
                "DateExamen": "",
                "CategorieDepense": cat,
                "Description": request.form["description"],
                "Montant": float(request.form["montant"])
            }
            if data["Montant"] <= 0:
                flash("Erreur : Le montant doit être supérieur à zéro.", "error")
                return redirect(url_for("ajouter_depense_autres"))
            enregistrer_depense(data)
            flash("Autre dépense enregistrée !", "success")
            return redirect(url_for("liste_depenses_autres"))
        except Exception as e:
            flash(f"Erreur lors de l'enregistrement de la dépense : {str(e)}", "error")
            return redirect(url_for("ajouter_depense_autres"))
    return render_template("ajouter_depense_autres.html", categories=categories)

def init_comments_excel():
    if not os.path.exists(COMMENTS_FILE):
        df = pd.DataFrame(columns=["NomClasse", "Etudiant", "Commentaire"])
        df.to_excel(COMMENTS_FILE, index=False)


def lire_comments():
    # Création du dossier 'data' s'il n'existe pas
    if not os.path.exists(COMMENTS_DIR):
        os.makedirs(COMMENTS_DIR)

    # Si le fichier comments.xlsx n'existe pas, on le crée avec la structure minimale attendue
    if not os.path.exists(COMMENTS_FILE):
        # Colonnes minimales nécessaires à votre logique
        colonnes = ["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"]
        df_empty = pd.DataFrame(columns=colonnes)
        df_empty.to_excel(COMMENTS_FILE, index=False)
    return pd.read_excel(COMMENTS_FILE)


CATEGORIES_PAIEMENT_FILE = os.path.join(DATA_FOLDER, "categories_paiement.xlsx")

def lire_categories_paiement():
    if not os.path.exists(CATEGORIES_PAIEMENT_FILE):
        df_vide = pd.DataFrame(columns=["Categorie"])
        df_vide.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)
        return df_vide
    return pd.read_excel(CATEGORIES_PAIEMENT_FILE)

def enregistrer_categories_paiement(df_cats):
    df_cats.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)

def ajouter_categorie(nouvelle_categorie):
    df = lire_categories_paiement()
    if nouvelle_categorie in df['Categorie'].values:
        raise ValueError("La catégorie existe déjà")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle_categorie}])], ignore_index=True)
    enregistrer_categories_paiement(df)

def supprimer_categorie(categorie):
    df = lire_categories_paiement()
    df = df[df['Categorie'] != categorie]
    enregistrer_categories_paiement(df)

def modifier_categorie(ancienne, nouvelle):
    df = lire_categories_paiement()
    if nouvelle in df['Categorie'].values and nouvelle != ancienne:
        raise ValueError("La nouvelle catégorie existe déjà")
    df.loc[df['Categorie'] == ancienne, 'Categorie'] = nouvelle
    enregistrer_categories_paiement(df)



def enregistrer_commentaire(nom_classe, etudiant, commentaire, auteur=None):
    if not os.path.exists(COMMENTS_DIR):
        os.makedirs(COMMENTS_DIR)

    if os.path.exists(COMMENTS_FILE):
        df = pd.read_excel(COMMENTS_FILE, header=0)
        df.columns = df.columns.str.strip()
    else:
        df = pd.DataFrame(columns=["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"])

    colonnes_necessaires = ["NomClasse", "Etudiant", "Commentaire"]
    if not all(col in df.columns for col in colonnes_necessaires):
        df = pd.DataFrame(columns=colonnes_necessaires + ["Auteur", "Date"])

    condition = (df["NomClasse"] == nom_classe) & (df["Etudiant"] == etudiant)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if condition.any():
        idx = df.index[condition][0]
        df.at[idx, "Commentaire"] = commentaire
        if auteur is not None:
            df.at[idx, "Auteur"] = auteur
        df.at[idx, "Date"] = now_str
    else:
        nouvelle_ligne = {
            "NomClasse": nom_classe,
            "Etudiant": etudiant,
            "Commentaire": commentaire,
            "Auteur": auteur if auteur is not None else "",
            "Date": now_str,
        }
        df = pd.concat([df, pd.DataFrame([nouvelle_ligne])], ignore_index=True)

    df.to_excel(COMMENTS_FILE, index=False)


CATS_DEPENSE_FILE = os.path.join(DATA_FOLDER, "categories_depense.xlsx")

def lire_categories_depense():
    # Création du dossier data si besoin (sécuriser)
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    # Vérifier si le fichier existe
    if not os.path.exists(CATS_DEPENSE_FILE):
        # Création d'un DataFrame vide avec la colonne "Categorie"
        df_vide = pd.DataFrame(columns=["Categorie"])
        # Sauvegarder ce fichier Excel vide
        df_vide.to_excel(CATS_DEPENSE_FILE, index=False)
        return df_vide

    # Si le fichier existe, le lire normalement
    return pd.read_excel(CATS_DEPENSE_FILE)



def lire_categories_paiement():
    # Création du dossier data si absent
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    if not os.path.exists(CATEGORIES_PAIEMENT_FILE):
        df_vide = pd.DataFrame(columns=["Categorie"])
        df_vide.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)
        return df_vide

    return pd.read_excel(CATEGORIES_PAIEMENT_FILE)

def lire_categories_depense():
    if not os.path.exists(CATS_DEPENSE_FILE):
        df = pd.DataFrame(columns=["Categorie"])
        df.to_excel(CATS_DEPENSE_FILE, index=False)
        return df
    return pd.read_excel(CATS_DEPENSE_FILE)


def ajouter_categorie_paiement(nouvelle_categorie: str):
    df = lire_categories_paiement()
    if nouvelle_categorie in df["Categorie"].values:
        raise ValueError(f"La catégorie de paiement '{nouvelle_categorie}' existe déjà.")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle_categorie}])], ignore_index=True)
    df.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)

def ajouter_categorie_depense(nouvelle_categorie: str):
    df = lire_categories_depense()
    if nouvelle_categorie in df["Categorie"].values:
        raise ValueError(f"La catégorie de dépense '{nouvelle_categorie}' existe déjà.")
    df = pd.concat([df, pd.DataFrame([{"Categorie": nouvelle_categorie}])], ignore_index=True)
    df.to_excel(CATS_DEPENSE_FILE, index=False)

def modifier_categorie_paiement(ancienne_categorie: str, nouvelle_categorie: str):
    df = lire_categories_paiement()
    if ancienne_categorie not in df["Categorie"].values:
        raise ValueError(f"La catégorie de paiement '{ancienne_categorie}' n'existe pas.")
    if nouvelle_categorie in df["Categorie"].values:
        raise ValueError(f"La catégorie de paiement '{nouvelle_categorie}' existe déjà.")
    df.loc[df["Categorie"] == ancienne_categorie, "Categorie"] = nouvelle_categorie
    df.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)

def modifier_categorie_depense(ancienne_categorie: str, nouvelle_categorie: str):
    df = lire_categories_depense()
    if ancienne_categorie not in df["Categorie"].values:
        raise ValueError(f"La catégorie de dépense '{ancienne_categorie}' n'existe pas.")
    if nouvelle_categorie in df["Categorie"].values:
        raise ValueError(f"La catégorie de dépense '{nouvelle_categorie}' existe déjà.")
    df.loc[df["Categorie"] == ancienne_categorie, "Categorie"] = nouvelle_categorie
    df.to_excel(CATS_DEPENSE_FILE, index=False)

def supprimer_categorie_paiement(categorie: str):
    df = lire_categories_paiement()
    if categorie not in df["Categorie"].values:
        raise ValueError(f"La catégorie de paiement '{categorie}' n'existe pas.")
    df = df[df["Categorie"] != categorie]
    df.to_excel(CATEGORIES_PAIEMENT_FILE, index=False)

def supprimer_categorie_depense(categorie: str):
    df = lire_categories_depense()
    if categorie not in df["Categorie"].values:
        raise ValueError(f"La catégorie de dépense '{categorie}' n'existe pas.")
    df = df[df["Categorie"] != categorie]
    df.to_excel(CATS_DEPENSE_FILE, index=False)


@app.route("/classe/<nom_classe>/modifier_etudiant/<etudiant>", methods=["GET", "POST"])
def modifier_etudiant(nom_classe, etudiant):
    df_classes = lire_classes()
    df_comments = lire_comments()

    commentaire = ""

    # Vérifier colonnes et extraire commentaire existant
    colonnes_attendues = {"NomClasse", "Etudiant", "Commentaire"}
    if colonnes_attendues.issubset(df_comments.columns):
        comm_row = df_comments[(df_comments["NomClasse"] == nom_classe) & (df_comments["Etudiant"] == etudiant)]
        if not comm_row.empty:
            commentaire = comm_row.iloc[0]["Commentaire"]

    if request.method == "POST":
        nouveau_nom = request.form["nom"].strip()
        nouveau_commentaire = request.form["commentaire"].strip()

        if not nouveau_nom:
            flash("Le nom de l'étudiant ne peut pas être vide.", "error")
            return redirect(request.url)

        # Mise à jour nom dans classes.xlsx
        idx = df_classes[(df_classes["NomClasse"] == nom_classe) & (df_classes["Etudiant"] == etudiant)].index
        if len(idx) == 0:
            flash("Étudiant introuvable.", "error")
            return redirect(url_for("detail_classe", nom_classe=nom_classe))

        df_classes.loc[idx[0], "Etudiant"] = nouveau_nom
        df_classes.to_excel(CLASSES_FILE, index=False)

        # Mise à jour commentaire
        enregistrer_commentaire(nom_classe, nouveau_nom, nouveau_commentaire)

        flash("Étudiant modifié avec succès.", "success")
        return redirect(url_for("detail_classe", nom_classe=nom_classe))

    # Pour GET, passez la variable commentaire au template
    return render_template("modifier_etudiant.html",
                           nom_classe=nom_classe,
                           ancien_nom=etudiant,
                           commentaire=commentaire)


@app.route("/depenses/examen/")
def choisir_classe_depenses_examen():
    df_classes = lire_classes()  # votre fonction pour lire classes.xlsx
    classes = sorted(df_classes["NomClasse"].drop_duplicates().tolist())
    return render_template("choisir_classe_depenses_examen.html", classes=classes)


@app.route("/depenses/examen/<nom_classe>")
def liste_depenses_examen(nom_classe):
    df_depenses = lire_depenses()
    df_cours = lire_cours()

    # Récupérer le paramètre optionnel pour choix d'affichage
    group_by_cours = request.args.get("group_by_cours", "true").lower() == "true"

    # Filtrer les cours de la classe
    cours_classe = df_cours[df_cours["NomClasse"] == nom_classe]["NomCours"].tolist()

    if not cours_classe:
        if group_by_cours:
            cours_depenses = []
            page = 1
            total_pages = 0
            return render_template("liste_depenses_par_cours.html",
                                   cours_depenses=cours_depenses,
                                   titre=f"Dépenses liées aux examens - Classe {nom_classe}",
                                   nom_classe=nom_classe,
                                   page=page,
                                   total_pages=total_pages)
        else:
            depenses_page = []
            page = 1
            total_pages = 0
            return render_template("liste_depenses.html",
                                   depenses=depenses_page,
                                   titre=f"Dépenses liées aux examens - Classe {nom_classe}",
                                   nom_classe=nom_classe,
                                   page=page,
                                   total_pages=total_pages)

    # Filtrer les dépenses pour ces cours (liées aux examens)
    df_filtre = df_depenses[df_depenses["NomCours"].isin(cours_classe) & df_depenses["NomCours"].notna() & (df_depenses["NomCours"] != "")]

    # Recherche optionnelle : description ou catégorie
    recherche = request.args.get("recherche", "").strip().lower()
    if recherche:
        df_filtre = df_filtre[df_filtre.apply(
            lambda row: recherche in str(row["Description"]).lower() or recherche in str(row["CategorieDepense"]).lower(),
            axis=1)]

    page = request.args.get("page", 1, type=int)

    if group_by_cours:
        # Grouper par cours les dépenses
        grouped = df_filtre.groupby("NomCours")
        cours_depenses = []
        for cours, group in grouped:
            depenses_liste = group.to_dict(orient="records")
            cours_depenses.append({
                "NomCours": cours,
                "Depenses": depenses_liste
            })

        per_page = 10
        total = len(cours_depenses)
        total_pages = (total + per_page - 1) // per_page
        if page < 1: page = 1
        if page > total_pages and total_pages > 0: page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        cours_depenses = cours_depenses[start:end]

        return render_template("liste_depenses_par_cours.html",
                               cours_depenses=cours_depenses,
                               titre=f"Dépenses liées aux examens - Classe {nom_classe}",
                               nom_classe=nom_classe,
                               page=page,
                               total_pages=total_pages)
    else:
        # Affichage simple liste plate
        per_page = 15
        total = len(df_filtre)
        total_pages = (total + per_page - 1) // per_page
        if page < 1: page = 1
        if page > total_pages and total_pages > 0: page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        depenses_page = df_filtre.iloc[start:end].to_dict(orient="records")

        return render_template("liste_depenses.html",
                               depenses=depenses_page,
                               titre=f"Dépenses liées aux examens - Classe {nom_classe}",
                               nom_classe=nom_classe,
                               page=page,
                               total_pages=total_pages)



@app.route('/ajouter_recette', methods=['GET', 'POST'])
def ajouter_recette():
    if request.method == 'POST':
        try:
            type_recette = request.form.get('type_recette')
            montant = float(request.form.get('montant'))
            description = request.form.get('description')
            nom_classe = request.form.get('nom_classe', '')  # si vous avez ce champ dans le formulaire
            etudiant = request.form.get('etudiant', '')  # optionnel ou vide si recette générale
            date = datetime.now().strftime("%Y-%m-%d")

            if montant <= 0:
                flash("Le montant doit être supérieur à zéro.", "error")
                return redirect(url_for('ajouter_recette'))

            # Enregistrer dans le fichier dédié aux autres recettes
            enregistrer_autre_recette(nom_classe, etudiant, type_recette, montant, description, date)
            
            flash("Recette ajoutée avec succès.", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Erreur lors de l'ajout de la recette : {e}", "error")
            return redirect(url_for('ajouter_recette'))

    return render_template('ajouter_recette.html')

from flask import flash

@app.route("/categories_paiement", methods=["GET", "POST"])
def gerer_categories_paiement():
    # Lecture des catégories paiement et dépense (adaptation selon votre propre fonction)
    df_cats_paiement = lire_categories_paiement()   # Doit retourner ces catégories
    df_cats_depense = lire_categories_depense()     # À adapter ou créer si besoin

    if request.method == "POST":
        action = request.form.get("action")
        type_categorie = request.form.get("type_categorie", "").strip().lower()

        if not type_categorie in ["paiement", "depense"]:
            flash("Le type de catégorie est invalide.", "error")
            # Recharger les listes après flash
            categories_paiement = df_cats_paiement['Categorie'].dropna().tolist()
            categories_depense = df_cats_depense['Categorie'].dropna().tolist()
            return render_template("gerer_categories_paiement.html",
                                   categories_paiement=categories_paiement,
                                   categories_depense=categories_depense)

        if action == "ajouter":
            nouvelle_categorie = request.form.get("nouvelle_categorie", "").strip()
            if not nouvelle_categorie:
                flash("Le nom de la catégorie est requis.", "error")
            else:
                try:
                    if type_categorie == "paiement":
                        ajouter_categorie_paiement(nouvelle_categorie)
                    else:
                        ajouter_categorie_depense(nouvelle_categorie)
                    flash(f"Catégorie '{nouvelle_categorie}' ajoutée avec succès.", "success")
                    return redirect(url_for("gerer_categories_paiement"))
                except ValueError as e:
                    flash(str(e), "error")

        elif action == "modifier":
            ancienne = request.form.get("ancienne_categorie", "").strip()
            nouvelle = request.form.get("nouvelle_categorie_modif", "").strip()
            if not ancienne or not nouvelle:
                flash("Les deux noms de catégorie sont requis.", "error")
            else:
                try:
                    if type_categorie == "paiement":
                        modifier_categorie_paiement(ancienne, nouvelle)
                    else:
                        modifier_categorie_depense(ancienne, nouvelle)
                    flash(f"Catégorie '{ancienne}' modifiée en '{nouvelle}'.", "success")
                    return redirect(url_for("gerer_categories_paiement"))
                except ValueError as e:
                    flash(str(e), "error")

        elif action == "supprimer":
            categorie = request.form.get("categorie_suppr", "").strip()
            if not categorie:
                flash("La catégorie à supprimer est requise.", "error")
            else:
                try:
                    if type_categorie == "paiement":
                        supprimer_categorie_paiement(categorie)
                    else:
                        supprimer_categorie_depense(categorie)
                    flash(f"Catégorie '{categorie}' supprimée.", "success")
                    return redirect(url_for("gerer_categories_paiement"))
                except ValueError as e:
                    flash(str(e), "error")

    # En GET ou en cas d’erreur, on re-lit les listes à jour
    categories_paiement = df_cats_paiement['Categorie'].dropna().tolist()
    categories_depense = df_cats_depense['Categorie'].dropna().tolist()

    return render_template(
        "gerer_categories_paiement.html",
        categories_paiement=categories_paiement,
        categories_depense=categories_depense
    )



# Exemple de définition globale dans le module (à mettre au-dessus des routes)
CATEGORIES_TRAVAUX = {
    "Mémoire": [
        {"nom": "Paiement jury de soutenance", "commentaire_label": "Date de soutenance"},
        {"nom": "Paiement direction du travail", "commentaire_label": "Nom du directeur"},
        {"nom": "Paiement encadrement", "commentaire_label": "Nom de l'encadreur"}
    ],
    "Travaux tutorés": [
        {"nom": "Paiement jury de soutenance", "commentaire_label": "Date de soutenance"},
        {"nom": "Paiement encadrement", "commentaire_label": "Nom de l'encadreur"}
    ],
    "Stage": [
        {"nom": "Correction rapport de stage", "commentaire_label": "Commentaires"}
    ]
}

@app.route("/classe/<nom_classe>/ajouter_depense_travail", methods=["GET", "POST"])
def ajouter_depense_travail(nom_classe):
    df_classes = lire_classes()
    etudiants = df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"].drop_duplicates().tolist()

    # Gestion de la recherche côté serveur (paramètre GET "recherche")
    recherche = request.args.get("recherche", "").strip().lower()
    if recherche:
        etudiants = [e for e in etudiants if recherche in e.lower()]

    categories = list(CATEGORIES_TRAVAUX.keys())

    if request.method == "POST":
        etudiant = request.form.get("etudiant", "").strip()
        categorie_travail = request.form.get("categorie_travail", "").strip()
        depense = request.form.get("depense", "").strip()
        commentaire = request.form.get("commentaire", "").strip()
        montant_raw = request.form.get("montant", "").strip()
        date_depense = request.form.get("date_depense", "").strip()

        erreurs = []

        # Validation étudiante
        if etudiant not in etudiants:
            erreurs.append("Étudiant invalide ou non sélectionné.")

        # Validation catégorie
        if categorie_travail not in categories:
            erreurs.append("Catégorie de travail invalide.")

        # Validation dépense (doit exister dans la catégorie choisie)
        depenses_valides = [d['nom'] for d in CATEGORIES_TRAVAUX.get(categorie_travail, [])]
        if depense not in depenses_valides:
            erreurs.append("Dépense sélectionnée invalide.")

        # Montant valide
        try:
            montant = float(montant_raw)
            if montant <= 0:
                erreurs.append("Le montant doit être supérieur à zéro.")
        except ValueError:
            erreurs.append("Montant invalide.")

        # Date obligatoire
        if not date_depense:
            erreurs.append("La date de la dépense est obligatoire.")

        if erreurs:
            for err in erreurs:
                flash(err, "error")
            # Re-rendu du formulaire avec données remplies
            return render_template(
                "ajouter_depense_travail.html",
                nom_classe=nom_classe,
                etudiants=etudiants,
                categories=categories,
                depenses=CATEGORIES_TRAVAUX.get(categorie_travail, []),
                etudiant_selectionne=etudiant,
                categorie_selectionnee=categorie_travail,
                depense_selectionnee=depense,
                commentaire_valeur=commentaire,
                montant_valeur=montant_raw,
                date_depense_valeur=date_depense,
                recherche=recherche,
                CATEGORIES_TRAVAUX=CATEGORIES_TRAVAUX  # Passez toujours pour tojson
            )

        # Construction des données à enregistrer
        data = {
            "NomClasse": nom_classe,
            "Etudiant": etudiant,
            "CategorieTravail": categorie_travail,
            "TypeDepense": depense,
            "Commentaire": commentaire,
            "Montant": montant,
            "DateDepense": date_depense
        }

        # Enregistrement (fonction à implémenter ou adapter)
        try:
            enregistrer_depense_travail(data)  # A créer ou utiliser selon votre logique
            flash("Dépense de travail ajoutée avec succès !", "success")
            return redirect(url_for("detail_classe", nom_classe=nom_classe))
        except Exception as e:
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "error")
            # Re-rendu formulaire en cas d’erreur
            return render_template(
                "ajouter_depense_travail.html",
                nom_classe=nom_classe,
                etudiants=etudiants,
                categories=categories,
                depenses=CATEGORIES_TRAVAUX.get(categorie_travail, []),
                etudiant_selectionne=etudiant,
                categorie_selectionnee=categorie_travail,
                depense_selectionnee=depense,
                commentaire_valeur=commentaire,
                montant_valeur=montant_raw,
                date_depense_valeur=date_depense,
                recherche=recherche,
                CATEGORIES_TRAVAUX=CATEGORIES_TRAVAUX
            )

    # En GET, formulaire vierge, catégorie par défaut vide, avec possibilité d’avoir une recherche
    return render_template(
        "ajouter_depense_travail.html",
        nom_classe=nom_classe,
        etudiants=etudiants,
        categories=categories,
        depenses=[],
        recherche=recherche,
        CATEGORIES_TRAVAUX=CATEGORIES_TRAVAUX
    )



if __name__ == "__main__":
    init_excel()
    init_classes_excel()
    init_paiements_excel()
    init_depenses_excel()
    init_cours_excel()

    port = 5008  # Ou votre port souhaité

    # Ouvrir le navigateur dans un thread séparé pour ne pas bloquer Flask
    def open_browser():
        webbrowser.open_new(f"http://127.0.0.1:{port}")

    threading.Timer(1.0, open_browser).start()  # délai léger pour laisser le serveur démarrer

    app.run(debug=False, port=port)