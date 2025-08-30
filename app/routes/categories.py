import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.routes.auth import login_required, admin_required  # Décorateurs custom
from ..models.storage_gsheets import (
    lire_categories_paiement,
    lire_categories_depense,
    ajouter_categorie_paiement,
    ajouter_categorie_depense,
    modifier_categorie_paiement,
    modifier_categorie_depense,
    supprimer_categorie_paiement,
    supprimer_categorie_depense,
)

categories_bp = Blueprint("categories", __name__, template_folder="../templates")


@categories_bp.route("/categories", methods=["GET", "POST"])
@login_required
@admin_required
def gerer_categories():
    df_p = lire_categories_paiement()
    df_d = lire_categories_depense()

    def normalize_columns(df):
        df.columns = df.columns.astype(str)
        # Nettoyer et normaliser noms colonnes (éliminer accents, espaces)
        df.columns = (
            df.columns.str.strip()
                      .str.normalize('NFKD')
                      .str.encode('ascii', errors='ignore')
                      .str.decode('utf-8')
        )
        # Renommer 'Categorie' sans accent si la colonne originale s'appelle 'Categorie' ou 'Catégorie'
        if 'Categorie' not in df.columns:
            if 'Categorie' not in df.columns and 'Categorie' not in df.columns:
                # Recherche de la colonne avec accent qui deviendra Categorie
                for col in df.columns:
                    if col.lower() == 'categorie':
                        df.rename(columns={col: 'Categorie'}, inplace=True)
                        break
        return df

    df_p = normalize_columns(df_p)
    df_d = normalize_columns(df_d)

    if request.method == "POST":
        action = request.form.get("action")
        type_categorie = request.form.get("type_categorie", "").strip().lower()

        if type_categorie not in ["paiement", "depense"]:
            flash("Le type de catégorie est invalide.", "error")
            return redirect(url_for("categories.gerer_categories"))

        try:
            df_courant = df_p if type_categorie == "paiement" else df_d
            categories_existantes = df_courant["Categorie"].dropna().tolist() if "Categorie" in df_courant.columns else []

            if action == "ajouter":
                nouvelle = request.form.get("nouvelle_categorie", "").strip()
                if not nouvelle:
                    flash("Le nom de la catégorie est requis.", "error")
                else:
                    if nouvelle in categories_existantes:
                        flash(f"La catégorie '{nouvelle}' existe déjà.", "error")
                    else:
                        if type_categorie == "paiement":
                            ajouter_categorie_paiement(nouvelle)
                        else:
                            ajouter_categorie_depense(nouvelle)
                        flash(f"Catégorie '{nouvelle}' ajoutée.", "success")
                        return redirect(url_for("categories.gerer_categories"))

            elif action == "modifier":
                ancienne = request.form.get("ancienne_categorie", "").strip()
                nouvelle = request.form.get("nouvelle_categorie_modif", "").strip()
                if not ancienne or not nouvelle:
                    flash("Les noms des catégories doivent être fournis pour la modification.", "error")
                else:
                    if ancienne not in categories_existantes:
                        flash(f"La catégorie '{ancienne}' n'existe pas.", "error")
                    else:
                        if type_categorie == "paiement":
                            modifier_categorie_paiement(ancienne, nouvelle)
                        else:
                            modifier_categorie_depense(ancienne, nouvelle)
                        flash(f"Catégorie '{ancienne}' modifiée en '{nouvelle}'.", "success")
                        return redirect(url_for("categories.gerer_categories"))

            elif action == "supprimer":
                categorie = request.form.get("categorie_suppr", "").strip()
                if not categorie:
                    flash("Le nom de la catégorie est requis pour la suppression.", "error")
                else:
                    if categorie not in categories_existantes:
                        flash(f"La catégorie '{categorie}' n'existe pas.", "error")
                    else:
                        if type_categorie == "paiement":
                            supprimer_categorie_paiement(categorie)
                        else:
                            supprimer_categorie_depense(categorie)
                        flash(f"Catégorie '{categorie}' supprimée.", "success")
                        return redirect(url_for("categories.gerer_categories"))

            else:
                flash("Action inconnue.", "error")

        except Exception as e:
            logging.exception("Erreur lors de la gestion des catégories")
            flash(f"Une erreur est survenue : {e}", "error")
            return redirect(url_for("categories.gerer_categories"))

    categories_paiement = df_p["Categorie"].dropna().tolist() if df_p is not None and "Categorie" in df_p.columns else []
    categories_depense = df_d["Categorie"].dropna().tolist() if df_d is not None and "Categorie" in df_d.columns else []

    return render_template(
        "gerer_categories_paiement.html",
        categories_paiement=categories_paiement,
        categories_depense=categories_depense,
    )

