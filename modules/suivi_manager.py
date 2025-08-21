import os
import logging
from modules.excel_backend import load_workbook_for_classe

DATA_DIR = "data/classes"
FILE_EXT = ".xlsx"

def _get_classe_filepath(classe_name):
    return os.path.join(DATA_DIR, f"{classe_name}{FILE_EXT}")

def update_suivi(classe_name, student_name, category):
    filepath = _get_classe_filepath(classe_name)
    try:
        wb = load_workbook_for_classe(classe_name)
    except FileNotFoundError:
        logging.error(f"Fichier classe non trouvé : {filepath}")
        raise
    except Exception as e:
        logging.error(f"Erreur chargement workbook classe '{classe_name}': {e}")
        raise

    if 'Suivi' not in wb.sheetnames:
        raise ValueError(f"La feuille 'Suivi' est absente dans le fichier de la classe '{classe_name}'.")

    ws = wb['Suivi']

    header = [cell.value for cell in ws[1]]
    if category not in header:
        raise ValueError(f"La catégorie '{category}' n'existe pas dans la feuille 'Suivi'.")

    category_col = header.index(category) + 1

    # Cherche la ligne de l'étudiant (comparaison normalisée)
    student_name_norm = student_name.strip().lower()
    found = False
    for row in ws.iter_rows(min_row=2):
        cell_value = row[0].value
        if isinstance(cell_value, str) and cell_value.strip().lower() == student_name_norm:
            row[category_col - 1].value = "Payé"
            found = True
            break

    # Si pas trouvé, ajoute une nouvelle ligne
    if not found:
        new_row = [""] * len(header)
        new_row[0] = student_name.strip()
        new_row[category_col - 1] = "Payé"
        ws.append(new_row)

    wb.save(filepath)


def get_suivi_data(classe_name):
    filepath = _get_classe_filepath(classe_name)
    try:
        wb = load_workbook_for_classe(classe_name)
    except FileNotFoundError:
        logging.error(f"Fichier classe non trouvé : {filepath}")
        raise
    except Exception as e:
        logging.error(f"Erreur chargement workbook classe '{classe_name}': {e}")
        raise

    if 'Suivi' not in wb.sheetnames:
        raise ValueError(f"La feuille 'Suivi' est absente dans le fichier de la classe '{classe_name}'.")

    ws = wb['Suivi']

    headers = [cell.value for cell in ws[1]]
    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        student = row[0]
        paiements = dict(zip(headers[1:], row[1:]))
        data.append({'student': student, 'paiements': paiements})

    return headers[1:], data
