from flask import Blueprint, request, redirect, url_for, flash, session, render_template
from flask import send_file
from app.models.storage_gsheets import (
    get_students_for_class,
    get_payment_status,
    update_student_payment,
    get_payment_summary,
    enregistrer_paiement_google,
    generate_summary_pdf
)

inscription_bp = Blueprint('inscription', __name__, url_prefix='/inscription')

@inscription_bp.route('/selection_type', methods=['GET', 'POST'])
def selection_type():
    if request.method == 'POST':
        type_inscription = request.form.get('type_inscription')
        if type_inscription not in ('1er_semestre', '2nd_semestre', 'rattrapage'):
            flash("Veuillez sélectionner un type d'inscription valide.", "error")
            return render_template('selection_type_inscription.html')
        session['type_inscription'] = type_inscription
        return redirect(url_for('inscription.selection_classe'))
    return render_template('selection_type_inscription.html')




@inscription_bp.route('/selection_classe', methods=['GET', 'POST'])
def selection_classe():
    from app.models.storage_gsheets import lire_classes  # Import local pour éviter problème circulaire

    # Lire les données de la feuille Classes dans un DataFrame
    df_classes = lire_classes()

    # Nettoyer les noms de colonnes pour éviter soucis d'espaces invisibles
    df_classes.columns = df_classes.columns.str.strip()

    # Extraire la liste unique des noms de classes triée et nettoyée
    classes = df_classes['NomClasse'].drop_duplicates().sort_values().tolist()
    classes_clean = [c.strip() for c in classes]

    if request.method == 'POST':
        nom_classe = request.form.get('classe')
        if nom_classe:
            nom_classe = nom_classe.strip()

        # Vérifier si la classe choisie est bien dans la liste nettoyée
        if not nom_classe or nom_classe not in classes_clean:
            flash("Veuillez sélectionner une classe valide.", "error")
            return render_template('selection_classe.html', classes=classes)

        # Stocker la classe valide en session
        session['nom_classe'] = nom_classe
        return redirect(url_for('inscription.liste_etudiants'))

    # En GET : afficher la liste des classes dans le formulaire
    return render_template('selection_classe.html', classes=classes)




@inscription_bp.route('/liste_etudiants', methods=['GET', 'POST'])
def liste_etudiants():
    nom_classe = session.get('nom_classe')
    type_inscription = session.get('type_inscription')

    if not nom_classe or not type_inscription:
        flash("Veuillez d'abord sélectionner le type d'inscription et la classe.", "error")
        return redirect(url_for('inscription.selection_type'))

    if request.method == 'POST':
        etudiant = request.form.get('etudiant')
        if etudiant:
            paiement_existe = get_payment_status(nom_classe, etudiant, type_inscription)
            if paiement_existe == "Payé":
                flash(f"Le paiement pour {etudiant} est déjà enregistré.", "error")
            else:
                try:
                    update_student_payment(nom_classe, etudiant, type_inscription, montant=10.0)
                    flash(f"Paiement de 10 USD enregistré pour {etudiant}.", "success")
                except Exception as e:
                    flash(f"Erreur lors de l'enregistrement du paiement : {e}", "error")
            return redirect(url_for('inscription.liste_etudiants'))

    etudiants = get_students_for_class(nom_classe)
    etudiants_paiements = {
        etudiant: get_payment_status(nom_classe, etudiant, type_inscription)
        for etudiant in etudiants
    }

    return render_template(
        'liste_etudiants.html',
        nom_classe=nom_classe,
        etudiants_paiements=etudiants_paiements,
    )


from flask import flash, redirect, request, session, url_for
from app.models.storage_gsheets import enregistrer_paiement_google, get_payment_status

@inscription_bp.route('/enregistrer_paiement', methods=['POST'])
def enregistrer_paiement():
    nom_classe = session.get('nom_classe')
    type_inscription = session.get('type_inscription')
    etudiant = request.form.get('etudiant')

    if not nom_classe or not type_inscription or not etudiant:
        flash("Informations manquantes pour enregistrer le paiement.", "error")
        return redirect(url_for('inscription.liste_etudiants'))

    # Vérifier si paiement déjà fait
    paiement_existe = get_payment_status(nom_classe, etudiant, type_inscription)
    if paiement_existe == "Payé":
        flash(f"Le paiement pour {etudiant} est déjà enregistré.", "error")
        return redirect(url_for('inscription.liste_etudiants'))

    try:
        # Enregistrer un paiement de 10 dans la feuille Paiements_Inscriptions
        success = enregistrer_paiement_google(nom_classe, etudiant, type_inscription, montant=10.0)
        if success:
            flash(f"Paiement de 10 USD enregistré pour {etudiant}.", "success")
        else:
            flash("Erreur lors de l'enregistrement du paiement.", "error")
    except Exception as e:
        flash(f"Erreur lors de l'enregistrement du paiement : {e}", "error")

    return redirect(url_for('inscription.liste_etudiants'))


@inscription_bp.route('/statistiques', methods=['GET', 'POST'])
def statistiques():
    from app.models.storage_gsheets import get_payment_summary, toggle_payment_status

    nom_classe = session.get('nom_classe')
    type_inscription = session.get('type_inscription')
    user_role = session.get('role')

    if not nom_classe or not type_inscription:
        flash("Veuillez d'abord sélectionner le type d'inscription et la classe.", "error")
        return redirect(url_for('inscription.selection_type'))

    # Récupération des stats depuis le module de stockage
    summary = get_payment_summary(nom_classe, type_inscription)  
    # summary attendu comme dict: {'payes': int, 'non_payes': int, 'total_recettes': float}

    # Gestion admin : toggle statut paiement
    if request.method == 'POST' and user_role == 'admin':
        etudiant = request.form.get('etudiant')
        action = request.form.get('action')
        if etudiant and action in ['MarquerPayé', 'MarquerNonPayé']:
            new_status = "Payé" if action == 'MarquerPayé' else "Non payé"
            try:
                toggle_payment_status(nom_classe, etudiant, type_inscription, new_status)
                flash(f"Le statut de paiement pour {etudiant} a été mis à jour.", "success")
            except Exception as e:
                flash(f"Erreur lors de la mise à jour : {e}", "error")
            return redirect(url_for('inscription.statistiques'))

    return render_template(
        'statistiques.html',
        nom_classe=nom_classe,
        type_inscription=type_inscription,
        summary=summary,
        is_admin=(user_role == 'admin'),
    )


@inscription_bp.route('/generer_pdf')
def generer_pdf():
    nom_classe = session.get('nom_classe')
    type_inscription = session.get('type_inscription')

    if not nom_classe or not type_inscription:
        flash("Veuillez sélectionner une classe et type d'inscription avant de générer le PDF.", "error")
        return redirect(url_for('inscription.selection_type'))

    summary = get_payment_summary(nom_classe, type_inscription)
    pdf_buffer = generate_summary_pdf(summary, nom_classe, type_inscription)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Résumé_paiements_{nom_classe}_{type_inscription}.pdf"
    )

