import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.routes.auth import login_required
from ..models.storage import (
    lire_depenses, lire_cours, lire_categories_depense,
    ajouter_categorie_depense, modifier_categorie_depense, supprimer_categorie_depense,
    enregistrer_depense, enregistrer_cours, lire_classes
)

depenses_bp = Blueprint('depenses', __name__, template_folder='templates/depenses')

# ==========================
# Helpers internes
# ==========================

def paginate(items, page, per_page=15):
    """Retourne slice_items, page_corrigée, total_pages."""
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages or 1))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total_pages


def validate_montant(montant_raw):
    try:
        montant = float(montant_raw)
        if montant <= 0:
            raise ValueError("Le montant doit être supérieur à zéro.")
        return montant
    except Exception:
        raise ValueError("Le montant est invalide.")


# ==========================
# Routes principales
# ==========================

@depenses_bp.route('/')
@login_required
def depenses_index():
    return render_template('depenses.html')


@depenses_bp.route('/autres')
@login_required
def liste_depenses_autres():
    try:
        df = lire_depenses()
        if "NomCours" not in df.columns:
            df["NomCours"] = None
        depenses_autres = df[df["NomCours"].isna() | (df["NomCours"] == "")]
        recherche = request.args.get("recherche", "").strip().lower()

        depenses_list = depenses_autres.to_dict(orient="records")
        if recherche:
            depenses_list = [
                d for d in depenses_list
                if recherche in (d.get('Description') or '').lower()
                or recherche in (d.get('CategorieDepense') or '').lower()
            ]

        page = request.args.get("page", 1, type=int)
        depenses_page, page, total_pages = paginate(depenses_list, page, 15)

        return render_template(
            "liste_depenses.html",
            depenses=depenses_page,
            titre="Autres dépenses",
            nom_classe=None,
            page=page,
            total_pages=total_pages
        )
    except Exception:
        logging.exception("Erreur lors de l'affichage des autres dépenses")
        flash("Impossible d'afficher les autres dépenses.", "error")
        return redirect(url_for("depenses.depenses_index"))


@depenses_bp.route('/ajouter_examen/<nom_classe>', methods=['GET', 'POST'])
@login_required
def ajouter_depense_examen(nom_classe):
    categories = ["Paiement surveillance", "Paiement correction", "Paiement envoi copie", "Autre"]
    df_cours = lire_cours()
    if "NomClasse" not in df_cours.columns or "NomCours" not in df_cours.columns:
        df_cours["NomClasse"] = df_cours["NomCours"] = None
    cours_classe = df_cours[df_cours["NomClasse"] == nom_classe]["NomCours"].dropna().tolist()

    if request.method == "POST":
        cat = request.form.get("categorie", "").strip()
        categorie_autre = request.form.get("categorie_autre", "").strip()
        nom_cours = request.form.get("nom_cours", "").strip()
        date_examen = request.form.get("date_examen", "").strip()
        description = request.form.get("description", "").strip()
        montant_raw = request.form.get("montant", "").strip()

        erreurs = []
        if not nom_cours:
            erreurs.append("Le cours est obligatoire.")
        elif nom_cours not in cours_classe:
            erreurs.append("Le cours sélectionné est invalide.")

        if not cat:
            erreurs.append("La catégorie de dépense est obligatoire.")
        elif cat == "Autre":
            if not categorie_autre:
                erreurs.append("Merci de préciser la catégorie 'Autre'.")
            else:
                cat = categorie_autre

        if not date_examen:
            erreurs.append("La date de l'examen est obligatoire.")

        try:
            montant = validate_montant(montant_raw)
        except ValueError as ve:
            erreurs.append(str(ve))

        if erreurs:
            for err in erreurs:
                flash(err, "error")
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

        data = {
            "NomClasse": nom_classe,
            "NomCours": nom_cours,
            "DateExamen": date_examen,
            "CategorieDepense": cat,
            "Description": description,
            "Montant": montant,
            "TypeDepense": "Examen",
            "Commentaire": "",
            "DateDepense": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            enregistrer_depense(data)
            flash("Dépense liée à un examen enregistrée !", "success")
            return redirect(url_for("depenses.liste_depenses_examen", nom_classe=nom_classe))
        except Exception as e:
            logging.exception("Erreur lors de l'enregistrement de la dépense")
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "error")
            return redirect(url_for("depenses.ajouter_depense_examen", nom_classe=nom_classe))

    return render_template("ajouter_depense_examen.html", categories=categories, nom_classe=nom_classe, cours_classe=cours_classe)


@depenses_bp.route('/ajouter_autres', methods=['GET', 'POST'])
@login_required
def ajouter_depense_autres():
    categories = ["Achat fournitures", "Paiement primes", "Autre"]
    if request.method == "POST":
        cat = request.form.get("categorie", "")
        if cat == "Autre":
            cat = request.form.get("categorie_autre", "").strip() or "Autre"

        try:
            montant = validate_montant(request.form.get("montant", "0"))
        except ValueError as ve:
            flash(str(ve), "error")
            return redirect(url_for("depenses.ajouter_depense_autres"))

        data = {
            "NomClasse": "",
            "NomCours": "",
            "DateExamen": "",
            "CategorieDepense": cat,
            "Description": request.form.get("description", "").strip(),
            "Montant": montant,
            "TypeDepense": "Autres",
            "Commentaire": "",
            "DateDepense": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            enregistrer_depense(data)
            flash("Autre dépense enregistrée !", "success")
            return redirect(url_for("depenses.liste_depenses_autres"))
        except Exception as e:
            logging.exception("Erreur lors de l'enregistrement de la dépense")
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "error")
            return redirect(url_for("depenses.ajouter_depense_autres"))

    return render_template("ajouter_depense_autres.html", categories=categories)


@depenses_bp.route('/liste_examen/<nom_classe>')
@login_required
def liste_depenses_examen(nom_classe):
    try:
        df_depenses = lire_depenses()
        df_cours = lire_cours()
        if "NomClasse" not in df_cours.columns or "NomCours" not in df_cours.columns:
            df_cours["NomClasse"] = df_cours["NomCours"] = None
        if "NomClasse" not in df_depenses.columns or "NomCours" not in df_depenses.columns:
            df_depenses["NomClasse"] = df_depenses["NomCours"] = None

        group_by_cours = request.args.get("group_by_cours", "true").lower() == "true"
        recherche = request.args.get("recherche", "").strip().lower()
        page = request.args.get("page", 1, type=int)

        cours_classe = df_cours[df_cours["NomClasse"] == nom_classe]["NomCours"].dropna().tolist()

        df_filtre = df_depenses[
            (df_depenses["NomClasse"] == nom_classe) &
            (df_depenses["NomCours"].isin(cours_classe)) &
            (df_depenses["NomCours"].notna()) &
            (df_depenses["NomCours"] != "")
        ]

        if recherche:
            df_filtre = df_filtre[df_filtre.apply(
                lambda row: recherche in str(row.get("Description", "")).lower() or recherche in str(row.get("CategorieDepense", "")).lower(),
                axis=1
            )]

        if group_by_cours:
            grouped = df_filtre.groupby("NomCours")
            cours_depenses = [{"NomCours": cours, "Depenses": group.to_dict(orient="records")} for cours, group in grouped]
            cours_depenses_page, page, total_pages = paginate(cours_depenses, page, 10)
            return render_template(
                "liste_depenses_par_cours.html",
                cours_depenses=cours_depenses_page,
                titre=f"Dépenses liées aux examens - Classe {nom_classe}",
                nom_classe=nom_classe,
                page=page,
                total_pages=total_pages
            )
        else:
            depenses_page, page, total_pages = paginate(df_filtre.to_dict(orient="records"), page, 15)
            return render_template(
                "liste_depenses.html",
                depenses=depenses_page,
                titre=f"Dépenses liées aux examens - Classe {nom_classe}",
                nom_classe=nom_classe,
                page=page,
                total_pages=total_pages
            )
    except Exception:
        logging.exception("Erreur lors de l'affichage des dépenses examens")
        flash("Impossible d'afficher les dépenses liées aux examens.", "error")
        return redirect(url_for("depenses.depenses_index"))


@depenses_bp.route('/choisir_classe')
@login_required
def choisir_classe_depenses_examen():
    try:
        df_classes = lire_classes()
        if "NomClasse" not in df_classes.columns:
            df_classes["NomClasse"] = []
        classes = sorted(df_classes["NomClasse"].dropna().unique().tolist())
        return render_template("choisir_classe_depenses_examen.html", classes=classes)
    except Exception:
        logging.exception("Erreur lors du choix de classe pour dépenses examen")
        flash("Impossible d'afficher les classes.", "error")
        return redirect(url_for("depenses.depenses_index"))


@depenses_bp.route('/ajouter_cours/<nom_classe>', methods=['GET', 'POST'])
@login_required
def ajouter_cours(nom_classe):
    if request.method == 'POST':
        cours_brut = request.form.get("cours", "")
        liste_cours = [c.strip() for c in cours_brut.splitlines() if c.strip()]
        try:
            for c in liste_cours:
                enregistrer_cours(nom_classe, c)
            flash(f"{len(liste_cours)} cours ajoutés à la classe {nom_classe}.", "success")
        except Exception:
            logging.exception("Erreur lors de l'ajout de cours")
            flash("Impossible d'ajouter les cours.", "error")
        return redirect(url_for("depenses.liste_depenses_examen", nom_classe=nom_classe))
    return render_template("ajouter_cours.html", nom_classe=nom_classe)


@depenses_bp.route('/categorie_gestion', methods=['GET', 'POST'])
@login_required
def gerer_categories_depense():
    try:
        df_cats_depense = lire_categories_depense()
        if "Categorie" not in df_cats_depense.columns:
            df_cats_depense["Categorie"] = []

        if request.method == "POST":
            action = request.form.get("action")
            nom_categorie = request.form.get("nom_categorie", "").strip()

            if action == "ajouter":
                if not nom_categorie:
                    flash("Le nom de la catégorie est requis.", "error")
                else:
                    try:
                        ajouter_categorie_depense(nom_categorie)
                        flash(f"Catégorie '{nom_categorie}' ajoutée.", "success")
                    except ValueError as e:
                        flash(str(e), "error")
            elif action == "modifier":
                ancienne = request.form.get("ancienne_categorie", "").strip()
                nouvelle = request.form.get("nouvelle_categorie", "").strip()
                if not ancienne or not nouvelle:
                    flash("Les deux noms de catégorie sont requis.", "error")
                else:
                    try:
                        modifier_categorie_depense(ancienne, nouvelle)
                        flash(f"Catégorie '{ancienne}' modifiée en '{nouvelle}'.", "success")
                    except ValueError as e:
                        flash(str(e), "error")
            elif action == "supprimer":
                if not nom_categorie:
                    flash("La catégorie à supprimer est requise.", "error")
                else:
                    try:
                        supprimer_categorie_depense(nom_categorie)
                        flash(f"Catégorie '{nom_categorie}' supprimée.", "success")
                    except ValueError as e:
                        flash(str(e), "error")

            return redirect(url_for("depenses.gerer_categories_depense"))

        categories = df_cats_depense["Categorie"].dropna().tolist()
        return render_template("gerer_categories_depense.html", categories=categories)
    except Exception:
        logging.exception("Erreur lors de la gestion des catégories de dépense")
        flash("Impossible de gérer les catégories de dépense.", "error")
        return redirect(url_for("depenses.depenses_index"))
