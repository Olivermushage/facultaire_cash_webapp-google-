import os

class Config:
    # Clé secrète Flask (sessions, cookies)
    SECRET_KEY = os.environ.get("SECRET_KEY", "gN9v!2mLzXqPp7&4sRfT")

    # Chemin vers le fichier JSON des identifiants du compte de service Google
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "path/to/service_account.json")

    # ID de la feuille Google Sheets principale
    GOOGLE_SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "votre_spreadsheet_id_ici")

    # Scopes Google API nécessaires pour accéder aux Sheets et Drive
    GOOGLE_API_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
