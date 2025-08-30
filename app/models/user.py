# app/models/users.py
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

# Dossiers et fichiers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "..", "data")
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")


def _ensure_users_file():
    """Assure que le dossier et le fichier utilisateurs existent."""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)


def load_users():
    """Charge la liste des utilisateurs depuis users.json."""
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
    """Enregistre la liste des utilisateurs dans users.json."""
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_list, f, indent=2, ensure_ascii=False)


def get_user_by_username(username):
    """Retourne le dictionnaire utilisateur si trouvé, sinon None."""
    users = load_users()
    for user in users:
        if user.get("username") == username:
            return user
    return None


def create_user(username, password, role="user"):
    """Crée un nouvel utilisateur et l'ajoute au fichier JSON."""
    if get_user_by_username(username):
        raise ValueError(f"Utilisateur '{username}' déjà existant.")
    
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    user = {
        "username": username,
        "password": hashed_password,
        "role": role
    }
    users = load_users()
    users.append(user)
    save_users(users)
    return user


def create_admin_default():
    """Crée un admin par défaut si aucun n'existe."""
    users = load_users()
    admin_exists = any(u.get("role") == "admin" for u in users)
    if not admin_exists:
        admin_password = "adminFST@=="  # À sécuriser en prod
        admin_user = {
            "username": "admin",
            "password": generate_password_hash(admin_password, method="pbkdf2:sha256"),
            "role": "admin"
        }
        users.append(admin_user)
        save_users(users)
        print(f"[INFO] Admin créé : username='admin', mot de passe clair : {admin_password}")
    else:
        print("[INFO] Un utilisateur admin existe déjà.")


# ===============================
# Classe User simple pour Flask-Login
# ===============================
class User:
    """Objet User minimal pour Flask-Login."""
    def __init__(self, username, role="user"):
        self.username = username
        self.role = role

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    def check_password(self, password):
        """Vérifie le mot de passe en clair."""
        user_data = get_user_by_username(self.username)
        if not user_data:
            return False
        return check_password_hash(user_data["password"], password)
