from app.models.user import create_user, get_user_by_username

# Crée un utilisateur normal
try:
    create_user("user1", "UserPass123", role="user")
    print("Utilisateur 'user1' créé avec succès !")
except ValueError:
    print("Utilisateur 'user1' existe déjà.")

# Vérifie qu'il est bien dans users.json
user = get_user_by_username("user1")
if user:
    print(f"Utilisateur chargé : {user.id}, rôle : {user.role}")
else:
    print("Utilisateur non trouvé.")

if user.verify_password("UserPass123"):
    print("Connexion réussie !")
else:
    print("Nom d'utilisateur ou mot de passe incorrect.")
