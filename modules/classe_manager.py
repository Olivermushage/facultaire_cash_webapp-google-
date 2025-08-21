import os
import shutil
import logging
import re

DATA_DIR = 'data/classes'
MODELE_PATH = 'templates/ClasseModele.xlsx'
FILE_EXTENSION = '.xlsx'

# Expression régulière simple pour valider un nom de classe (lettres, chiffres, espaces, underscore, tiret)
CLASSNAME_REGEX = re.compile(r'^[\w\s-]+$')

def is_valid_classname(name):
    return bool(name) and CLASSNAME_REGEX.match(name) is not None

def create_classe(name):
    """
    Crée une nouvelle classe en copiant le modèle Excel.
    Retourne un tuple (success: bool, message: str)
    """
    if not is_valid_classname(name):
        return False, "Nom de classe invalide. Veuillez utiliser uniquement des lettres, chiffres, espaces, tirets ou underscores."

    os.makedirs(DATA_DIR, exist_ok=True)
    new_path = os.path.join(DATA_DIR, f"{name}{FILE_EXTENSION}")

    if os.path.exists(new_path):
        return False, f"La classe « {name} » existe déjà."

    try:
        shutil.copy(MODELE_PATH, new_path)
        return True, f"La classe « {name} » a été créée avec succès."
    except Exception as e:
        logging.error(f"Erreur lors de la création de la classe '{name}': {e}", exc_info=True)
        return False, f"Erreur lors de la création de la classe : {str(e)}"


def list_classes():
    """
    Liste les classes disponibles dans le dossier data/classes, triées alphabétiquement.
    """
    if not os.path.exists(DATA_DIR):
        return []
    classes = [f[:-len(FILE_EXTENSION)] for f in os.listdir(DATA_DIR) if f.endswith(FILE_EXTENSION)]
    return sorted(classes)


def delete_classe(name):
    """
    Supprime la classe par nom (fichier Excel).
    Retourne un tuple (success: bool, message: str)
    """
    path = os.path.join(DATA_DIR, f"{name}{FILE_EXTENSION}")

    if not os.path.exists(path):
        return False, f"La classe « {name} » n'existe pas."

    try:
        os.remove(path)
        return True, f"La classe « {name} » a été supprimée avec succès."
    except Exception as e:
        logging.error(f"Erreur lors de la suppression de la classe '{name}': {e}", exc_info=True)
        return False, f"Erreur lors de la suppression de la classe : {str(e)}"
