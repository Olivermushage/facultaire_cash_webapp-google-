from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from urllib.parse import urlparse, urljoin
from functools import wraps
from ..models.user import get_user_by_username, create_user

auth_bp = Blueprint("auth", __name__, template_folder="templates/auth")


# === Helpers ===
def is_safe_url(target):
    """Vérifie si l'URL est sûre pour la redirection."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def login_required(f):
    """Décorateur simple pour protéger les routes (sans Flask-Login)."""
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if "user" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_view


def admin_required(f):
    """Décorateur pour protéger les routes réservées aux admins."""
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Accès réservé aux administrateurs.", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated_view


# === Routes ===
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password.strip():
            flash("Nom d'utilisateur et mot de passe requis.", "error")
            return redirect(url_for("auth.login"))

        user = get_user_by_username(username)
        if user is None or not check_password_hash(user["password"], password):
            flash("Nom d'utilisateur ou mot de passe incorrect.", "error")
            return redirect(url_for("auth.login"))

        # Mettre en session les infos utilisateur
        session.clear()
        session["user"] = username
        session["role"] = user.get("role", "user")

        flash(f"Bienvenue {username} ! Connexion réussie.", "success")

        # Gestion de la redirection post-login
        next_page = request.args.get("next")
        if not next_page or not is_safe_url(next_page):
            next_page = url_for("main.index")
        return redirect(next_page)

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Vous avez été déconnecté avec succès.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/create_user", methods=["GET", "POST"])
@login_required
@admin_required
def create_user_route():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user").strip()

        if not username:
            flash("Le nom d'utilisateur est requis.", "error")
            return redirect(url_for("auth.create_user_route"))

        if not password.strip():
            flash("Le mot de passe est requis.", "error")
            return redirect(url_for("auth.create_user_route"))

        if role not in {"user", "admin"}:
            flash("Rôle invalide fourni (doit être 'user' ou 'admin').", "error")
            return redirect(url_for("auth.create_user_route"))

        try:
            create_user(username, password, role)
            flash(f"Utilisateur '{username}' créé avec succès.", "success")
            return redirect(url_for("main.index"))
        except ValueError:
            flash("Cet utilisateur existe déjà.", "error")
            return redirect(url_for("auth.create_user_route"))
        except Exception as e:
            flash(f"Erreur lors de la création : {e}", "error")
            return redirect(url_for("auth.create_user_route"))

    return render_template("create_user.html")
