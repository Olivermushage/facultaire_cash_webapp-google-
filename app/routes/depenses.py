import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.routes.auth import login_required
from app.models import storage_gsheets as storage
from app.utils.pagination import paginate  # Assurez-vous que paginate est défini ici
from flask import session
from app.models.storage_gsheets import get_sheet,  read_sheet
import pandas as pd

# --- Blueprint ---
depenses_bp = Blueprint("depenses", __name__, template_folder="../templates")

# # --- Fonctions utilitaires pour lire les données ---
@depenses_bp.route("/depenses")
@login_required
def depenses_index():
    """Page principale des dépenses avec pagination."""
    try:
        depenses = storage.lire_depenses()  # DataFrame complète

        # Liste des colonnes attendues/affichées
        colonnes_a_afficher = [
            "NomCours",
            "CategorieDepense",
            "Description",
            "Montant",
            "NomClasse",
            "TypeDepense",
            "Commentaire",
            "DateDepense"
        ]

        # S'assurer que ces colonnes existent, sinon les créer vides
        for col in colonnes_a_afficher:
            if col not in depenses.columns:
                depenses[col] = None

        # Sélectionner uniquement ces colonnes, garder l'ordre
        depenses = depenses[colonnes_a_afficher]

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = 20
        total = len(depenses)
        start = (page - 1) * per_page
        end = start + per_page
        depenses_paginees = depenses.iloc[start:end]

        total_pages = (total + per_page - 1) // per_page  # arrondi supérieur

        return render_template(
            "depenses_index.html",
            depenses=depenses_paginees.to_dict(orient="records"),
            page=page,
            total_pages=total_pages
        )
    except Exception as e:
        logging.exception("Erreur lors de l'affichage de la page des dépenses")
        return render_template(
            "depenses_index.html",
            depenses=[],
            page=1,
            total_pages=1,
            error="Impossible de charger les dépenses."
        )

def lire_cours():
    df = read_sheet("Cours")
    if df.empty:
        return pd.DataFrame(columns=["NomClasse", "NomCours"])

    # Normalisation des noms de colonnes
    df.columns = df.columns.astype(str).str.strip()

    # Corrige la faute de frappe si présente
    if "NomClassse" in df.columns and "NomClasse" not in df.columns:
        df.rename(columns={"NomClassse": "NomClasse"}, inplace=True)

    # S'assure que les deux colonnes existent
    if "NomClasse" not in df.columns:
        df["NomClasse"] = ""
    if "NomCours" not in df.columns:
        df["NomCours"] = ""

    # Nettoyage valeurs
    df["NomClasse"] = df["NomClasse"].astype(str).str.strip()
    df["NomCours"] = df["NomCours"].astype(str).str.strip()
    return df


# --- Route liste des dépenses examens ---
@depenses_bp.route('/liste_examen/<nom_classe>')
@login_required
def liste_depenses_examen(nom_classe):
    try:
        df_depenses = lire_depenses()
        df_cours = lire_cours()

        # Logs pour diagnostic
        logging.debug(f"Colonnes depenses : {df_depenses.columns.tolist()}")
        logging.debug(f"Premières lignes depenses :\n{df_depenses.head(5)}")
        logging.debug(f"Colonnes cours : {df_cours.columns.tolist()}")
        logging.debug(f"Premières lignes cours :\n{df_cours.head(5)}")

        # Assurer présence colonnes essentielles
        for col in ["NomClasse", "NomCours"]:
            if col not in df_cours.columns:
                logging.warning(f"Colonne {col} manquante dans cours, ajout colonne vide.")
                df_cours[col] = None
            if col not in df_depenses.columns:
                logging.warning(f"Colonne {col} manquante dans depenses, ajout colonne vide.")
                df_depenses[col] = None

        # Nettoyer espaces
        df_cours["NomClasse"] = df_cours["NomClasse"].astype(str).str.strip()
        df_cours["NomCours"] = df_cours["NomCours"].astype(str).str.strip()
        df_depenses["NomClasse"] = df_depenses["NomClasse"].astype(str).str.strip()
        df_depenses["NomCours"] = df_depenses["NomCours"].astype(str).str.strip()

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
        # Récupération des classes disponibles
        df_classes = storage.lire_classes()
        classes = sorted(df_classes["NomClasse"].dropna().unique().tolist()) if not df_classes.empty else []

        recherche = request.args.get("recherche", "").strip().lower()
        categories_examen = ["Matériel", "Frais", "Autre"]

        if request.method == "POST":
            nom_classe = request.form.get("nom_classe", "").strip()
            categorie_examen = request.form.get("categorie_examen", "").strip()
            description = request.form.get("description", "").strip()
            commentaire = request.form.get("commentaire", "").strip()
            montant_raw = request.form.get("montant")
            date_depense = request.form.get("date_depense", "").strip()
            type_depense = "standard"

            erreurs = []

            # --- Validation des champs ---
            if nom_classe not in classes:
                erreurs.append("Classe invalide ou non sélectionnée.")
            if categorie_examen not in categories_examen:
                erreurs.append("Catégorie invalide.")
            if not description:
                erreurs.append("La description est obligatoire.")
            if not montant_raw:
                erreurs.append("Le montant est obligatoire.")
            if not date_depense:
                erreurs.append("La date de dépense obligatoire.")

            try:
                montant = float(montant_raw) if montant_raw else 0.0
            except ValueError:
                erreurs.append("Montant invalide.")

            if erreurs:
                for err in erreurs:
                    flash(err, "error")
                return render_template(
                    "ajouter_depense_examen.html",
                    classes=classes,
                    categories=categories_examen,
                    nom_classe_valeur=nom_classe,
                    categorie_valeur=categorie_examen,
                    description_valeur=description,
                    commentaire_valeur=commentaire,
                    montant_valeur=montant_raw,
                    date_depense_valeur=date_depense,
                    recherche=recherche
                )

            # --- Enregistrement via la fonction centralisée ---
            try:
                storage.ajouter_depense(
                    categorie=f"Examen - {categorie_examen}",
                    description=description,
                    commentaire=commentaire,
                    montant=montant,
                    date_depense=date_depense,
                    nom_classe=nom_classe,
                    nom_cours="",  # Pas de cours spécifique pour cette route
                    type_depense=type_depense,
                    utilisateur=session.get("username", "inconnu")
                )
                flash("Dépense examen ajoutée avec succès !", "success")
                return redirect(url_for("depenses.depenses_index"))
            except Exception as e:
                logging.exception("Erreur lors de l'enregistrement d'une dépense examen")
                flash(f"Erreur lors de l'enregistrement : {str(e)}", "error")
                return render_template(
                    "ajouter_depense_examen.html",
                    classes=classes,
                    categories=categories_examen,
                    nom_classe_valeur=nom_classe,
                    categorie_valeur=categorie_examen,
                    description_valeur=description,
                    commentaire_valeur=commentaire,
                    montant_valeur=montant_raw,
                    date_depense_valeur=date_depense,
                    recherche=recherche
                )

        # GET : formulaire vide
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




@depenses_bp.route("/ajouter_autres", methods=["GET", "POST"])
@login_required
def ajouter_depense_autres():
    classes = storage.get_classes()  # Récupère la liste des classes
    if request.method == "POST":
        type_depense = request.form.get("type_depense")
        sous_type = request.form.get("sous_type")
        classe = request.form.get("classe")
        cours = request.form.get("cours")
        description = request.form.get("description", "").strip()
        commentaire = request.form.get("commentaire", "").strip()
        montant_raw = request.form.get("montant")
        date_depense = request.form.get("date_depense")

        erreurs = []

        # --- Validation des champs ---
        if not type_depense:
            erreurs.append("Le type de dépense est requis.")

        if type_depense == "standard" and not sous_type:
            erreurs.append("Le sous-type est requis pour une dépense standard.")

        if not description:
            erreurs.append("La description est obligatoire.")

        if not montant_raw:
            erreurs.append("Le montant est obligatoire.")

        if not date_depense:
            erreurs.append("La date est obligatoire.")

        # --- Cas spécifiques selon le type ---
        categorie = None
        if type_depense == "manuelle":
            categorie = "Autres - Manuelle"

        elif type_depense == "standard":
            if sous_type == "examen":
                if not classe or classe not in classes:
                    erreurs.append("Classe invalide ou non sélectionnée.")
                if not cours:
                    erreurs.append("Un cours doit être sélectionné pour une dépense liée à un examen.")
                categorie = f"Examen - {classe or ''} - {cours or ''}"

            elif sous_type == "travail":
                if not classe or classe not in classes:
                    erreurs.append("Classe invalide ou non sélectionnée pour une dépense liée au travail.")
                categorie = f"Travail - {classe or ''}"

            elif sous_type == "autre":
                categorie = "Autres - Standard"

            else:
                erreurs.append("Sous-type invalide.")

        else:
            erreurs.append("Type de dépense invalide.")

        if erreurs:
            for err in erreurs:
                flash(err, "error")
            return render_template(
                "ajouter_depense_autres.html",
                classes=classes,
                type_depense_valeur=type_depense,
                sous_type_valeur=sous_type,
                classe_valeur=classe,
                cours_valeur=cours,
                description_valeur=description,
                commentaire_valeur=commentaire,
                montant_valeur=montant_raw,
                date_depense_valeur=date_depense
            )

        # --- Conversion du montant ---
        try:
            montant = float(montant_raw)
        except ValueError:
            flash("Montant invalide.", "error")
            return render_template(
                "ajouter_depense_autres.html",
                classes=classes,
                type_depense_valeur=type_depense,
                sous_type_valeur=sous_type,
                classe_valeur=classe,
                cours_valeur=cours,
                description_valeur=description,
                commentaire_valeur=commentaire,
                montant_valeur=montant_raw,
                date_depense_valeur=date_depense
            )

        # --- Sauvegarde via la fonction centralisée ---
        try:
            storage.ajouter_depense(
                categorie=categorie,
                description=description,
                commentaire=commentaire,
                montant=montant,
                date_depense=date_depense,
                nom_classe=classe,
                nom_cours=cours,
                type_depense=type_depense,
                utilisateur=session.get("username", "inconnu")
            )
            flash("Dépense ajoutée avec succès.", "success")
            return redirect(url_for("depenses.depenses_index"))
        except Exception as e:
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "error")
            return redirect(url_for("depenses.ajouter_depense_autres"))

    # GET : formulaire vide
    return render_template("ajouter_depense_autres.html", classes=classes)


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



@depenses_bp.route("/api/cours/<classe_id>")
def get_cours_by_classe(classe_id):
    """
    Retourne en JSON la liste des cours pour une classe donnée
    """
    try:
        sheet = get_sheet("Cours")  # suppose qu'on a une feuille "Cours" avec colonnes Classe, NomCours
        rows = sheet.get_all_records()

        cours = [row["NomCours"] for row in rows if row.get("Classe") == classe_id]

        return jsonify({"status": "success", "cours": cours})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@depenses_bp.route("/api/cours", methods=["GET"])
@login_required
def api_cours_by_classe():
    """
    Retourne en JSON la liste des cours pour une classe donnée (paramètre query ?classe=).
    S'appuie sur storage.lire_cours() qui corrige NomClassse -> NomClasse.
    """
    classe = (request.args.get("classe") or "").strip()
    if not classe:
        return jsonify({"status": "error", "message": "Paramètre 'classe' requis."}), 400
    try:
        df = storage.lire_cours()
        if df.empty:
            return jsonify({"status": "success", "cours": []})

        # Filtre strict sur la classe
        mask = df["NomClasse"].astype(str).str.strip() == classe
        cours = (
            df.loc[mask, "NomCours"]
              .dropna()
              .astype(str)
              .str.strip()
              .unique()
              .tolist()
        )
        return jsonify({"status": "success", "cours": cours})
    except Exception as e:
        logging.exception("Erreur AJAX /api/cours")
        return jsonify({"status": "error", "message": str(e)}), 500
