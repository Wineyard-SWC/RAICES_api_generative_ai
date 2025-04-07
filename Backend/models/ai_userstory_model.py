from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List, Union
from datetime import datetime

class UserStoryItem(BaseModel):
    id: str
    title: str
    description: str
    priority: Literal["Alta", "Media", "Baja"]
    assigned_epic: str
    acceptance_criteria: List[str]

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
    content: Union[List[UserStoryItem], str] = Field(
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

    def _format_user_stories(self, stories: List[Union[UserStoryItem, Dict]]) -> List[UserStoryItem]:
        formatted = []

        for i, story in enumerate(stories, 1):
            item = UserStoryItem(**story) if isinstance(story, dict) else story

            # Asegurar que acceptance_criteria sea lista
            criteria = item.acceptance_criteria if isinstance(item.acceptance_criteria, list) else []

            # Actualizar campos
            item = item.model_copy(update={
                "id": f"US-{i:03d}",
                "acceptance_criteria": criteria
            })

            formatted.append(item)

        return formatted

    def format_response(self) -> str:
        if isinstance(self.content, list):
            self.content = self._format_user_stories(self.content)
        return self.model_dump_json(indent=4)
