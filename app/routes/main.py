import pandas as pd
from flask import Blueprint, render_template, request, url_for
from app.routes.auth import login_required  # juste le décorateur
from app.models import storage_gsheets as storage  # ✅ Google Sheets uniquement

main_bp = Blueprint("main", __name__, template_folder="../templates")


def paginate_list(data_list, page, per_page=20):
    total = len(data_list)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages or 1))
    start = (page - 1) * per_page
    end = start + per_page
    return data_list[start:end], page, total_pages


def safe_sum(df, col):
    return df[col].sum() if col is not None and col in df.columns else 0


def concat_or_empty(dfs, columns):
    """Concatène les DataFrames ou retourne un DataFrame vide avec les colonnes spécifiées."""
    non_empty_dfs = [df for df in dfs if df is not None and not df.empty]
    if non_empty_dfs:
        return pd.concat(non_empty_dfs, ignore_index=True)
    else:
        return pd.DataFrame(columns=columns)


# ✅ Injection du menu accessible dans tous les templates
@main_bp.app_context_processor
def inject_menu():
    return {
        "menu_actions": [
            {
                "label": "Ajouter une dépense",
                "url": url_for("depenses.ajouter_depense_autres"),
                "endpoint": "depenses.ajouter_depense_autres",
            },
        #   """   {
        #         "label": "Ajouter une classe",
        #         "url": url_for("classes.ajouter_cours"),  # endpoint pour créer une nouvelle classe
        #         "endpoint": "classes.ajouter_cours",
        #     }, """
            # {
            #     "label": "Ajouter un étudiant",
            #     "url": url_for("classes.ajouter_etudiant"),
            #     "endpoint": "classes.ajouter_etudiant",
            # },
            # 🔹 Ne PAS mettre Ajouter cours ici : nécessite nom_classe
        ]
    }



@main_bp.route("/")
@login_required
def index():
    # --- Récupérer toutes les données des feuilles ---
    df_classes = storage.lire_classes()

    # Toutes les recettes
    recettes_list = [storage.lire_recettes(), storage.lire_paiements(), storage.lire_autres_recettes()]
    df_recettes_complet = concat_or_empty(recettes_list, [
        "ID", "NomClasse", "Etudiant", "Type", "Montant", "Description", "Date", "Utilisateur"
    ])

    # Toutes les dépenses
    df_depenses_list = [storage.lire_depenses()]
    df_depenses = concat_or_empty(df_depenses_list, [
        "ID", "NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description",
        "Montant", "TypeDepense", "Commentaire", "DateDepense"
    ])

    # --- Totaux ---
    total_recettes = safe_sum(df_recettes_complet, "Montant")
    total_depenses = safe_sum(df_depenses, "Montant")
    solde = total_recettes - total_depenses

    # Dépenses examens / autres
    if not df_depenses.empty and "NomCours" in df_depenses.columns:
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
        for classe in df_classes["NomClasse"].drop_duplicates().tolist():
            etudiants = df_classes[df_classes["NomClasse"] == classe]["Etudiant"].drop_duplicates().tolist()
            paiements_classe = df_recettes_complet[df_recettes_complet["NomClasse"] == classe] if not df_recettes_complet.empty else pd.DataFrame()

            paiements_par_categorie = {}
            if not paiements_classe.empty and "CategoriePaiement" in paiements_classe.columns:
                for cat in paiements_classe["CategoriePaiement"].drop_duplicates():
                    nb_etudiants = len(
                        paiements_classe[paiements_classe["CategoriePaiement"] == cat]["Etudiant"].drop_duplicates()
                    )
                    paiements_par_categorie[cat] = nb_etudiants

            classes_info.append({
                "classe": classe,
                "total_etudiants": len(etudiants),
                "paiements_par_categorie": paiements_par_categorie,
            })

    return render_template(
        "index.html",
        solde=round(solde, 2),
        total_recettes=round(total_recettes, 2),
        total_depenses_examen=round(total_depenses_examen, 2),
        total_depenses_autres=round(total_depenses_autres, 2),
        classes_info=classes_info,
    )


@main_bp.route("/historique")
@login_required
def historique():
    recherche = request.args.get("recherche", "").strip().lower()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Toutes les données
    df_depenses_list = [storage.lire_depenses()]
    df_depenses = concat_or_empty(df_depenses_list, [
        "ID", "NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description",
        "Montant", "TypeDepense", "Commentaire", "DateDepense"
    ])

    recettes_list = [storage.lire_recettes(), storage.lire_paiements(), storage.lire_autres_recettes()]
    df_recettes_complet = concat_or_empty(recettes_list, [
        "ID", "NomClasse", "Etudiant", "Type", "Montant", "Description", "Date", "Utilisateur"
    ])

    # Filtre recherche
    def filter_df(df, recherche):
        if recherche and not df.empty:
            return df[df.apply(
                lambda row: recherche in " ".join(
                    str(row[col]).lower() for col in df.columns if pd.notna(row[col])
                ),
                axis=1
            )]
        return df

    df_depenses_filtered = filter_df(df_depenses, recherche)
    df_recettes_filtered = filter_df(df_recettes_complet, recherche)

    # Séparation travaux / dépenses classiques
    df_travaux = df_depenses_filtered[
        df_depenses_filtered.get("CategorieDepense", "").str.contains("Travail", na=False, case=False)
    ]
    df_depenses_classiques = df_depenses_filtered[
        ~df_depenses_filtered.get("CategorieDepense", "").str.contains("Travail", na=False, case=False)
    ]

    operations_caisse = df_depenses_filtered.to_dict(orient="records")
    depenses_classiques = df_depenses_classiques.to_dict(orient="records")
    depenses_travaux = df_travaux.to_dict(orient="records")
    recettes = df_recettes_filtered.to_dict(orient="records")

    operations_page, page, total_pages = paginate_list(operations_caisse, page, per_page)

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
        recherche=recherche,
    )
