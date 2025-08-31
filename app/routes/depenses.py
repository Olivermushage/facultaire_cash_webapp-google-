import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.routes.auth import login_required
from app.models import storage_gsheets as storage
from app.utils.pagination import paginate  # Assurez-vous que paginate est défini ici
from flask import session


# --- Blueprint ---
depenses_bp = Blueprint("depenses", __name__, template_folder="../templates")

# --- Fonctions utilitaires pour lire les données ---
def lire_depenses():
    return storage.lire_depenses()

def lire_cours():
    return storage.lire_cours()

# --- Route liste des dépenses examens ---
@depenses_bp.route('/liste_examen/<nom_classe>')
@login_required
def liste_depenses_examen(nom_classe):
    try:
        df_depenses = lire_depenses()
        df_cours = lire_cours()

        # Sécurité colonnes manquantes
        if "NomClasse" not in df_cours.columns:
            df_cours["NomClasse"] = None
        if "NomCours" not in df_cours.columns:
            df_cours["NomCours"] = None

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
                lambda row: recherche in str(row.get("Description", "")).lower()
                            or recherche in str(row.get("CategorieDepense", "")).lower(),
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

# --- Ajout de dépense travail (existante dans votre fichier) ---
@depenses_bp.route("/ajouter_depense_travail", methods=["GET", "POST"])
@login_required
def ajouter_depense_travail():
    try:
        df_classes = storage.lire_classes()
        classes = sorted(df_classes["NomClasse"].dropna().unique().tolist()) if not df_classes.empty else []
        recherche = request.args.get("recherche", "").strip().lower()
        categories_travaux = ["Travail pratique", "Projet", "Autre"]  # exemple

        if request.method == "POST":
            nom_classe = request.form.get("nom_classe", "").strip()
            etudiant = request.form.get("etudiant", "").strip()
            categorie_travail = request.form.get("categorie_travail", "").strip()
            type_depense = request.form.get("type_depense", "").strip()
            commentaire = request.form.get("commentaire", "").strip()
            date_depense = request.form.get("date_depense", "").strip()

            erreurs = []
            if nom_classe not in classes:
                erreurs.append("Classe invalide ou non sélectionnée.")
            etudiants_possibles = df_classes[df_classes["NomClasse"]==nom_classe]["Etudiant"].tolist() if nom_classe else []
            if etudiant not in etudiants_possibles:
                erreurs.append("Étudiant invalide pour la classe sélectionnée.")
            if categorie_travail not in categories_travaux:
                erreurs.append("Catégorie invalide.")
            if not type_depense:
                erreurs.append("Type de dépense obligatoire.")
            if not date_depense:
                erreurs.append("Date de dépense obligatoire.")

            if erreurs:
                for err in erreurs:
                    flash(err, "error")
                return render_template(
                    "ajouter_depense_travail.html",
                    classes=classes,
                    etudiants=etudiants_possibles,
                    categories=categories_travaux,
                    nom_classe_valeur=nom_classe,
                    etudiant_valeur=etudiant,
                    categorie_valeur=categorie_travail,
                    type_depense_valeur=type_depense,
                    commentaire_valeur=commentaire,
                    date_depense_valeur=date_depense,
                    recherche=recherche
                )

            data = {
                "NomClasse": nom_classe,
                "Etudiant": etudiant,
                "CategorieTravail": categorie_travail,
                "TypeDepense": type_depense,
                "Commentaire": commentaire,
                "DateDepense": date_depense
            }

            try:
                storage.enregistrer_depense_travaux(data)
                flash("Dépense travail ajoutée avec succès !", "success")
                return redirect(url_for("depenses.depenses_index"))
            except Exception:
                logging.exception("Erreur lors de l'enregistrement d'une dépense travail")
                flash("Erreur lors de l'enregistrement de la dépense.", "error")
                return render_template(
                    "ajouter_depense_travail.html",
                    classes=classes,
                    etudiants=etudiants_possibles,
                    categories=categories_travaux,
                    nom_classe_valeur=nom_classe,
                    etudiant_valeur=etudiant,
                    categorie_valeur=categorie_travail,
                    type_depense_valeur=type_depense,
                    commentaire_valeur=commentaire,
                    date_depense_valeur=date_depense,
                    recherche=recherche
                )

        return render_template(
            "ajouter_depense_travail.html",
            classes=classes,
            etudiants=[],
            categories=categories_travaux,
            recherche=recherche
        )

    except Exception:
        logging.exception("Erreur sur la page d'ajout de dépense travail")
        flash("Impossible d'afficher la page des dépenses travail.", "error")
        return redirect(url_for("depenses.depenses_index"))



@depenses_bp.route("/depenses")
@login_required
def depenses_index():
    """Page principale des dépenses avec pagination."""
    try:
        # Récupérer toutes les dépenses
        depenses = storage.lire_depenses()
        
        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = 20  # nombre de lignes par page
        total = len(depenses)
        start = (page - 1) * per_page
        end = start + per_page
        depenses_paginees = depenses.iloc[start:end]  # DataFrame slice

        # Calcul du nombre total de pages
        total_pages = (total + per_page - 1) // per_page  # arrondi supérieur

        return render_template(
            "depenses_index.html",
            depenses=depenses_paginees.to_dict(orient="records"),  # pour Jinja2
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages
        )
    except Exception as e:
        logging.exception("Erreur lors de l'affichage de la page des dépenses")
        return render_template(
            "depenses_index.html",
            depenses=[],
            page=1,
            per_page=20,
            total=0,
            total_pages=1,
            error="Impossible de charger les dépenses."
        )



@depenses_bp.route('/choisir_classe_examen')
@login_required
def choisir_classe_examen():
    # Lire les données depuis Google Sheets
    df_classes = storage.lire_classes()  # renvoie un DataFrame

    # Obtenir uniquement la liste des classes uniques
    if df_classes is None or df_classes.empty:
        classes = []
    else:
        classes = df_classes["NomClasse"].dropna().unique().tolist()  # unique supprime les doublons
        classes.sort()  # tri optionnel

    return render_template(
        "choisir_classe.html",
        classes=classes,
        action="liste_depenses_examen"
    )


@depenses_bp.route('/liste_autres')
@login_required
def liste_depenses_autres():
    # Lire toutes les dépenses
    df_depenses = storage.lire_depenses()

    # Filtrer les autres dépenses
    autres_depenses = df_depenses[df_depenses['TypeDepense'] != 'Examen'].to_dict(orient='records')

    # Pagination simple
    page = request.args.get('page', 1, type=int)
    per_page = 10  # nombre de dépenses par page
    total = len(autres_depenses)
    start = (page - 1) * per_page
    end = start + per_page
    depenses_page = autres_depenses[start:end]

    return render_template(
        "liste_depenses.html",
        depenses=depenses_page,
        titre="Autres dépenses",
        page=page,
        total_pages=(total + per_page - 1) // per_page  # calcul du nombre total de pages
    )

@depenses_bp.route("/ajouter_depense_examen", methods=["GET", "POST"])
@login_required
def ajouter_depense_examen():
    try:
        df_classes = storage.lire_classes()
        classes = sorted(df_classes["NomClasse"].dropna().unique().tolist()) if not df_classes.empty else []
        recherche = request.args.get("recherche", "").strip().lower()
        categories_examen = ["Matériel", "Frais", "Autre"]

        if request.method == "POST":
            nom_classe = request.form.get("nom_classe", "").strip()
            categorie_examen = request.form.get("categorie_examen", "").strip()
            type_depense = request.form.get("type_depense", "").strip()
            commentaire = request.form.get("commentaire", "").strip()
            date_depense = request.form.get("date_depense", "").strip()

            erreurs = []
            if nom_classe not in classes:
                erreurs.append("Classe invalide ou non sélectionnée.")
            if categorie_examen not in categories_examen:
                erreurs.append("Catégorie invalide.")
            if not type_depense:
                erreurs.append("Type de dépense obligatoire.")
            if not date_depense:
                erreurs.append("Date de dépense obligatoire.")

            if erreurs:
                for err in erreurs:
                    flash(err, "error")
                return render_template(
                    "ajouter_depense_examen.html",
                    classes=classes,
                    categories=categories_examen,
                    nom_classe_valeur=nom_classe,
                    categorie_valeur=categorie_examen,
                    type_depense_valeur=type_depense,
                    commentaire_valeur=commentaire,
                    date_depense_valeur=date_depense,
                    recherche=recherche
                )

            data = {
                "NomClasse": nom_classe,
                "CategorieDepense": categorie_examen,
                "TypeDepense": type_depense,
                "Commentaire": commentaire,
                "DateDepense": date_depense
            }

            try:
                storage.enregistrer_depense_examen(data)
                flash("Dépense examen ajoutée avec succès !", "success")
                return redirect(url_for("depenses.depenses_index"))
            except Exception:
                logging.exception("Erreur lors de l'enregistrement d'une dépense examen")
                flash("Erreur lors de l'enregistrement de la dépense.", "error")
                return render_template(
                    "ajouter_depense_examen.html",
                    classes=classes,
                    categories=categories_examen,
                    nom_classe_valeur=nom_classe,
                    categorie_valeur=categorie_examen,
                    type_depense_valeur=type_depense,
                    commentaire_valeur=commentaire,
                    date_depense_valeur=date_depense,
                    recherche=recherche
                )

        return render_template(
            "ajouter_depense_examen.html",
            classes=classes,
            categories=categories_examen,
            recherche=recherche
        )

    except Exception:
        logging.exception("Erreur sur la page d'ajout de dépense examen")
        flash("Impossible d'afficher la page des dépenses examen.", "error")
        return redirect(url_for("depenses.depenses_index"))


@depenses_bp.route("/ajouter_depense_autres", methods=["GET", "POST"])
@login_required
def ajouter_depense_autres():
    """
    Ajouter une dépense autre que celles liées aux travaux ou examens.
    Gestion du type : 'manuelle' ou 'standard' avec sous-type possible.
    """
    try:
        # Lecture des classes disponibles
        df_classes = storage.lire_classes()
        classes = df_classes["NomClasse"].dropna().drop_duplicates().tolist() if not df_classes.empty else []

        # Catégories standard pour ce formulaire
        categories_autres = ["Fournitures", "Déplacements", "Autres"]

        if request.method == "POST":
            type_depense = request.form.get("type_depense", "").strip()
            sous_type = request.form.get("sous_type", "").strip()
            nom_classe = request.form.get("nom_classe", "").strip()
            description = request.form.get("description", "").strip()
            commentaire = request.form.get("commentaire", "").strip()
            montant_raw = request.form.get("montant", "").strip()
            date_depense = request.form.get("date_depense", "").strip()

            erreurs = []

            # Validation type
            if type_depense not in ["manuelle", "standard"]:
                erreurs.append("Le type de dépense n'est pas valide.")

            # Validation sous-type et classe
            # Validation sous-type et classe
            if type_depense == "standard":
            # Si c’est une dépense liée à Travaux ou Examens, la classe est obligatoire
                if sous_type in ["Travaux", "Examen"] and nom_classe not in classes:
                    erreurs.append("Classe invalide ou non sélectionnée.")


            # Validation montant
            try:
                montant = float(montant_raw)
                if montant <= 0:
                    erreurs.append("Le montant doit être supérieur à 0.")
            except ValueError:
                erreurs.append("Montant invalide.")

            if not description:
                erreurs.append("Description obligatoire.")

            if not date_depense:
                erreurs.append("Date de dépense obligatoire.")

            if erreurs:
                for err in erreurs:
                    flash(err, "error")
                return render_template(
                    "ajouter_depense_autres.html",
                    classes=classes,
                    categories=categories_autres,
                    type_depense_valeur=type_depense,
                    sous_type_valeur=sous_type,
                    nom_classe_valeur=nom_classe,
                    description_valeur=description,
                    commentaire_valeur=commentaire,
                    montant_valeur=montant_raw,
                    date_depense_valeur=date_depense
                )

            # Construction de l'enregistrement
            data = {
                "Description": description,
                "Commentaire": commentaire,
                "Montant": montant,
                "DateDepense": date_depense,
                "TypeDepense": type_depense,
                "NomClasse": nom_classe if nom_classe else "",
                "CategorieDepense": sous_type if type_depense == "standard" else "Autre",
                "Utilisateur": session.get("username", "inconnu")
            }

            try:
                storage.enregistrer_depense_autres(data)
                flash("Dépense ajoutée avec succès !", "success")
                return redirect(url_for("depenses.depenses_index"))
            except Exception:
                logging.exception("Erreur lors de l'enregistrement d'une dépense autre")
                flash("Erreur lors de l'enregistrement de la dépense.", "error")
                return render_template(
                    "ajouter_depense_autres.html",
                    classes=classes,
                    categories=categories_autres,
                    type_depense_valeur=type_depense,
                    sous_type_valeur=sous_type,
                    nom_classe_valeur=nom_classe,
                    description_valeur=description,
                    commentaire_valeur=commentaire,
                    montant_valeur=montant_raw,
                    date_depense_valeur=date_depense
                )

        # GET : formulaire vide
        return render_template(
            "ajouter_depense_autres.html",
            classes=classes,
            categories=categories_autres
        )

    except Exception:
        logging.exception("Erreur sur la page d'ajout de dépense autres")
        flash("Impossible d'afficher la page des autres dépenses.", "error")
        return redirect(url_for("depenses.depenses_index"))

@depenses_bp.route('/modifier/<int:depense_id>', methods=['GET', 'POST'])
@login_required
def modifier_depense(depense_id):
    # Lire toutes les dépenses
    df_depenses = storage.lire_depenses()

    # Chercher la dépense à modifier
    depense = df_depenses[df_depenses['ID'] == depense_id]
    if depense.empty:
        flash("Dépense introuvable.", "danger")
        return redirect(url_for("depenses.liste_depenses_autres"))

    depense_data = depense.iloc[0].to_dict()  # convertir en dict

    if request.method == "POST":
        # Récupérer les champs du formulaire
        type_depense = request.form.get("TypeDepense")
        montant = request.form.get("Montant")
        description = request.form.get("Description")

        # Mettre à jour le DataFrame
        df_depenses.loc[df_depenses['ID'] == depense_id, ['TypeDepense', 'Montant', 'Description']] = [
            type_depense, montant, description
        ]

        # Sauvegarder les modifications
        storage.ecrire_depenses(df_depenses)
        flash("Dépense modifiée avec succès.", "success")
        return redirect(url_for("depenses.liste_depenses_autres"))

    # Afficher le formulaire avec les données existantes
    return render_template("modifier_depense.html", depense=depense_data)
