import json
import re
from langchain_core.output_parsers import JsonOutputParser
from typing import Literal, Optional, Dict, List,Union
from datetime import datetime
from pydantic import BaseModel, Field

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
    content: Union[List[Dict], str] = Field(
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

    def _format_requirements(self, requirements: List[Dict]) -> List[Dict]:
        """
        Reformatea el id de cada requerimiento.
        Se espera que cada diccionario tenga al menos una clave "id". Además, si el requerimiento
        es no funcional se asume que el diccionario posee una clave "category" que contenga la palabra "no funcional" (o similar).
        """
        formatted = []
        for req in requirements:
            new_req = req.copy()
            # Intentar extraer un número del id original
            raw_id = new_req.get("id", None)
            try:
                # Si raw_id es numérico, se formatea directamente
                num = int(raw_id)
            except (ValueError, TypeError):
                # Si no es numérico, buscar dígitos en el string
                import re
                num_match = re.search(r'\d+', str(raw_id))
                num = int(num_match.group()) if num_match else 0

            # Determinar si es no funcional basándonos en la clave "category"
            category = new_req.get("category", "").lower()
            if "no funcional" in category or "nf" in category:
                new_req["id"] = f"REQ-NF-{num:03d}"
            else:
                new_req["id"] = f"REQ-{num:03d}"
            formatted.append(new_req)
        return formatted

    def format_response(self) -> str:
        # Si content es una lista, aplicar el formateo a cada requerimiento
        if isinstance(self.content, list):
            self.content = self._format_requirements(self.content)
        # Luego, devuelve el JSON formateado
        return self.model_dump_json(indent=4)
