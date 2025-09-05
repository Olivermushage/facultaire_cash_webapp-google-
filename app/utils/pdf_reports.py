from fpdf import FPDF

def generate_payment_report_pdf(nom_classe, motif_paiement, etudiants_paiements):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # En-tête
    pdf.cell(0, 10, f"Rapport de paiement - Classe : {nom_classe}", ln=True, align='C')
    pdf.cell(0, 10, f"Motif : {motif_paiement}", ln=True, align='C')
    pdf.ln(10)

    # Tableau en-tête
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(10, 10, "N°", border=1)
    pdf.cell(100, 10, "Étudiant", border=1)
    pdf.cell(40, 10, "Statut Paiement", border=1)
    pdf.ln()

    # Contenu tableau
    pdf.set_font("Arial", '', 12)
    for i, (etudiant, statut) in enumerate(etudiants_paiements.items(), 1):
        pdf.cell(10, 10, str(i), border=1)
        pdf.cell(100, 10, etudiant, border=1)
        pdf.cell(40, 10, statut, border=1)
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, "- Fin du rapport -", align='C')

    return pdf.output(dest='S').encode('latin1')
