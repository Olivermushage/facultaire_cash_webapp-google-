import os
from modules.excel_backend import load_workbook_for_classe

DATA_DIR = "data/classes"
FILE_EXT = ".xlsx"

def add_students(classe_name, raw_text):
    filepath = os.path.join(DATA_DIR, f"{classe_name}{FILE_EXT}")

    try:
        wb = load_workbook_for_classe(classe_name)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Fichier Excel pour la classe '{classe_name}' non trouvé : {filepath}") from e
    except Exception as e:
        raise IOError(f"Erreur lors du chargement du fichier Excel '{filepath}': {e}") from e

    if 'Étudiants' not in wb.sheetnames:
        raise ValueError(f"La feuille 'Étudiants' est absente du fichier '{filepath}'")

    ws = wb['Étudiants']

    # Nettoyer et splitter
    lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]

    # Normaliser existants en minuscules sans espaces superflus
    existing_names = [
        (row[0].value.strip().lower() if isinstance(row[0].value, str) else "")
        for row in ws.iter_rows(min_row=2) if row[0].value
    ]

    added_count = 0
    for name in lines:
        name_norm = name.lower()
        if name_norm not in existing_names:
            ws.append([name])
            existing_names.append(name_norm)
            added_count += 1

    wb.save(filepath)
    return added_count
