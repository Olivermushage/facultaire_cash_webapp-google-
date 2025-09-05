from flask import Blueprint, request, redirect, url_for, flash, session, render_template, send_file
from app.models.storage_gsheets import (
    lire_classes,
    get_students_for_class,
    get_payment_status_travaux,
    update_student_payment_travaux,
    enregistrer_paiement_travaux,
    generate_summary_pdf_travaux,
)

travaux_bp = Blueprint('travaux', __name__, url_prefix='/travaux')

from io import BytesIO
from app.models.storage_gsheets import get_payment_summary_travaux  # fonction à créer pour travaux


@travaux_bp.route('/selection_type', methods=['GET', 'POST'])
def selection_type():
    types_travaux_possibles = ['Projet tutoré', 'Stage', 'Mémoire']

    if request.method == 'POST':
        type_travail = request.form.get('type_travail')
        if type_travail not in types_travaux_possibles:
            flash("Veuillez sélectionner un type de travail valide.", "error")
            return render_template('selection_type_travaux.html', types=types_travaux_possibles)
        session['type_travail'] = type_travail
        return redirect(url_for('travaux.selection_classe'))
    return render_template('selection_type_travaux.html', types=types_travaux_possibles)


@travaux_bp.route('/selection_classe', methods=['GET', 'POST'])
def selection_classe():
    df_classes = lire_classes()
    classes = df_classes['NomClasse'].drop_duplicates().sort_values().tolist()

    if request.method == 'POST':
        nom_classe = request.form.get('classe')
        if nom_classe:
            nom_classe = nom_classe.strip()  # retirer espaces avant/après

        # On uniformise la casse pour comparaison
        classes_clean = [c.strip() for c in classes]

        if not nom_classe or nom_classe not in classes_clean:
            flash("Veuillez sélectionner une classe valide.", "error")
            return render_template('selection_classe_travaux.html', classes=classes)

        session['nom_classe'] = nom_classe
        return redirect(url_for('travaux.liste_etudiants'))

    return render_template('selection_classe_travaux.html', classes=classes)



@travaux_bp.route('/liste_etudiants', methods=['GET', 'POST'])
def liste_etudiants():
    nom_classe = session.get('nom_classe')
    type_travail = session.get('type_travail')

    if not nom_classe or not type_travail:
        flash("Veuillez d'abord sélectionner le type de travail et la classe.", "error")
        return redirect(url_for('travaux.selection_type'))

    if request.method == 'POST':
        etudiant = request.form.get('etudiant')
        if etudiant:
            paiement_existe = get_payment_status_travaux(nom_classe, etudiant, type_travail)
            if paiement_existe == "Payé":
                flash(f"Le paiement pour {etudiant} est déjà enregistré.", "error")
            else:
                try:
                    montant = 10.0 if type_travail in ['Projet tutoré', 'Stage'] else 150.0
                    update_student_payment_travaux(nom_classe, etudiant, type_travail, montant)
                    flash(f"Paiement de {montant} USD enregistré pour {etudiant}.", "success")
                except Exception as e:
                    flash(f"Erreur lors de l'enregistrement du paiement : {e}", "error")
            return redirect(url_for('travaux.liste_etudiants'))

    etudiants = get_students_for_class(nom_classe)
    etudiants_paiements = {
        etudiant: get_payment_status_travaux(nom_classe, etudiant, type_travail)
        for etudiant in etudiants
    }

    return render_template(
        'liste_etudiants_travaux.html',
        nom_classe=nom_classe,
        etudiants_paiements=etudiants_paiements,
        type_travail=type_travail
    )


@travaux_bp.route('/enregistrer_paiement', methods=['POST'])
def enregistrer_paiement():
    nom_classe = session.get('nom_classe')
    type_travail = session.get('type_travail')
    etudiant = request.form.get('etudiant')

    if not nom_classe or not type_travail or not etudiant:
        flash("Informations manquantes pour enregistrer le paiement.", "error")
        return redirect(url_for('travaux.liste_etudiants'))

    paiement_existe = get_payment_status_travaux(nom_classe, etudiant, type_travail)
    if paiement_existe == "Payé":
        flash(f"Le paiement pour {etudiant} est déjà enregistré.", "error")
        return redirect(url_for('travaux.liste_etudiants'))

    try:
        montant = 10.0 if type_travail in ['Projet tutoré', 'Stage'] else 150.0
        success = enregistrer_paiement_travaux(nom_classe, etudiant, type_travail, montant)
        if success:
            flash(f"Paiement de {montant} USD enregistré pour {etudiant}.", "success")
        else:
            flash("Erreur lors de l'enregistrement du paiement.", "error")
    except Exception as e:
        flash(f"Erreur lors de l'enregistrement du paiement : {e}", "error")

    return redirect(url_for('travaux.liste_etudiants'))



@travaux_bp.route('/suivi_paiements', methods=['GET', 'POST'])
def suivi_paiements():
    options_paiement = [
        ('inscriptions', 'Paiement Inscriptions'),
        ('travaux', 'Paiement Travaux'),
    ]

    if request.method == 'POST':
        choix = request.form.get('type_paiement')
        if choix == 'inscriptions':
            return redirect(url_for('inscription.selection_type'))  # route à définir
        elif choix == 'travaux':
            return redirect(url_for('travaux.selection_type'))
        else:
            flash("Veuillez choisir un type de paiement valide.", "error")

    return render_template('suivi_paiements.html', options=options_paiement)



from flask import session, flash, redirect, url_for, send_file, current_app
from io import BytesIO

@travaux_bp.route('/generer_pdf')
def travaux_generer_pdf():
    nom_classe = session.get('nom_classe')
    type_travail = session.get('type_travail')

    if not nom_classe or not type_travail:
        flash("Veuillez sélectionner une classe et type de travail avant de générer le PDF.", "error")
        return redirect(url_for('travaux.selection_type'))

    # Debug
    current_app.logger.debug(f"travaux_generer_pdf : nom_classe={nom_classe}, type_travail={type_travail}")

    summary = get_payment_summary_travaux(nom_classe, type_travail)

    # Debug : vérifier le contenu
    current_app.logger.debug(f"Résumé paiements : {summary}")

    pdf_buffer = generate_summary_pdf_travaux(summary, nom_classe, type_travail)

    if not isinstance(pdf_buffer, BytesIO):
        current_app.logger.error("generate_summary_pdf_travaux doit retourner un BytesIO")
        flash("Erreur interne lors de la génération du PDF.", "error")
        return redirect(url_for('travaux.selection_type'))

    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Résumé_paiements_{nom_classe}_{type_travail}.pdf"
    )


