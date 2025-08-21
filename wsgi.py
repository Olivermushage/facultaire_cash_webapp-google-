# wsgi.py
from app import create_app  # ou l'import qui convient chez toi
app = create_app()

# Si tu n'as pas de factory, fais plutôt :
# from app import app
# (et supprime les deux lignes au-dessus)
