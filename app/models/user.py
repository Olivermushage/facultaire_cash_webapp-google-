import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

# Chemins vers le dossier et fichier utilisateurs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "..", "data")
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")

def _ensure_users_file():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)


def create_admin_default():
    users = load_users()
    # Vérifier si un admin existe déjà
    admin_exists = any(u.get("role") == "admin" for u in users)
    if not admin_exists:
        admin_password = "adminFST@=="  # À modifier en environnement sécurisé
        admin_user = {
            "username": "admin",
            "password": generate_password_hash(admin_password, method="pbkdf2:sha256"),
            "role": "admin"
        }
        users.append(admin_user)
        save_users(users)
        print(f"Utilisateur admin créé avec mot de passe clair : {admin_password}")
    else:
        print("Un utilisateur admin existe déjà.")


def load_users():
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    return data

def save_users(users_list):
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_list, f, indent=2, ensure_ascii=False)

def get_user_by_username(username):
    users = load_users()
    for user in users:
        if user.get("username") == username:
            return user
    return None

def create_user(username, password, role="user"):
    users = load_users()
    if any(u.get("username") == username for u in users):
        raise ValueError("Utilisateur déjà existant")
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    user = {
        "username": username,
        "password": hashed_password,
        "role": role
    }
    users.append(user)
    save_users(users)
    return user
