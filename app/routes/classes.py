import io
import logging
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file
)
from fpdf import FPDF

from app.routes.auth import login_required
from ..models.storage import (
    lire_classes, lire_paiements, lire_comments, lire_cours,
    enregistrer_classe_etudiants, enregistrer_paiement,
    enregistrer_commentaire, lire_categories_paiement,
    enregistrer_cours, enregistrer_depense_travail,
    CLASSES_FILE
)

classes_bp = Blueprint("classes", __name__, template_folder="../templates")


# ==========================
# Helpers internes
# ==========================

def paginate(items, page, per_page=15):
    """Retourne: (slice_items, page_corrigée, total_pages)."""
    total = len(items)
    total_pages = (total + per_page - 1) // per_page

    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total_pages


def validate_montant(montant_raw):
    """Valide et convertit un montant en float positif (> 0)."""
    try:
        montant = float(montant_raw)
    except Exception:
        raise ValueError("Le montant doit être un nombre valide.")
    if montant <= 0:
        raise ValueError("Le montant doit être supérieur à zéro.")
    return montant


# ==========================
# Routes
# ==========================

@classes_bp.route("/")
@login_required
def liste_classes():
    """Liste des classes avec recherche + pagination."""
    try:
        df = lire_classes()
        if "NomClasse" not in df.columns:
            df["NomClasse"] = []
        recherche = request.args.get("recherche", "").strip().lower()
        classes = df["NomClasse"].dropna().drop_duplicates()

        if recherche:
            classes = classes[classes.astype(str).str.lower().str.contains(recherche)]

        classes = classes.tolist()
        page = request.args.get("page", 1, type=int)
        classes_page, page, total_pages = paginate(classes, page, per_page=15)

        return render_template(
            "liste_classes.html",
            classes=classes_page,
            page=page,
            total_pages=total_pages
        )
    except Exception:
        logging.exception("Erreur lors de l'affichage de la liste des classes")
        flash("Impossible d'afficher la liste des classes.", "error")
        return render_template("liste_classes.html", classes=[], page=1, total_pages=1)


@classes_bp.route("/<nom_classe>")
@login_required
def detail_classe(nom_classe):
    """Détails d'une classe: étudiants, paiements, commentaires et cours."""
    try:
        df_classes = lire_classes()
        df_paiements = lire_paiements()
        df_comments = lire_comments()
        df_cours = lire_cours()

        # Garde-fous colonnes
        for df_, cols in [
            (df_classes, ["NomClasse", "Etudiant"]),
            (df_paiements, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"]),
            (df_comments, ["NomClasse", "Etudiant", "Commentaire"]),
            (df_cours, ["NomClasse", "NomCours"]),
        ]:
            for c in cols:
                if c not in df_.columns:
                    df_[c] = None

        df_comments.columns = df_comments.columns.str.strip()

        # Étudiants de la classe
        etudiants_liste = sorted(
            df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"]
            .dropna().unique().tolist()
        )

        # Recherche
        recherche = request.args.get("recherche", "").strip().lower()
        if recherche:
            etudiants_liste = [etu for etu in etudiants_liste if recherche in etu.lower()]

        # Pagination
        page = request.args.get("page", 1, type=int)
        etudiants_page, page, total_pages = paginate(etudiants_liste, page, per_page=15)

        # DataFrame étudiants de la page + commentaires
        df_etudiants_page = df_classes[df_classes["NomClasse"] == nom_classe]
        df_etudiants_page = df_etudiants_page[df_etudiants_page["Etudiant"].isin(etudiants_page)]
        df_comments_classe = df_comments[df_comments["NomClasse"] == nom_classe][["Etudiant", "Commentaire"]]

        df_etudiants_page = (
            df_etudiants_page[["Etudiant"]]
            .drop_duplicates()
            .merge(df_comments_classe, how="left", on="Etudiant")
        )
        df_etudiants_page["Commentaire"] = df_etudiants_page["Commentaire"].fillna("")

        # Paiements par étudiant
        paiements_dict = {}
        for etu in etudiants_page:
            paiements_etu = df_paiements[
                (df_paiements["NomClasse"] == nom_classe) &
                (df_paiements["Etudiant"] == etu)
            ]
            paiements_dict[etu] = paiements_etu.to_dict(orient="records")

        # Cours de la classe
        cours_classe = (
            df_cours[df_cours["NomClasse"] == nom_classe]["NomCours"]
            .dropna().tolist()
        )

        return render_template(
            "detail_classe.html",
            nom_classe=nom_classe,
            etudiants=df_etudiants_page.to_dict(orient="records"),
            paiements=paiements_dict,
            cours_classe=cours_classe,
            page=page,
            total_pages=total_pages,
            per_page=15,
        )
    except Exception:
        logging.exception("Erreur lors de l'affichage du détail de la classe")
        flash("Impossible d'afficher les détails de la classe.", "error")
        return redirect(url_for("classes.liste_classes"))


@classes_bp.route("/creer", methods=["GET", "POST"])
@login_required
def creer_classe():
    """Créer une classe avec une liste d'étudiants (un par ligne)."""
    if request.method == "POST":
        nom_classe = request.form.get("nom_classe", "").strip()
        etudiants_brut = request.form.get("etudiants", "")
        liste_etudiants = [e.strip() for e in etudiants_brut.splitlines() if e.strip()]

        if not nom_classe:
            flash("Le nom de la classe ne peut pas être vide.", "error")
            return redirect(url_for("classes.creer_classe"))
        if not liste_etudiants:
            flash("La liste des étudiants ne peut pas être vide.", "error")
            return redirect(url_for("classes.creer_classe"))

        try:
            enregistrer_classe_etudiants(nom_classe, liste_etudiants)
            flash(f"Classe '{nom_classe}' créée avec {len(liste_etudiants)} étudiants.", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
        except Exception:
            logging.exception("Erreur lors de la création de la classe")
            flash("Impossible de créer la classe.", "error")
            return redirect(url_for("classes.liste_classes"))

    return render_template("creer_classe.html")


@classes_bp.route("/<nom_classe>/ajouter_cours", methods=["GET", "POST"])
@login_required
def ajouter_cours(nom_classe):
    """Ajouter plusieurs cours à une classe (un par ligne)."""
    if request.method == "POST":
        try:
            cours_brut = request.form.get("cours", "")
            liste_cours = [c.strip() for c in cours_brut.splitlines() if c.strip()]
            for c in liste_cours:
                enregistrer_cours(nom_classe, c)
            flash(f"{len(liste_cours)} cours ajoutés à la classe {nom_classe}.", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
        except Exception:
            logging.exception("Erreur lors de l'ajout de cours")
            flash("Impossible d'ajouter les cours.", "error")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))

    return render_template("ajouter_cours.html", nom_classe=nom_classe)


@classes_bp.route("/<nom_classe>/etudiant/<etudiant>/ajouter_paiement", methods=["GET", "POST"])
@login_required
def ajouter_paiement(nom_classe, etudiant):
    """Ajouter un paiement pour un étudiant d'une classe."""
    df_cats = lire_categories_paiement()
    if "Categorie" not in df_cats.columns:
        df_cats["Categorie"] = None
    categories = df_cats["Categorie"].dropna().tolist()

    if request.method == "POST":
        try:
            categorie = request.form.get("categorie")
            montant_raw = request.form.get("montant", "0").strip()
            date_paiement = request.form.get("date_paiement")

            # Validations
            montant = validate_montant(montant_raw)

            if categorie not in categories:
                flash("La catégorie sélectionnée est invalide.", "error")
                return redirect(url_for("classes.ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))

            if not date_paiement:
                date_paiement = datetime.now().strftime("%Y-%m-%d")

            enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement)
            flash(f"Paiement ajouté pour {etudiant} ({categorie})", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))

        except ValueError as ve:
            flash(str(ve), "error")
            return redirect(url_for("classes.ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))
        except Exception:
            logging.exception("Erreur lors de l'ajout d'un paiement")
            flash("Erreur lors de l'ajout du paiement.", "error")
            return redirect(url_for("classes.ajouter_paiement", nom_classe=nom_classe, etudiant=etudiant))

    # GET : afficher form avec catégories
    return render_template(
        "ajouter_paiement.html",
        nom_classe=nom_classe,
        etudiant=etudiant,
        categories=categories
    )


@classes_bp.route("/<nom_classe>/generer_pdf_categorie/<categorie>")
@login_required
def generer_pdf_categorie(nom_classe, categorie):
    """Génère un PDF des paiements d'une classe, filtré par catégorie."""
    try:
        df_paiements = lire_paiements()
        df_classes = lire_classes()

        # Garde-fous colonnes
        for df_, cols in [
            (df_paiements, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"]),
            (df_classes, ["NomClasse", "Etudiant"])
        ]:
            for c in cols:
                if c not in df_.columns:
                    df_[c] = None

        etudiants_classe = (
            df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"]
            .dropna().drop_duplicates().reset_index(drop=True)
        )

        if categorie == "Toutes":
            paiements_filtres = df_paiements[df_paiements["NomClasse"] == nom_classe]
        else:
            paiements_filtres = df_paiements[
                (df_paiements["NomClasse"] == nom_classe) &
                (df_paiements["CategoriePaiement"] == categorie)
            ]

        df_complet = etudiants_classe.to_frame().merge(
            paiements_filtres[["Etudiant", "Montant", "DatePaiement", "CategoriePaiement"]],
            on="Etudiant",
            how="left"
        )

        df_complet["Montant"] = df_complet["Montant"].fillna(0)
        df_complet["DatePaiement"] = df_complet["DatePaiement"].fillna("-")
        df_complet["CategoriePaiement"] = df_complet["CategoriePaiement"].fillna("Aucun paiement")

        if df_complet.empty:
            flash(f"Aucun étudiant trouvé pour la classe '{nom_classe}'.", "warning")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))

        # Génération PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)

        titre_pdf = f"Paiements - Classe {nom_classe}"
        if categorie != "Toutes":
            titre_pdf += f" - Catégorie {categorie}"

        pdf.cell(0, 10, titre_pdf, ln=1, align="C")
        pdf.ln(5)

        col_widths = [70, 40, 50]  # Étudiant, Montant, Date
        headers = ["Étudiant", "Montant (USD)", "Date Paiement"]

        def dessiner_entete():
            pdf.set_font("Arial", "B", 12)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, border=1, align="C")
            pdf.ln()

        def dessiner_ligne(etudiant, montant, date_paiement):
            pdf.set_font("Arial", "", 12)
            pdf.cell(col_widths[0], 10, str(etudiant), border=1)
            pdf.cell(col_widths[1], 10, f"{float(montant):.2f} USD", border=1, align="R")
            pdf.cell(col_widths[2], 10, str(date_paiement), border=1)
            pdf.ln()

        dessiner_entete()
        for _, row in df_complet.iterrows():
            if pdf.get_y() > 265:
                pdf.add_page()
                dessiner_entete()
            dessiner_ligne(row["Etudiant"], row["Montant"], row["DatePaiement"])

        pdf_output = pdf.output(dest="S").encode("latin1", errors="replace")
        mem_pdf = io.BytesIO(pdf_output)
        mem_pdf.seek(0)

        return send_file(
            mem_pdf,
            download_name=f"Paiements_{nom_classe}_{categorie}.pdf",
            as_attachment=True
        )
    except Exception:
        logging.exception("Erreur lors de la génération du PDF des paiements")
        flash("Impossible de générer le PDF.", "error")
        return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))


@classes_bp.route("/<nom_classe>/modifier_etudiant/<etudiant>", methods=["GET", "POST"])
@login_required
def modifier_etudiant(nom_classe, etudiant):
    """Modifier le nom d'un étudiant et son commentaire associé."""
    try:
        df_classes = lire_classes()
        df_comments = lire_comments()

        # Garde-fous colonnes
        for df_, cols in [
            (df_classes, ["NomClasse", "Etudiant"]),
            (df_comments, ["NomClasse", "Etudiant", "Commentaire"])
        ]:
            for c in cols:
                if c not in df_.columns:
                    df_[c] = None

        # Préremplissage commentaire existant
        commentaire = ""
        comm_row = df_comments[
            (df_comments["NomClasse"] == nom_classe) &
            (df_comments["Etudiant"] == etudiant)
        ]
        if not comm_row.empty:
            commentaire = str(comm_row.iloc[0].get("Commentaire", "")) or ""

        if request.method == "POST":
            nouveau_nom = request.form.get("nom", "").strip()
            nouveau_commentaire = request.form.get("commentaire", "").strip()

            if not nouveau_nom:
                flash("Le nom de l'étudiant ne peut pas être vide.", "error")
                return redirect(request.url)

            idx = df_classes[
                (df_classes["NomClasse"] == nom_classe) &
                (df_classes["Etudiant"] == etudiant)
            ].index

            if len(idx) == 0:
                flash("Étudiant introuvable.", "error")
                return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))

            # Mise à jour du nom dans le fichier classes
            df_classes.loc[idx[0], "Etudiant"] = nouveau_nom
            df_classes.to_excel(CLASSES_FILE, index=False)

            # Enregistre/Met à jour le commentaire (utilise la logique de storage)
            enregistrer_commentaire(nom_classe, nouveau_nom, nouveau_commentaire)

            flash("Étudiant modifié avec succès.", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))

        return render_template(
            "modifier_etudiant.html",
            nom_classe=nom_classe,
            ancien_nom=etudiant,
            commentaire=commentaire
        )
    except Exception:
        logging.exception("Erreur lors de la modification d'un étudiant")
        flash("Impossible de modifier l'étudiant.", "error")
        return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))


@classes_bp.route("/<nom_classe>/ajouter_depense_travail", methods=["GET", "POST"])
@login_required
def ajouter_depense_travail(nom_classe):
    """
    Ajouter une dépense liée aux travaux (Mémoire, Travaux tutorés, Stage).
    Catégories et sous-dépenses prédéfinies.
    """
    try:
        # Lecture des étudiants pour la classe
        df_classes = lire_classes()
        if "NomClasse" not in df_classes.columns or "Etudiant" not in df_classes.columns:
            df_classes["NomClasse"] = None
            df_classes["Etudiant"] = None

        etudiants = (
            df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"]
            .dropna().drop_duplicates().tolist()
        )

        # Catégories travaux définies
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

        recherche = request.args.get("recherche", "").strip().lower()
        if recherche:
            etudiants = [e for e in etudiants if recherche in e.lower()]

        if request.method == "POST":
            etudiant = request.form.get("etudiant", "").strip()
            categorie_travail = request.form.get("categorie_travail", "").strip()
            depense = request.form.get("depense", "").strip()
            commentaire = request.form.get("commentaire", "").strip()
            montant_raw = request.form.get("montant", "").strip()
            date_depense = request.form.get("date_depense", "").strip()

            erreurs = []

            # Validation étudiant
            if etudiant not in etudiants:
                erreurs.append("Étudiant invalide ou non sélectionné.")

            # Validation catégorie
            if categorie_travail not in CATEGORIES_TRAVAUX:
                erreurs.append("Catégorie de travail invalide.")

            # Validation dépense dans la catégorie
            depenses_valides = [d["nom"] for d in CATEGORIES_TRAVAUX.get(categorie_travail, [])]
            if depense not in depenses_valides:
                erreurs.append("Dépense sélectionnée invalide.")

            # Validation montant
            try:
                montant = validate_montant(montant_raw)
            except ValueError as ve:
                erreurs.append(str(ve))

            # Validation date
            if not date_depense:
                erreurs.append("La date de la dépense est obligatoire.")

            if erreurs:
                for err in erreurs:
                    flash(err, "error")
                # Re-rendu du formulaire avec les valeurs précédentes
                return render_template(
                    "ajouter_depense_travail.html",
                    nom_classe=nom_classe,
                    etudiants=etudiants,
                    categories=list(CATEGORIES_TRAVAUX.keys()),
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

            # Enregistrement si tout est OK
            data = {
                "NomClasse": nom_classe,
                "Etudiant": etudiant,
                "CategorieTravail": categorie_travail,
                "TypeDepense": depense,
                "Commentaire": commentaire,
                "Montant": float(montant),
                "DateDepense": date_depense
            }

            try:
                enregistrer_depense_travail(data)
                flash("Dépense de travail ajoutée avec succès !", "success")
                return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
            except Exception:
                logging.exception("Erreur lors de l'enregistrement d'une dépense de travail")
                flash("Erreur lors de l'enregistrement de la dépense de travail.", "error")
                # Re-rendu formulaire en cas d'erreur
                return render_template(
                    "ajouter_depense_travail.html",
                    nom_classe=nom_classe,
                    etudiants=etudiants,
                    categories=list(CATEGORIES_TRAVAUX.keys()),
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

        # GET : formulaire vide
        return render_template(
            "ajouter_depense_travail.html",
            nom_classe=nom_classe,
            etudiants=etudiants,
            categories=list(CATEGORIES_TRAVAUX.keys()),
            depenses=[],
            recherche=recherche,
            CATEGORIES_TRAVAUX=CATEGORIES_TRAVAUX
        )
    except Exception:
        logging.exception("Erreur sur la page d'ajout de dépense de travail")
        flash("Impossible d'afficher la page des dépenses de travail.", "error")
        return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
