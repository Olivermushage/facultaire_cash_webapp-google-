import os
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

def get_gs_client():
    # Si GOOGLE_APPLICATION_CREDENTIALS pointe vers le JSON, gspread s'en charge
    creds = Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)
