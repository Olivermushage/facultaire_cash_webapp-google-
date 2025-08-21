import os
from flask import Flask, session
from .config import Config

def create_app():
    """Créer et configurer l'application Flask."""
    
    # Création de l'application Flask avec dossiers templates et static personnalisés
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    # Charger la configuration depuis Config ou variables d'environnement
    app.config.from_object(Config)

    # Initialisation des fichiers Excel nécessaires
    from .models.storage import init_all_files
    init_all_files()

    # Import et enregistrement des Blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.classes import classes_bp
    from .routes.depenses import depenses_bp
    from .routes.recettes import recettes_bp
    from .routes.categories import categories_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(classes_bp, url_prefix="/classes")
    app.register_blueprint(depenses_bp, url_prefix="/depenses")
    app.register_blueprint(recettes_bp, url_prefix="/recettes")
    app.register_blueprint(categories_bp, url_prefix="/categories")

    # Création automatique de l'administrateur par défaut s'il n'existe pas
    from .models.user import create_admin_default
    create_admin_default()

    # Injection de current_user personnalisé pour les templates
    @app.context_processor
    def inject_user():
        class CurrentUser:
            def __init__(self, username=None, role=None):
                self.username = username
                self.role = role

            @property
            def is_authenticated(self):
                return self.username is not None

        user = CurrentUser(
            username=session.get("user"),
            role=session.get("role")
        )
        return dict(current_user=user)

    return app
