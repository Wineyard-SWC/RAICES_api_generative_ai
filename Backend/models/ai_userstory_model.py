from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List, Union
from datetime import datetime

class UserStoryResponse(BaseModel):
    """Modelo para respuestas estructuradas de historias de usuario generadas por IA."""

    status: Literal["HISTORIAS_GENERADAS", "INFORMACION_INSUFICIENTE", "ERROR_PROCESAMIENTO", "RESPUESTA_GENERAL"] = Field(
        description="Estado de la respuesta generada"
    )
    query: str = Field(default="", description="Consulta original del usuario")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Momento en que se generó la respuesta"
    )
    content: Union[List[Dict], str] = Field(
        description="Contenido principal de la respuesta (HU generadas o mensaje explicativo)"
    )
    missing_info: Optional[List[str]] = Field(
        default=None,
        description="Lista de información adicional requerida cuando el status es INFORMACION_INSUFICIENTE"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Metadatos adicionales sobre la respuesta"
    )

    def _format_user_stories(self, stories: List[Dict]) -> List[Dict]:
        """
        Reformatea el ID de cada HU al formato HU-### y asegura estructura correcta.
        """
        formatted = []
        for i, story in enumerate(stories, 1):
            new_story = story.copy()
            new_story["id"] = f"HU-{i:03d}"
            if not isinstance(new_story.get("acceptance_criteria"), list):
                new_story["acceptance_criteria"] = []
            formatted.append(new_story)
        return formatted

    def format_response(self) -> str:
        if isinstance(self.content, list):
            self.content = self._format_user_stories(self.content)
        return self.model_dump_json(indent=4)
