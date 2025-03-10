# Standard library imports

# Third-party imports

# Local application imports
#Rutas de la IA generativa
from .req_routes_ia import router as ia_req_router   
from .epic_routes_ia import router as ia_epic_router
#Rutas default de la app
from .app_routes import router as app_router       # <--- Cambiar name por el nombre de la ruta.py

