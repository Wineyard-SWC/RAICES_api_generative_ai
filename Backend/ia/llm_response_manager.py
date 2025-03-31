"""
Nombre:
    llm_response_manager.py

Descripción:
    Este módulo procesa las respuestas crudas del modelo de lenguaje (LLM) y las transforma 
    en una estructura estándar esperada por la aplicación, incluyendo análisis, extracción de JSON, 
    estandarización de formato y manejo de errores.

    This module processes raw responses from the language model (LLM) and transforms them 
    into a standardized structure expected by the application, including JSON extraction, 
    formatting, and error handling.

Autor / Author:
    Abdiel Fritsche Barajas

Fecha de creación / Created: 2025-03-27
Última modificación / Last modified: 2025-03-29
Versión / Version: 1.0.0
"""

# ────────────────────────────────
# Librerías estándar / Standard libraries
import re
from datetime import datetime
import json

# ────────────────────────────────
# Librerías de terceros / Third-party libraries
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# ────────────────────────────────
# Imports locales / Local imports
from models import RequirementResponse

class LLMResponseProcessor:
    """
    Clase encargada de procesar y estandarizar las respuestas del modelo de lenguaje (LLM).

    Class responsible for processing and standardizing language model (LLM) responses.
    """
    __slots__ = ["llm"]

    def __init__(
            self,
            llm: ChatGoogleGenerativeAI 
        ):
        """
        Inicializa el procesador con una instancia del modelo de lenguaje.

        Initializes the processor with an instance of the language model.
        """

        self.llm = llm
    
    def standardize_output(self, raw_response, output_type="requirements", missing_info=None,query=""):
        """
        Convierte una respuesta cruda del modelo en una respuesta estructurada uniforme.

        Converts a raw model response into a uniformly structured output.

        Args:
            raw_response (str): Texto devuelto por el LLM / Raw text response
            output_type (str): Tipo de salida / Type of output ("requirements", "missing_info", "error")
            missing_info (list): Información faltante / Missing information
            query (str): Consulta original / Original user query

        Returns:
            str: Respuesta formateada / Formatted response string
        """
        outputs = {
            "requirements" : "REQUERIMIENTOS_GENERADOS",
            "missing_info" : "INFORMACION_INSUFICIENTE",
            "error" : "ERROR_PROCESAMIENTO"
        }
        
        status = outputs.get(output_type, "RESPUESTA_GENERAL")
        
        response_obj = RequirementResponse(
            status=status,  # Provide status when creating the object
            query=query,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            content=raw_response,
            missing_info=missing_info if missing_info and isinstance(missing_info, list) else None
        )
        
        return response_obj.format_response()
        
    def setup_structured_output(self):
        """
        Configura una cadena LLM para devolver respuestas estructuradas en formato JSON.

        Sets up an LLM chain to return structured responses in JSON format.
        """

        parser = JsonOutputParser(pydantic_object=RequirementResponse)

        format_instructions = parser.get_format_instructions()

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
            "Eres un asistente especializado en análisis de proyectos y generación de requerimientos. "
            "Debes proporcionar respuestas estructuradas según el formato especificado.\n\n"
            "Contexto adicional para tu respuesta:\n\n{context}\n\n"
            f"{format_instructions}"),
            ("human", "{input}")
        ])

        chain = prompt_template | self.llm | parser
    
        return chain
    
    def process_llm_response(self, response,query=""):
        """
        Procesa una respuesta del modelo de lenguaje, intentando extraer JSON válido y estandarizarla.

        Processes a language model response, extracting structured JSON and formatting it.

        Args:
            response (dict): Respuesta cruda del modelo / Raw model response
            query (str): Consulta del usuario / User's original query

        Returns:
            str: Respuesta procesada y formateada / Processed, formatted response
        """
        raw_answer = response.get('answer', 'No se encontró respuesta')
        
        try:
            # Extraer JSON de la respuesta
            json_str = self._extract_json_from_response(raw_answer)
            
            # Procesar los datos JSON
            return self._process_json_response(json_str, raw_answer,query)
            
        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            # Fallback a procesamiento manual
            output_type, processed_response, missing_info = self._detect_response_type(raw_answer)
            return self.standardize_output(processed_response, output_type, missing_info,query)

    def _extract_json_from_response(self, raw_answer):
        """
        Intenta extraer una estructura JSON desde el texto.

        Attempts to extract a JSON structure from the raw answer.
        """
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_answer, re.DOTALL)
        
        if json_match:
            return json_match.group(1)
        
        
        json_match = re.search(r'({.*})', raw_answer, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        raise ValueError("No JSON structure found in response")

    def _process_json_response(self, json_str, raw_answer,query=""):
        """
        Convierte un string JSON en una respuesta estructurada.

        Converts a JSON string into a structured response.
        """
        structured_data = json.loads(json_str)
        
        complete_data = {
            "status": "RESPUESTA_GENERAL",  
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": structured_data.get("content", raw_answer),
            "missing_info": structured_data.get("missing_info", None),
            "metadata": structured_data.get("metadata", None)
        }
        
        # Determinar el status adecuado
        complete_data["status"] = self._determine_response_status(structured_data, complete_data["content"])
        
        return self.standardize_output(
        complete_data["content"], 
        output_type=complete_data["status"].lower().replace("_", "_"), 
        missing_info=complete_data["missing_info"],
        query=query
        )
    
    def _determine_response_status(self, structured_data, content):
        """
        Determina el estado de una respuesta basada en su contenido.

        Determines the response status based on its content.
        """

        if "status" in structured_data:
            return structured_data["status"]
        
        content_lower = content.lower()
        if "información insuficiente" in content_lower or "necesito más información" in content_lower:
            return "INFORMACION_INSUFICIENTE"
        
        elif "error" in content_lower:
            return "ERROR_PROCESAMIENTO"
        
        elif "requerimiento" in content_lower or "requisito" in content_lower:
            return "REQUERIMIENTOS_GENERADOS"
        
        return "RESPUESTA_GENERAL"

    def _handle_missing_info(self, complete_data):
        """
        Procesa respuestas con información faltante que no esté en formato de lista.

        Processes missing info responses when it's not already in list form.
        """

        if complete_data["status"] == "INFORMACION_INSUFICIENTE" and not isinstance(complete_data["missing_info"], list):
            
            if isinstance(complete_data["content"], str):
                content_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)', complete_data["content"])
                
                if content_items:
                    complete_data["missing_info"] = content_items
                
                else:
                    complete_data["missing_info"] = ["Se requieren más detalles sobre el proyecto"]
        
        return complete_data

    def _detect_response_type(self, raw_response):
        """
        Detecta el tipo de respuesta cuando no se puede parsear como JSON.

        Detects the type of response when JSON parsing fails.

        Args:
            raw_response (str): Texto crudo de la IA / Raw LLM output

        Returns:
            tuple: (output_type, processed_response, missing_info)
        """
        lower_response = raw_response.lower()
        missing_info = None
        
        if "información insuficiente" in lower_response or "necesito más información" in lower_response:
            output_type = "missing_info"
            missing_info = self._extract_missing_info(lower_response)

        elif "error" in lower_response and ("procesar" in lower_response or "procesamiento" in lower_response):
            output_type = "error"

        else:
            output_type = "requirements"
        
        return output_type, raw_response, missing_info

    def _extract_missing_info(self, lower_response):
        """Extrae la información faltante de una respuesta"""
        missing_pattern = re.compile(r'(?:necesito|falta)(?:.*?)(?:información|detalles)(.*?)(?:$|(?:para generar))', re.DOTALL)
        match = missing_pattern.search(lower_response)
        
        if match:
            raw_missing = match.group(1).strip()
            list_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)', raw_missing)

            if not list_items:  
                list_items = [item.strip() for item in re.split(r'(?:\.|;|\n)', raw_missing) if item.strip()]
            
            if list_items:
                return list_items
        
        return None