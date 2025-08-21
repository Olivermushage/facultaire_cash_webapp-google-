import os
from modules.excel_backend import load_workbook_for_classe

DATA_DIR = "data/classes"
FILE_EXT = ".xlsx"

def add_paiement(classe_name, category, amount):
    if not category or not isinstance(category, str):
        raise ValueError("La catégorie doit être une chaîne non vide.")

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        raise ValueError("Le montant doit être un nombre valide.")

    if amount <= 0:
        raise ValueError("Le montant doit être strictement positif.")

    filepath = os.path.join(DATA_DIR, f"{classe_name}{FILE_EXT}")
    wb = load_workbook_for_classe(classe_name)
    ws = wb['Paiements']

    # Récupérer les catégories existantes (colonne A) à partir de la ligne 2
    existing_categories = [row[0].value for row in ws.iter_rows(min_row=2) if row[0].value is not None]

    if category not in existing_categories:
        # Ajouter la nouvelle ligne dans Paiements
        ws.append([category, amount])

        # Mise à jour de la feuille Suivi
        suivi_ws = wb['Suivi']

        # Trouver la dernière colonne utilisée dans la première ligne (en-têtes)
        max_col = suivi_ws.max_column
        # Lire tous les en-têtes existants dans la première ligne
        headers = [suivi_ws.cell(row=1, column=col).value for col in range(1, max_col + 1)]

        # Si la catégorie n'existe pas déjà en en-tête, ajouter à la fin
        if category not in headers:
            suivi_ws.cell(row=1, column=max_col + 1, value=category)

        # Note : ne pas gérer la ligne 1 vide, car openpyxl crée toujours une ligne par défaut.

    wb.save(filepath)
