import os
import webbrowser
import threading
from app import create_app

def open_browser(port):
    """Ouvre automatiquement le navigateur sur le bon port."""
    url = f"http://127.0.0.1:{port}"
    print(f"Ouverture du navigateur à {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    # Création de l'application
    app = create_app()

    # Lecture des variables d'environnement
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5008))

    print(f"Démarrage de l'application sur http://127.0.0.1:{port} (debug={debug_mode})")

    # Ouvrir le navigateur automatiquement seulement en debug
    if debug_mode:
        threading.Timer(1.0, open_browser, args=(port,)).start()

    try:
        # Lancement de l'application Flask
        app.run(debug=debug_mode, port=port, host="0.0.0.0", use_reloader=debug_mode)
    except Exception as e:
        print(f"Erreur lors du démarrage de l'application : {e}")
