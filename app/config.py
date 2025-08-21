import os
import pandas as pd

class Config:
    # Clé secrète Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "gN9v!2mLzXqPp7&4sRfT")
    
    # Répertoire racine et dossier de données
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_FOLDER = os.environ.get("DATA_FOLDER", os.path.join(BASE_DIR, "data"))

    # Chemins vers les fichiers Excel
    CLASSES_FILE = os.path.join(DATA_FOLDER, "classes.xlsx")
    PAIEMENTS_FILE = os.path.join(DATA_FOLDER, "paiements.xlsx")
    DEPENSES_FILE = os.path.join(DATA_FOLDER, "depenses.xlsx")
    COURS_FILE = os.path.join(DATA_FOLDER, "cours_par_classe.xlsx")
    COMMENTS_FILE = os.path.join(DATA_FOLDER, "comments.xlsx")
    TRAVAUX_DEPENSES_FILE = os.path.join(DATA_FOLDER, "depenses_travaux.xlsx")
    AUTRES_RECETTES_FILE = os.path.join(DATA_FOLDER, "autres_recettes.xlsx")
    CATEGORIES_PAIEMENT_FILE = os.path.join(DATA_FOLDER, "categories_paiement.xlsx")
    CATEGORIES_DEPENSE_FILE = os.path.join(DATA_FOLDER, "categories_depense.xlsx")
    RECETTES_FILE = os.path.join(DATA_FOLDER, "recettes.xlsx")
    CAISSE_FILE = os.path.join(DATA_FOLDER, "caisse.xlsx")

    @staticmethod
    def ensure_excel_file(path, columns):
        """
        Crée un fichier Excel avec colonnes spécifiées s'il n'existe pas.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            df = pd.DataFrame(columns=columns)
            df.to_excel(path, index=False)

    @classmethod
    def init_all_files(cls):
        """Initialise tous les fichiers Excel nécessaires."""
        cls.ensure_excel_file(cls.CLASSES_FILE, ["NomClasse", "Etudiant"])
        cls.ensure_excel_file(cls.PAIEMENTS_FILE, ["NomClasse", "Etudiant", "CategoriePaiement", "Montant", "DatePaiement"])
        cls.ensure_excel_file(cls.DEPENSES_FILE, ["NomClasse", "DateExamen", "CategorieDepense", "Description", "Montant", "TypeDepense", "Commentaire", "DateDepense"])
        cls.ensure_excel_file(cls.COURS_FILE, ["NomClasse", "NomCours"])
        cls.ensure_excel_file(cls.COMMENTS_FILE, ["NomClasse", "Etudiant", "Commentaire", "Auteur", "Date"])
        cls.ensure_excel_file(cls.TRAVAUX_DEPENSES_FILE, ["NomClasse", "Etudiant", "CategorieTravail", "TypeDepense", "Commentaire", "Montant", "DateDepense"])
        cls.ensure_excel_file(cls.AUTRES_RECETTES_FILE, ["Date", "NomClasse", "Etudiant", "CategoriePaiement", "Montant", "Description"])
        cls.ensure_excel_file(cls.CATEGORIES_PAIEMENT_FILE, ["Categorie"])
        cls.ensure_excel_file(cls.CATEGORIES_DEPENSE_FILE, ["Categorie"])
        cls.ensure_excel_file(cls.RECETTES_FILE, ["Date", "Source", "Type", "Description", "Montant"])
        cls.ensure_excel_file(cls.CAISSE_FILE, ["Date", "Nom", "Type", "Montant", "Description"])
