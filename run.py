import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5008))

    try:
        print(f"Démarrage de l'application sur le port {port} (debug={debug_mode})...")
        app.run(debug=debug_mode, port=port, host="0.0.0.0")
    except Exception as e:
        print(f"Erreur lors du démarrage de l'application : {e}")
