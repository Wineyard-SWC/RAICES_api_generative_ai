from langchain_core.output_parsers import JsonOutputParser
from typing import Literal, Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class RequirementResponse(BaseModel):
    """Modelo para respuestas estructuradas del asistente de proyectos."""
    
    status: Literal["REQUERIMIENTOS_GENERADOS", "INFORMACION_INSUFICIENTE", "ERROR_PROCESAMIENTO", "RESPUESTA_GENERAL"] = Field(
        description="Estado de la respuesta generada"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Momento en que se generó la respuesta"
    )
    content: str = Field(
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

    def format_response(self) -> str:
        """Formatea la respuesta para presentación al usuario."""
        timestamp_str = f"TIMESTAMP: {self.timestamp}"
        status_str = f"STATUS: {self.status.replace('_', ' ')}"
        
        if self.status == "REQUERIMIENTOS_GENERADOS":
            formatted_output = f"""
{status_str}
{timestamp_str}

{self.content}

---
Nota: Los requerimientos anteriores fueron generados automáticamente 
basados en la descripción del proyecto proporcionada.
"""
        elif self.status == "INFORMACION_INSUFICIENTE":
            missing_details = ""
            if self.missing_info:
                for i, item in enumerate(self.missing_info, 1):
                    missing_details += f"  {i}. {item}\n"
            else:
                missing_details = self.content
                
            formatted_output = f"""
{status_str}
{timestamp_str}

Se requiere más información para generar requerimientos adecuados.
Por favor, proporcione detalles adicionales sobre:

{missing_details}

---
Nota: Una vez proporcionada esta información, se podrán 
generar requerimientos más precisos y útiles.
"""
        elif self.status == "ERROR_PROCESAMIENTO":
            formatted_output = f"""
{status_str}
{timestamp_str}

No fue posible procesar su solicitud debido a:
{self.content}

---
Nota: Por favor, reformule su solicitud o contacte con soporte
si el problema persiste.
"""
        else:  # RESPUESTA_GENERAL
            formatted_output = f"""
{status_str}
{timestamp_str}

{self.content}
"""
        return formatted_output