# Standard library imports

# Third-party imports

# Local application imports
#Rutas de la IA generativa
from .req_routes_ia import router as ia_req_router   
from .epic_routes_ia import router as ia_epic_router
#Rutas default de la app
from .app_routes import router as app_router       # <--- Cambiar name por el nombre de la ruta.py
#Rutas de acceso a datos de firebase
from .epic_routes import router as epic_router  
from .users_routes import router as user_router 
from .projects_routes import router as project_router 
from .project_users_routes import router as project_user_router 

