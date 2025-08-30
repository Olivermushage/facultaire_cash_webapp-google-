import logging
from flask import Blueprint, render_template, send_file, request, redirect, url_for, flash, make_response
from app.routes.auth import login_required
from app.models import storage_gsheets as storage
from reportlab.lib.pagesizes import A4, landscape
from io import BytesIO
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle



# Blueprint pour les classes
classes_bp = Blueprint("classes", __name__, template_folder="../templates")


@classes_bp.route('/choisir_classe_etudiant')
@login_required
def choisir_classe_etudiant():
    classes = storage.liste_classes()
    return render_template('choisir_classe.html', classes=classes, action='ajouter_etudiant')


@classes_bp.route('/choisir_classe_paiement')
@login_required
def choisir_classe_paiement():
    classes = storage.liste_classes()
    return render_template('choisir_classe.html', classes=classes, action='suivi_paiements')


@classes_bp.route("/classes/<nom_classe>/suivi_paiements")
@login_required
def suivi_paiements(nom_classe):
    return redirect(url_for('classes.detail_classe', nom_classe=nom_classe))


@classes_bp.route('/classes/liste')
def liste_classes():
    try:
        df_classes = storage.lire_classes()
        if df_classes is not None and not df_classes.empty:
            classes = df_classes['NomClasse'].drop_duplicates().tolist()
            classes.sort()
        else:
            classes = []
        page = request.args.get('page', 1, type=int)
        per_page = 20
        total_pages = (len(classes) + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        classes_page = classes[start:end]
        return render_template(
            "liste_classes.html",
            classes=classes_page,
            page=page,
            total_pages=total_pages
        )
    except Exception as e:
        print(f"Erreur lecture classes: {e}")
        return render_template(
            "liste_classes.html",
            classes=[],
            page=1,
            total_pages=1,
            error=str(e)
        )


@classes_bp.route("/classes/creer", methods=["GET", "POST"])
@login_required
def creer_classe():
    if request.method == "POST":
        nom_classe = request.form.get("nom_classe", "").strip()
        etudiants = request.form.get("etudiants", "").strip().splitlines()
        if not nom_classe:
            flash("Le nom de la classe est requis.", "error")
            return redirect(request.url)
        try:
            storage.enregistrer_classe_etudiants(nom_classe, etudiants)
            flash("Classe créée avec succès ✅", "success")
            return redirect(url_for("classes.liste_classes"))
        except Exception as e:
            logging.exception("Erreur lors de la création de la classe")
            flash(f"Erreur lors de la création : {e}", "error")
            return redirect(request.url)
    return render_template("creer_classe.html")


@classes_bp.route("/classes/<nom_classe>")
@login_required
def detail_classe(nom_classe):
    try:
        df_classes = storage.lire_classes()
        df_paiements = storage.lire_paiements()
        df_comments = getattr(storage, "lire_comments", lambda: None)()
        df_cours = storage.lire_cours()
        df_depenses = storage.lire_depenses()

        def ensure_columns(df, cols):
            if df is not None:
                for c in cols:
                    if c not in df.columns:
                        df[c] = None

        ensure_columns(df_classes, ["NomClasse", "Etudiant"])
        ensure_columns(df_paiements, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"])
        ensure_columns(df_comments, ["NomClasse", "Etudiant", "Commentaire"])
        ensure_columns(df_cours, ["NomClasse", "NomCours"])
        ensure_columns(df_depenses, ["NomClasse", "Categorie", "Montant", "DateDepense"])

        etudiants_liste = []
        if df_classes is not None and not df_classes.empty:
            etudiants_liste = sorted(
                df_classes[df_classes["NomClasse"].astype(str).str.strip() == nom_classe.strip()]["Etudiant"]
                .dropna().unique().tolist()
            )

        recherche = request.args.get("recherche", "").strip().lower()
        if recherche:
            etudiants_liste = [etu for etu in etudiants_liste if recherche in etu.lower()]

        page = request.args.get("page", 1, type=int)
        per_page = 15
        total_pages = max(1, (len(etudiants_liste) + per_page - 1) // per_page)
        start = (page - 1) * per_page
        end = start + per_page
        etudiants_page = etudiants_liste[start:end]

        df_etudiants_page = df_classes[df_classes["NomClasse"].astype(str).str.strip() == nom_classe.strip()]
        df_etudiants_page = df_etudiants_page[df_etudiants_page["Etudiant"].isin(etudiants_page)]

        if df_comments is not None and not df_comments.empty:
            df_comments_classe = df_comments[df_comments["NomClasse"].astype(str).str.strip() == nom_classe.strip()][["Etudiant", "Commentaire"]]
        else:
            df_comments_classe = None

        if df_etudiants_page is not None:
            if df_comments_classe is not None:
                df_etudiants_page = df_etudiants_page[["Etudiant"]].drop_duplicates().merge(df_comments_classe, how="left", on="Etudiant")
            else:
                df_etudiants_page = df_etudiants_page[["Etudiant"]].drop_duplicates()
            if "Commentaire" in df_etudiants_page.columns:
                df_etudiants_page["Commentaire"] = df_etudiants_page["Commentaire"].fillna("")
            else:
                df_etudiants_page["Commentaire"] = ""
            etudiants_dict = df_etudiants_page.to_dict(orient="records")
        else:
            etudiants_dict = []

        paiements_dict = {}
        if df_paiements is not None and not df_paiements.empty:
            df_paiements["NomClasse"] = df_paiements["NomClasse"].astype(str).str.strip()
            df_paiements["Etudiant"] = df_paiements["Etudiant"].astype(str).str.strip()
            for etu in etudiants_page:
                paiements_dict[etu] = df_paiements[
                    (df_paiements["NomClasse"] == nom_classe.strip()) &
                    (df_paiements["Etudiant"] == etu)
                ].to_dict(orient="records")

        cours_classe = []
        if df_cours is not None and not df_cours.empty:
            df_cours["NomClasse"] = df_cours["NomClasse"].astype(str).str.strip()
            cours_classe = df_cours[df_cours["NomClasse"] == nom_classe.strip()]["NomCours"].dropna().tolist()

        depenses = []
        if df_depenses is not None and not df_depenses.empty:
            df_depenses["NomClasse"] = df_depenses["NomClasse"].astype(str).str.strip()
            depenses = df_depenses[df_depenses["NomClasse"] == nom_classe.strip()].to_dict(orient="records")

        categories_paiement = []
        if df_paiements is not None and not df_paiements.empty:
            categories_paiement = sorted(df_paiements["CategoriePaiement"].dropna().unique())

        return render_template(
            "detail_classe.html",
            nom_classe=nom_classe,
            etudiants=etudiants_dict,
            paiements=paiements_dict,
            cours_classe=cours_classe,
            depenses=depenses,
            categories_paiement=categories_paiement,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except Exception as e:
        logging.exception("Erreur lors de l'affichage du détail de la classe")
        flash(f"Impossible d'afficher les détails de la classe: {e}", "error")
        return redirect(url_for("classes.liste_classes"))


@classes_bp.route("/classes/<nom_classe>/ajouter_etudiant", methods=["GET", "POST"])
@login_required
def ajouter_etudiant(nom_classe):
    if request.method == "POST":
        etudiant = request.form.get("etudiant", "").strip()
        if not etudiant:
            flash("Le nom de l'étudiant est requis.", "error")
            return redirect(request.url)
        try:
            storage.enregistrer_classe_etudiants(nom_classe, [etudiant])
            flash("Étudiant ajouté avec succès ✅", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
        except Exception as e:
            logging.exception("Erreur lors de l'ajout d'un étudiant")
            flash(f"Erreur : {e}", "error")
            return redirect(request.url)
    return render_template("ajouter_etudiant.html", nom_classe=nom_classe)


@classes_bp.route("/classes/<nom_classe>/modifier_etudiant/<etudiant>", methods=["GET", "POST"])
@login_required
def modifier_etudiant(nom_classe, etudiant):
    if request.method == "POST":
        nouveau_nom = request.form.get("nouveau_nom", "").strip()
        if not nouveau_nom:
            flash("Le nouveau nom est requis.", "error")
            return redirect(request.url)
        try:
            storage.mettre_a_jour_etudiant(nom_classe, etudiant, nouveau_nom)
            flash("Étudiant modifié avec succès ✅", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
        except Exception as e:
            logging.exception("Erreur lors de la modification de l'étudiant")
            flash(f"Erreur lors de la modification : {e}", "error")
            return redirect(request.url)
    return render_template("modifier_etudiant.html", nom_classe=nom_classe, etudiant=etudiant)


@classes_bp.route("/classes/<nom_classe>/ajouter_cours", methods=["GET", "POST"])
@login_required
def ajouter_cours(nom_classe):
    cours_valeur = ""
    if request.method == "POST":
        cours_valeur = request.form.get("cours", "").strip()
        if not cours_valeur:
            flash("Veuillez saisir au moins un cours.", "error")
        else:
            cours_lignes = [c.strip() for c in cours_valeur.splitlines() if c.strip()]
            try:
                df_cours = storage.lire_cours()
                if df_cours is None:
                    df_cours = pd.DataFrame(columns=["NomClasse", "NomCours"])
                new_rows = pd.DataFrame([{"NomClasse": nom_classe, "NomCours": c} for c in cours_lignes])
                df_cours = pd.concat([df_cours, new_rows], ignore_index=True)
                storage.write_sheet("Cours", df_cours)
                flash(f"{len(cours_lignes)} cours ajoutés à la classe {nom_classe}.", "success")
                return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
            except Exception as e:
                flash(f"Erreur lors de l'ajout des cours : {e}", "error")
    return render_template("ajouter_cours.html", nom_classe=nom_classe, cours_valeur=cours_valeur)


@classes_bp.route("/classes/<nom_classe>/ajouter_paiement", methods=["GET", "POST"])
@login_required
def ajouter_paiement(nom_classe):
    if request.method == "POST":
        etudiant = request.form.get("etudiant", "").strip()
        categorie = request.form.get("categorie", "").strip()
        montant = request.form.get("montant", "").strip()
        date_paiement = request.form.get("date_paiement", "").strip()
        utilisateur = request.form.get("utilisateur", "").strip()
        if not (etudiant and categorie and montant and date_paiement):
            flash("Tous les champs sont requis.", "error")
            return redirect(request.url)
        try:
            storage.enregistrer_paiement(nom_classe, etudiant, categorie, montant, date_paiement, utilisateur)
            flash("Paiement enregistré avec succès ✅", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
        except Exception as e:
            logging.exception("Erreur lors de l'ajout du paiement")
            flash(f"Erreur : {e}", "error")
            return redirect(request.url)
    df_classes = storage.lire_classes()
    etudiants = df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"].dropna().tolist()
    categories = storage.lire_categories_paiement()["Categorie"].dropna().tolist()
    return render_template(
        "ajouter_paiement.html",
        nom_classe=nom_classe,
        etudiants=etudiants,
        categories=categories
    )


@classes_bp.route("/classes/<nom_classe>/modifier_paiement/<int:paiement_id>", methods=["GET", "POST"])
@login_required
def modifier_paiement(nom_classe, paiement_id):
    df_paiements = storage.lire_paiements()
    paiement = df_paiements[df_paiements["ID"] == paiement_id].to_dict(orient="records")
    paiement = paiement[0] if paiement else None
    if not paiement:
        flash("Paiement introuvable.", "error")
        return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
    if request.method == "POST":
        categorie = request.form.get("categorie", "").strip()
        montant = request.form.get("montant", "").strip()
        date = request.form.get("date_paiement", "").strip()
        if not (categorie and montant and date):
            flash("Tous les champs sont requis.", "error")
            return redirect(request.url)
        try:
            storage.modifier_paiement(paiement_id, categorie, montant, date)
            flash("Paiement modifié avec succès ✅", "success")
            return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
        except Exception as e:
            logging.exception("Erreur lors de la modification du paiement")
            flash(f"Erreur : {e}", "error")
            return redirect(request.url)
    categories = storage.lire_categories_paiement()["Categorie"].dropna().tolist()
    return render_template(
        "modifier_paiement.html",
        nom_classe=nom_classe,
        paiement=paiement,
        categories=categories
    )


@classes_bp.route("/<nom_classe>/ajouter_depense_travail", methods=["GET", "POST"])
@login_required
def ajouter_depense_travail(nom_classe):
    try:
        df_classes = storage.lire_classes()
        if df_classes is None or df_classes.empty:
            etudiants = []
        else:
            df_classes["NomClasse"] = df_classes["NomClasse"].astype(str).str.strip()
            df_classes["Etudiant"] = df_classes["Etudiant"].astype(str).str.strip()
            etudiants = df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"].dropna().drop_duplicates().tolist()
            etudiants.sort()

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

            if etudiant not in etudiants:
                erreurs.append("Étudiant invalide ou non sélectionné.")
            if categorie_travail not in CATEGORIES_TRAVAUX:
                erreurs.append("Catégorie de travail invalide.")
            depenses_valides = [d["nom"] for d in CATEGORIES_TRAVAUX.get(categorie_travail, [])]
            if depense not in depenses_valides:
                erreurs.append("Dépense sélectionnée invalide.")
            try:
                montant = float(montant_raw)
                if montant < 0:
                    erreurs.append("Le montant doit être positif.")
            except ValueError:
                erreurs.append("Montant invalide.")
            if not date_depense:
                erreurs.append("La date de la dépense est obligatoire.")

            if erreurs:
                for err in erreurs:
                    flash(err, "error")
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

            data = {
                "NomClasse": nom_classe,
                "Etudiant": etudiant,
                "CategorieTravail": categorie_travail,
                "TypeDepense": depense,
                "Commentaire": commentaire,
                "Montant": montant,
                "DateDepense": date_depense
            }

            try:
                storage.enregistrer_depense_travail(data)
                flash("Dépense de travail ajoutée avec succès !", "success")
                return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
            except Exception:
                logging.exception("Erreur lors de l'enregistrement d'une dépense de travail")
                flash("Erreur lors de l'enregistrement de la dépense de travail.", "error")
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


@classes_bp.route("/classes/<nom_classe>/pdf/<categorie>")
@login_required
def generer_pdf_categorie(nom_classe, categorie):
    try:
        df_classes = storage.lire_classes()
        df_paiements = storage.lire_paiements()
        etudiants = df_classes[df_classes["NomClasse"] == nom_classe]["Etudiant"].dropna().tolist()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        wrap_style = ParagraphStyle(name="Wrap", fontSize=9, leading=11)  # Petite police pour retour à la ligne

        elements = []
        elements.append(Paragraph(f"Rapport - Classe : {nom_classe}", styles["Title"]))
        elements.append(Spacer(1, 12))

        # --- STATISTIQUES DES PAIEMENTS ---
        elements.append(Paragraph("📊 Statistiques des paiements par catégorie", styles["Heading2"]))

        if df_paiements is not None and not df_paiements.empty:
            paiements_classe = df_paiements[df_paiements["Etudiant"].isin(etudiants)]

            if categorie != "Toutes":
                paiements_classe = paiements_classe[paiements_classe["CategoriePaiement"] == categorie]

            # Calcul nombre paiements par catégorie et somme totale
            stats_count = paiements_classe.groupby("CategoriePaiement")["Montant"].count().reset_index(name="NombrePaiements")
            stats_sum = paiements_classe.groupby("CategoriePaiement")["Montant"].sum().reset_index(name="TotalMontant")

            stats = stats_count.merge(stats_sum, on="CategoriePaiement")

            stats_data = [["Catégorie", "Nombre de paiements", "Total payé (CDF)"]]
            for _, row in stats.iterrows():
                stats_data.append([
                    row["CategoriePaiement"],
                    int(row["NombrePaiements"]),
                    f"{row['TotalMontant']:,}"
                ])
            total_nbr = stats["NombrePaiements"].sum()
            total_mont = stats["TotalMontant"].sum()
            stats_data.append(["TOTAL", int(total_nbr), f"{total_mont:,}"])

            stats_table = Table(stats_data, colWidths=[200, 150, 150])
            stats_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            elements.append(stats_table)

        else:
            elements.append(Paragraph("Aucun paiement enregistré.", styles["Normal"]))

        elements.append(Spacer(1, 20))

        # --- TABLEAU ÉTUDIANTS ---
        elements.append(Paragraph("📋 Liste des étudiants", styles["Heading2"]))

        data = [["N°", "Étudiant", "Paiements", "Commentaires"]]

        for idx, etu in enumerate(etudiants, start=1):
            paiements_etu = df_paiements[df_paiements["Etudiant"] == etu] if df_paiements is not None else None
            if paiements_etu is not None and not paiements_etu.empty:
                paiement_text = ", ".join(
                    [f"{row['CategoriePaiement']}={row['Montant']}" for _, row in paiements_etu.iterrows()]
                )
                commentaire = ", ".join(
                    [str(row.get('Commentaire', '')) for _, row in paiements_etu.iterrows()]
                )
            else:
                paiement_text, commentaire = "Aucun", "—"

            data.append([
                idx,
                Paragraph(etu, wrap_style),
                Paragraph(paiement_text, wrap_style),
                Paragraph(commentaire, wrap_style)
            ])

        table = Table(data, colWidths=[40, 200, 250, 200])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))

        elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{nom_classe}_{categorie}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        logging.exception("Erreur génération PDF")
        flash(f"Impossible de générer le PDF : {e}", "error")
        return redirect(url_for("classes.detail_classe", nom_classe=nom_classe))
