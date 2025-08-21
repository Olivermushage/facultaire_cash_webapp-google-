import os
import json
from werkzeug.security import generate_password_hash

# Dossier et fichier pour stocker les utilisateurs
DATA_FOLDER = "data"
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")


def create_admin_user():
    """Crée l'utilisateur administrateur avec un mot de passe haché pbkdf2:sha256."""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    password_clear = "AdminPass123"

    # Hachage compatible avec check_password_hash
    password_hash = generate_password_hash(password_clear, method="pbkdf2:sha256")

    admin_user = [
        {
            "username": "admin",
            "password": password_hash,
            "role": "admin"
        }
    ]

    # Sauvegarde dans users.json
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(admin_user, f, indent=2, ensure_ascii=False)

    print(f"Fichier {USERS_FILE} créé avec l'utilisateur administrateur.")
    print(f"Nom d'utilisateur : admin")
    print(f"Mot de passe (clair) : {password_clear}")


if __name__ == "__main__":
    create_admin_user()
