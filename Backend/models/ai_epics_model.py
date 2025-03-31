import json
import re
from langchain_core.output_parsers import JsonOutputParser
from typing import Literal, Optional, Dict, List,Union
from datetime import datetime
from pydantic import BaseModel, Field

class EpicResponse(BaseModel):
    """Modelo para respuestas estructuradas del asistente de proyectos."""
    
    status: Literal["EPICAS_GENERADOS", "INFORMACION_INSUFICIENTE", "ERROR_PROCESAMIENTO", "RESPUESTA_GENERAL"] = Field(
        description="Estado de la respuesta generada"
    )
    query: str = Field(default="", description="Consulta original del usuario")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Momento en que se generó la respuesta"
    )
    content: Union[List[Dict], str] = Field(
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

    def _format_epics(self, epics: List[Dict]) -> List[Dict]:
        """
        Reformatea el ID de cada épica al formato EPIC-### si es necesario.

        Reformat each epic ID to 'EPIC-###'.
        """
        formatted = []
        for epic in epics:
            new_epic = epic.copy()
            raw_id = new_epic.get("id", None)

            try:
                num = int(raw_id)
            except (ValueError, TypeError):
                num_match = re.search(r'\d+', str(raw_id))
                num = int(num_match.group()) if num_match else 0

            new_epic["id"] = f"EPIC-{num:03d}"

            if not isinstance(new_epic.get("related_requirements"), list):
                new_epic["related_requirements"] = []

            formatted.append(new_epic)
        return formatted

    def format_response(self) -> str:
        """
        Aplica el formateo de IDs si el contenido es una lista y devuelve el JSON formateado.
        """
        if isinstance(self.content, list):
            self.content = self._format_epics(self.content)
        return self.model_dump_json(indent=4)
