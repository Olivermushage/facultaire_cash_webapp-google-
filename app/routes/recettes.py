import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.routes.auth import login_required
from ..models.storage import (
    lire_recettes, lire_categories_paiement,
    enregistrer_autre_recette
)

recettes_bp = Blueprint('recettes', __name__, template_folder='templates/recettes')

# ==========================
# Helpers
# ==========================

def paginate(items, page, per_page=15):
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

@recettes_bp.route('/')
@login_required
def index_recettes():
    try:
        df_recettes = lire_recettes()
        if df_recettes.empty:
            recettes_list = []
        else:
            recettes_list = df_recettes.to_dict(orient="records")

        recherche = request.args.get("recherche", "").strip().lower()
        if recherche:
            recettes_list = [
                r for r in recettes_list
                if recherche in (r.get('Description') or '').lower()
                or recherche in (r.get('Source') or '').lower()
                or recherche in (r.get('Type') or '').lower()
            ]

        page = request.args.get("page", 1, type=int)
        recettes_page, page, total_pages = paginate(recettes_list, page, 15)

        return render_template(
            'liste_recettes.html',
            recettes=recettes_page,
            page=page,
            total_pages=total_pages,
            titre="Liste des recettes"
        )
    except Exception:
        logging.exception("Erreur lors de l'affichage des recettes")
        flash("Impossible d'afficher les recettes.", "error")
        return redirect(url_for('recettes.index_recettes'))


@recettes_bp.route('/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_recette():
    try:
        df_categories = lire_categories_paiement()
        categories = df_categories.get('Categorie', []).dropna().tolist()
    except Exception:
        logging.exception("Erreur lecture catégories recettes")
        categories = []

    if request.method == 'POST':
        type_recette = request.form.get('type_recette', '').strip()
        montant_raw = request.form.get('montant', '').strip()
        description = request.form.get('description', '').strip()
        commentaire = request.form.get('commentaire', '').strip()
        nom_classe = request.form.get('nom_classe', '').strip()
        etudiant = request.form.get('etudiant', '').strip()
        categorie = request.form.get('categorie', '').strip() if type_recette == "standard" else None

        erreurs = []

        # Validation du type
        if type_recette not in ["standard", "manuelle"]:
            erreurs.append("Le type de recette sélectionné n'est pas valide.")

        # Validation de la catégorie si standard
        if type_recette == "standard":
            if not categorie:
                erreurs.append("Une catégorie est requise pour une recette standard.")
            elif categories and categorie not in categories:
                erreurs.append(f"La catégorie '{categorie}' n'est pas valide.")

        # Validation du montant
        try:
            montant = validate_montant(montant_raw)
        except ValueError as ve:
            erreurs.append(str(ve))

        if erreurs:
            for err in erreurs:
                flash(err, "error")
            return render_template(
                'ajouter_recette.html',
                categories=categories,
                titre="Ajouter une recette",
                type_recette_valeur=type_recette,
                montant_valeur=montant_raw,
                description_valeur=description,
                commentaire_valeur=commentaire,
                nom_classe_valeur=nom_classe,
                etudiant_valeur=etudiant
            )

        date = datetime.now().strftime("%Y-%m-%d")
        utilisateur = session.get("username", "inconnu")  # ✅ utilisation de session à la place de current_user

        try:
            if type_recette == "standard":
                description_finale = categorie
            else:
                description_finale = description or "Recette manuelle"

            # Inclure le commentaire si fourni
            details = description_finale
            if commentaire:
                details += f" | Commentaire : {commentaire}"

            enregistrer_autre_recette(
                nom_classe, etudiant, type_recette, montant,
                details, date, utilisateur
            )
            flash("Recette ajoutée avec succès.", "success")
            return redirect(url_for('recettes.index_recettes'))
        except Exception as e:
            logging.exception("Erreur lors de l'ajout de la recette")
            flash(f"Erreur lors de l'ajout : {str(e)}", "error")
            return redirect(url_for('recettes.ajouter_recette'))

    # GET
    return render_template(
        'ajouter_recette.html',
        categories=categories,
        titre="Ajouter une recette"
    )


@recettes_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def gerer_categories_recette():
    try:
        df_categories = lire_categories_paiement()
        categories = df_categories.get('Categorie', []).dropna().tolist()
    except Exception:
        logging.exception("Erreur lecture catégories recettes")
        categories = []

    if request.method == "POST":
        action = request.form.get("action")
        nom_categorie = request.form.get("nom_categorie", "").strip()
        ancienne_categorie = request.form.get("ancienne_categorie", "").strip()
        nouvelle_categorie = request.form.get("nouvelle_categorie", "").strip()

        try:
            from ..models.storage import (
                ajouter_categorie_paiement,
                modifier_categorie_paiement,
                supprimer_categorie_paiement
            )

            if action == "ajouter":
                if not nom_categorie:
                    flash("Le nom de la catégorie est requis.", "error")
                else:
                    ajouter_categorie_paiement(nom_categorie)
                    flash(f"Catégorie '{nom_categorie}' ajoutée avec succès.", "success")

            elif action == "modifier":
                if not ancienne_categorie or not nouvelle_categorie:
                    flash("Le nom actuel et le nouveau nom sont requis.", "error")
                else:
                    modifier_categorie_paiement(ancienne_categorie, nouvelle_categorie)
                    flash(f"Catégorie '{ancienne_categorie}' modifiée en '{nouvelle_categorie}'.", "success")

            elif action == "supprimer":
                if not nom_categorie:
                    flash("Le nom de la catégorie à supprimer est requis.", "error")
                else:
                    supprimer_categorie_paiement(nom_categorie)
                    flash(f"Catégorie '{nom_categorie}' supprimée.", "success")
            else:
                flash("Action inconnue.", "error")

        except Exception as e:
            logging.exception("Erreur gestion catégories recettes")
            flash(str(e), "error")

        return redirect(url_for('recettes.gerer_categories_recette'))

    # GET
    return render_template(
        'gerer_categories_recette.html',
        categories=categories,
        titre="Gérer les catégories de recettes"
    )
