import json
import re
from langchain_core.output_parsers import JsonOutputParser
from typing import Literal, Optional, Dict, List,Union
from datetime import datetime
from pydantic import BaseModel, Field

class RequirementItem(BaseModel):
    id: str
    title: str
    description: str
    category: Literal["Funcional", "No Funcional"]
    priority: Literal["Alta", "Media", "Baja"]


class RequirementResponse(BaseModel):
    """Modelo para respuestas estructuradas del asistente de proyectos."""
    
    status: Literal["REQUERIMIENTOS_GENERADOS", "INFORMACION_INSUFICIENTE", "ERROR_PROCESAMIENTO", "RESPUESTA_GENERAL"] = Field(
        description="Estado de la respuesta generada"
    )
    query: str = Field(default="", description="Consulta original del usuario")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Momento en que se generó la respuesta"
    )
    content: Union[List[RequirementItem], str] = Field(
        description="Contenido principal de la respuesta (requerimientos, explicación o mensaje de error)"
    )
    missing_info: Optional[List[str]] = Field(
        default=None,
        description="Lista de información adicional requerida cuando el status es INFORMACION_INSUFICIENTE"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Metadatos adicionales sobre la respuesta"
    )

    def _format_requirements(self, requirements: List[Union[RequirementItem, Dict]]) -> List[RequirementItem]:
        formatted = []
        for i, req in enumerate(requirements, 1):
            item = RequirementItem(**req) if isinstance(req, dict) else req

            raw_id = item.id
            try:
                num = int(raw_id)
            except (ValueError, TypeError):
                num_match = re.search(r'\d+', str(raw_id))
                num = int(num_match.group()) if num_match else i

            category = item.category.lower()
            item.id = f"REQ-NF-{num:03d}" if "no funcional" in category or "nf" in category else f"REQ-{num:03d}"
            formatted.append(item)

        return formatted


    def format_response(self) -> str:
        if isinstance(self.content, list):
            self.content = self._format_requirements(self.content)
        return self.model_dump_json(indent=4, exclude_none=True)

