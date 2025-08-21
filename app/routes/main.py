import os
import pandas as pd
from flask import Flask, Blueprint, render_template, request
from ..models.storage import (
    lire_paiements, lire_autres_recettes, lire_depenses,
    lire_classes, lire_recettes
)
from app.routes.auth import auth_bp, login_required  # Décorateur custom session

# Création de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "UneChaineComplexeUniqueEtSecrete123!")

# Enregistrement du blueprint auth
app.register_blueprint(auth_bp)

# Blueprint principal
main_bp = Blueprint("main", __name__, template_folder="../templates")


def paginate_list(data_list, page, per_page=20):
    """Pagination générique pour n'importe quelle liste de dicts."""
    total = len(data_list)
    total_pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    return data_list[start:end], page, total_pages


def safe_sum(df, col):
    """Somme sécurisée si la colonne existe."""
    return df[col].sum() if col in df.columns else 0


@main_bp.route("/")
@login_required
def index():
    """Tableau de bord principal."""
    df_paiements = lire_paiements()
    df_autres_recettes = lire_autres_recettes()
    df_depenses = lire_depenses()
    df_classes = lire_classes()
    df_recettes = lire_recettes()

    # Paiements complets
    df_paiements_complets = pd.concat([df_paiements, df_autres_recettes], ignore_index=True)

    total_paiements = safe_sum(df_paiements_complets, "Montant")
    total_depenses = safe_sum(df_depenses, "Montant")
    solde = total_paiements - total_depenses

    # Dépenses examens / autres
    if "NomCours" in df_depenses.columns:
        depenses_examen = df_depenses[df_depenses["NomCours"].notna() & (df_depenses["NomCours"] != "")]
        total_depenses_examen = safe_sum(depenses_examen, "Montant")

        depenses_autres = df_depenses[df_depenses["NomCours"].isna() | (df_depenses["NomCours"] == "")]
        total_depenses_autres = safe_sum(depenses_autres, "Montant")
    else:
        total_depenses_examen = 0
        total_depenses_autres = 0

    # Infos par classe
    classes_info = []
    if not df_classes.empty and "NomClasse" in df_classes.columns:
        classes = df_classes["NomClasse"].drop_duplicates().tolist()
        for classe in classes:
            etudiants = df_classes[df_classes["NomClasse"] == classe]["Etudiant"].drop_duplicates().tolist()
            paiements_classe = df_paiements_complets[df_paiements_complets["NomClasse"] == classe] if not df_paiements_complets.empty else pd.DataFrame()
            paiements_par_categorie = {}

            if not paiements_classe.empty and "CategoriePaiement" in paiements_classe.columns:
                for cat in paiements_classe["CategoriePaiement"].drop_duplicates():
                    nb_etudiants = len(paiements_classe[paiements_classe["CategoriePaiement"] == cat]["Etudiant"].drop_duplicates())
                    paiements_par_categorie[cat] = nb_etudiants

            classes_info.append({
                "classe": classe,
                "total_etudiants": len(etudiants),
                "paiements_par_categorie": paiements_par_categorie
            })

    return render_template(
        "index.html",
        solde=round(solde, 2),
        total_depenses_examen=round(total_depenses_examen, 2),
        total_depenses_autres=round(total_depenses_autres, 2),
        classes_info=classes_info
    )


@main_bp.route("/historique")
@login_required
def historique():
    """Historique des opérations : dépenses et recettes."""
    recherche = request.args.get("recherche", "").strip().lower()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    df_depenses = lire_depenses()
    df_recettes = lire_recettes()

    # Filtre recherche
    def filter_df(df, recherche):
        if recherche and not df.empty:
            return df[df.apply(lambda row: recherche in ' '.join(str(row[col]).lower() for col in df.columns if pd.notna(row[col])), axis=1)]
        return df

    df_depenses_filtered = filter_df(df_depenses, recherche)
    df_recettes_filtered = filter_df(df_recettes, recherche)

    # Séparation travaux / dépenses classiques
    df_travaux = df_depenses_filtered[df_depenses_filtered.get("CategorieDepense", "").str.contains("Travail", na=False, case=False)]
    df_depenses_classiques = df_depenses_filtered[~df_depenses_filtered.get("CategorieDepense", "").str.contains("Travail", na=False, case=False)]

    operations_caisse = df_depenses_filtered.to_dict(orient="records")
    depenses_classiques = df_depenses_classiques.to_dict(orient="records")
    depenses_travaux = df_travaux.to_dict(orient="records")
    recettes = df_recettes_filtered.to_dict(orient="records")

    operations_page, page, total_pages = paginate_list(operations_caisse, page, per_page)

    # Totaux
    total_caisse = safe_sum(df_depenses_filtered, "Montant")
    total_depenses_classiques = safe_sum(df_depenses_classiques, "Montant")
    total_travaux = safe_sum(df_travaux, "Montant")
    total_recettes = safe_sum(df_recettes_filtered, "Montant")
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


# Enregistrement du blueprint main_bp
app.register_blueprint(main_bp)
