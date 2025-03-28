import re
from datetime import datetime
import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


from models import RequirementResponse

class LLMResponseProcessor:
    def __init__(
            self,
            llm: ChatGoogleGenerativeAI 
        ):
        self.llm = llm
    
    def standardize_output(self, raw_response, output_type="requirements", missing_info=None,query=""):
        """
        Estandariza el formato de las respuestas de la IA para mantener consistencia.
        """
        outputs = {
            "requirements" : "REQUERIMIENTOS_GENERADOS",
            "missing_info" : "INFORMACION_INSUFICIENTE",
            "error" : "ERROR_PROCESAMIENTO"
        }
        
        status = outputs.get(output_type, "RESPUESTA_GENERAL")
        
        # Create the object with all required fields at initialization
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
        Cadena configurada para generar salidas estructuradas 
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
        """Procesa la respuesta del LLM y la estandariza"""
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
        """Extrae el contenido JSON de la respuesta"""
        # Buscar JSON en formato de código
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_answer, re.DOTALL)
        
        if json_match:
            return json_match.group(1)
        
        # Buscar JSON en formato regular
        json_match = re.search(r'({.*})', raw_answer, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Si no se encuentra JSON
        raise ValueError("No JSON structure found in response")

    def _process_json_response(self, json_str, raw_answer,query=""):
        """Procesa la respuesta JSON y la convierte en una estructura estandarizada"""
        structured_data = json.loads(json_str)
        
        # Crear los datos completos con campos esperados
        complete_data = {
            "status": "RESPUESTA_GENERAL",  # Valor por defecto
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
        """Determina el estado de la respuesta basado en su contenido"""
        # Si ya tiene un status explícito, usarlo
        if "status" in structured_data:
            return structured_data["status"]
        
        # Determinar status basado en el contenido
        content_lower = content.lower()
        if "información insuficiente" in content_lower or "necesito más información" in content_lower:
            return "INFORMACION_INSUFICIENTE"
        elif "error" in content_lower:
            return "ERROR_PROCESAMIENTO"
        elif "requerimiento" in content_lower or "requisito" in content_lower:
            return "REQUERIMIENTOS_GENERADOS"
        
        return "RESPUESTA_GENERAL"

    def _handle_missing_info(self, complete_data):
        """Maneja el caso especial de información insuficiente"""
        if complete_data["status"] == "INFORMACION_INSUFICIENTE" and not isinstance(complete_data["missing_info"], list):
            if isinstance(complete_data["content"], str):
                # Extraer posibles elementos de lista del contenido
                content_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)', complete_data["content"])
                if content_items:
                    complete_data["missing_info"] = content_items
                else:
                    # Si no se pueden extraer elementos, crear una lista con un elemento genérico
                    complete_data["missing_info"] = ["Se requieren más detalles sobre el proyecto"]
        
        return complete_data

    def _detect_response_type(self, raw_response):
        """
        Detecta automáticamente el tipo de respuesta cuando no se puede parsear como JSON.
        
        Args:
            raw_response (str): Respuesta original del LLM
                
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
            # Extraer elementos usando diversos patrones
            list_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)', raw_missing)
            if not list_items:  # Si no hay formato de lista, intenta extraer oraciones
                list_items = [item.strip() for item in re.split(r'(?:\.|;|\n)', raw_missing) if item.strip()]
            
            if list_items:
                return list_items
        
        return None