import pandas as pd
from flask import Blueprint, render_template, request, url_for
from app.routes.auth import login_required  # juste le décorateur
from app.models import storage_gsheets as storage  # ✅ Google Sheets uniquement
from app.models.storage_gsheets import (
    lire_paiements_inscriptions,
    total_paiements_travaux,  # Importez ceci
    # autres fonctions...
)



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
    # Lire les données de Google Sheets via vos fonctions
    df_classes = storage.lire_classes()

    df_recettes = storage.lire_recettes()
    df_autres_recettes = storage.lire_autres_recettes()
    df_paiements_inscriptions = lire_paiements_inscriptions()

    df_depenses_list = [storage.lire_depenses()]
    df_depenses = concat_or_empty(df_depenses_list, [
        "ID", "NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description",
        "Montant", "TypeDepense", "Commentaire", "DateDepense"
    ])

    # Combine recettes hors paiements inscriptions
    df_recettes_complet = concat_or_empty([df_recettes, df_autres_recettes], [
        "ID", "NomClasse", "Etudiant", "Type", "Montant", "Description", "Date", "Utilisateur"
    ])

    # Totaux
    total_recettes_normales = safe_sum(df_recettes, "Montant")
    total_autres_recettes = safe_sum(df_autres_recettes, "Montant")
    total_paiements_inscriptions = safe_sum(df_paiements_inscriptions, "Montant")

    # Calcul total paiements travaux - attention à ne pas utiliser le même nom que la fonction
    total_paiements_travaux_valeur = total_paiements_travaux()

    total_depenses = safe_sum(df_depenses, "Montant")

    # Calcul du solde en ajoutant le total des paiements travaux
    solde = (
        total_recettes_normales
        + total_autres_recettes
        + total_paiements_inscriptions
        + total_paiements_travaux_valeur  # <-- Ajout ici
        - total_depenses
    )

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

    # Passer toutes ces variables au template
    return render_template(
        "index.html",
        solde=round(solde, 2),
        total_recettes_normales=round(total_recettes_normales, 2),
        total_paiements_inscriptions=round(total_paiements_inscriptions, 2),
        total_autres_recettes=round(total_autres_recettes, 2),
        total_depenses_examen=round(total_depenses_examen, 2),
        total_depenses_autres=round(total_depenses_autres, 2),
        classes_info=classes_info,
        total_paiements_travaux=round(total_paiements_travaux_valeur, 2),  # <-- Variable renommée pour éviter conflit
    )





@main_bp.route("/historique")
@login_required
def historique():
    recherche = request.args.get("recherche", "").strip().lower()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Charger les données des dépenses
    df_depenses_list = [storage.lire_depenses()]
    df_depenses = concat_or_empty(df_depenses_list, [
        "ID", "NomClasse", "NomCours", "DateExamen", "CategorieDepense", "Description",
        "Montant", "TypeDepense", "Commentaire", "DateDepense"
    ])

    # Charger les recettes : recettes, paiements inscriptions, autres recettes
    recettes_list = [storage.lire_recettes(), storage.lire_paiements(), storage.lire_autres_recettes()]
    df_recettes_complet = concat_or_empty(recettes_list, [
        "ID", "NomClasse", "Etudiant", "Type", "Montant", "Description", "Date", "Utilisateur"
    ])

    # Lire inscriptions et paiements travaux (à adapter fonctions selon projet)
    df_inscriptions = storage.lire_inscriptions()
    df_paiements_travaux = storage.lire_paiements_travaux()

    # Concaténer inscriptions et paiements travaux dans opérations caisse
    df_operations_supplementaires = concat_or_empty([df_inscriptions, df_paiements_travaux], [
        "ID", "NomClasse", "Etudiant", "TypeInscription", "TypeTravail", "StatutPaiement", "Montant", "DatePaiement"
    ])

    # Concaténer toutes les opérations caisse
    df_operations_caisse = concat_or_empty([df_depenses, df_operations_supplementaires], [
        "ID", "NomClasse", "Etudiant", "TypeInscription", "TypeTravail", "CategorieDepense",
        "StatutPaiement", "Montant", "DatePaiement", "Description", "TypeDepense", "DateDepense"
    ])

    # Fonction filtre recherche
    def filter_df(df, recherche):
        if recherche and not df.empty:
            return df[df.apply(
                lambda row: recherche in " ".join(
                    str(row[col]).lower() for col in df.columns if pd.notna(row[col])
                ),
                axis=1
            )]
        return df

    df_operations_filtered = filter_df(df_operations_caisse, recherche)
    df_recettes_filtered = filter_df(df_recettes_complet, recherche)

    # Séparer travaux / dépenses classiques dans les opérations
    df_travaux = df_operations_filtered[
        df_operations_filtered.get("CategorieDepense", "").str.contains("Travail", na=False, case=False)
    ]
    df_depenses_classiques = df_operations_filtered[
        ~df_operations_filtered.get("CategorieDepense", "").str.contains("Travail", na=False, case=False)
    ]

    # Pagination
    operations_page, page, total_pages = paginate_list(
        df_operations_filtered.to_dict(orient="records"), page, per_page
    )

    # Conversion dict pour le template
    depenses_classiques = df_depenses_classiques.to_dict(orient="records")
    depenses_travaux = df_travaux.to_dict(orient="records")
    recettes = df_recettes_filtered.to_dict(orient="records")
    inscriptions = df_inscriptions.to_dict(orient="records")
    paiements_travaux = df_paiements_travaux.to_dict(orient="records")

    # Totaux
    total_caisse = safe_sum(df_operations_filtered, "Montant")
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
        inscriptions=inscriptions,
        paiements_travaux=paiements_travaux,
        page=page,
        total_pages=total_pages,
        total_caisse=total_caisse,
        total_depenses_classiques=total_depenses_classiques,
        total_travaux=total_travaux,
        total_recettes=total_recettes,
        solde=solde,
        recherche=recherche,
    )

