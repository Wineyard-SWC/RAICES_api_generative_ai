import json
import re
from langchain_core.output_parsers import JsonOutputParser
from typing import Literal, Optional, Dict, List,Union
from datetime import datetime
from pydantic import BaseModel, Field

class RelatedRequirement(BaseModel):
    id: str
    description: str

class EpicItem(BaseModel):
    id: str
    title: str
    description: str
    related_requirements: List[RelatedRequirement]

class EpicResponse(BaseModel):
    """Modelo para respuestas estructuradas del asistente de proyectos."""
    
    status: Literal["EPICAS_GENERADAS", "INFORMACION_INSUFICIENTE", "ERROR_PROCESAMIENTO", "RESPUESTA_GENERAL"] = Field(
        description="Estado de la respuesta generada"
    )
    query: str = Field(default="", description="Consulta original del usuario")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Momento en que se generó la respuesta"
    )
    content: Union[List[EpicItem], str] = Field(
        description="Contenido principal de la respuesta (epicas, explicación o mensaje de error)"
    )
    missing_info: Optional[List[str]] = Field(
        default=None,
        description="Lista de información adicional requerida cuando el status es INFORMACION_INSUFICIENTE"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Metadatos adicionales sobre la respuesta"
    )


    def _format_epics(self, epics: List[Union[EpicItem, Dict]]) -> List[EpicItem]:
        formatted = []

        for i, epic in enumerate(epics, 1):
            item = EpicItem(**epic) if isinstance(epic, dict) else epic

            item = item.model_copy(update={"id": f"EPIC-{i:03d}"})

            related = item.related_requirements or []
            fixed_related = [
                RelatedRequirement(**r) if isinstance(r, dict) else r
                for r in related
            ]

            item = item.model_copy(update={"related_requirements": fixed_related})
            formatted.append(item)

        return formatted


    def format_response(self) -> str:
        """
        Aplica el formateo de IDs si el contenido es una lista y devuelve el JSON formateado.
        """
        if isinstance(self.content, list):
            self.content = self._format_epics(self.content)
        return self.model_dump_json(indent=4)
