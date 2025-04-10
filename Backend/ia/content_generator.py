"""
Nombre: 
    content_generator.py

Descripción:
    Módulo encargado de la generación de contenido utilizando el modelo LLM,
    el historial de conversación y la recuperación de documentos relevantes.

    Module responsible for content generation using the LLM model,
    conversation history and retrieval of relevant documents.

Autor / Author: 
    Abdiel Fritsche Barajas

Fecha de creación / Created: 2025-03-26  
Última modificación / Last modified: 2025-03-29  
Versión / Version: 1.0.0
"""

# ────────────────────────────────
# Librerías estándar / Standard libraries
from datetime import datetime


# ────────────────────────────────
# Librerías de terceros / Third-party libraries
from langchain_core.output_parsers import JsonOutputParser
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain 
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate, MessagesPlaceholder

# ────────────────────────────────
# Imports locales / Local imports
from models import RequirementResponse
from models import EpicResponse
from models import UserStoryResponse

class ContentGenerator:
    """
    Clase encargada de orquestar la generación de contenido con recuperación contextual y formato estructurado.

    Class responsible for orchestrating content generation using context-aware retrieval and structured formatting.
    """

    __slots__ = ["document_manager",
                 "conversation_manager",
                 "llm",
                 "thinking_manager"
                 ]
    
    def __init__(
            self,
            document_manager,
            conversation_manager,
            llm: ChatGoogleGenerativeAI,
            thinking_manager
        ):
        """
        Inicializa el generador de contenido con sus componentes principales.

        Initializes the content generator with its core components.

        Args:
            document_manager: Manejador de vectores y documentos / Document and vectorstore handler
            conversation_manager: Manejador de sesiones y contexto / Session and context manager
            llm (ChatGoogleGenerativeAI): Modelo generativo / Generative language model
            thinking_manager: Simulador de pasos mentales / Thought step simulator
        """

        self.document_manager = document_manager
        self.conversation_manager = conversation_manager
        self.thinking_manager= thinking_manager
        self.llm = llm
    
    def _manage_session(self, session_id, newchat):
        """
        Crea o recupera una sesión de conversación.

        Creates or retrieves a conversation session.
        """

        if newchat or session_id is None:
            return self.conversation_manager.create_conversation(session_id)
        
        elif session_id not in self.conversation_manager.conversations:
            return self.conversation_manager.create_conversation(session_id)
        
        return session_id

    def _configure_retriever(self, session_id, newchat):
        """
        Configura el retriever según el tipo de conversación.

        Configures the retriever based on whether it's a new chat or not.
        """
        if newchat:
            return self.document_manager.vectorstore.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 5}
            )
        
        else:
            return self.conversation_manager.create_history_aware_retriever(session_id)

    def _prepare_prompt(self, query, preprompt, session_id, newchat, type):
        """
        Prepara el prompt que se le enviará al modelo de lenguaje, incorporando historial si es necesario.

        Prepares the full prompt that will be sent to the LLM, including history if needed.

        Args:
            query: Pregunta del usuario / User query
            preprompt: Contexto inicial / Initial instruction
            session_id: ID de la sesión activa / Active session ID
            newchat: Indicador de si es una conversación nueva / Flag to indicate if it's a new chat
        """
        if type == "requerimientos":
            parser = JsonOutputParser(pydantic_object=RequirementResponse)
        elif type == "epicas":
            parser = JsonOutputParser(pydantic_object=EpicResponse)
        elif type == "historias_usuario":
            parser = JsonOutputParser(pydantic_object=UserStoryResponse)
        else:
            parser = JsonOutputParser(pydantic_object=RequirementResponse)

        format_instructions = parser.get_format_instructions()

        system_message = self._create_system_message(preprompt, format_instructions, type)
        

        history_messages = self.conversation_manager.format_chat_history(session_id) if not newchat else []
        
        if history_messages and not newchat:
            return ChatPromptTemplate.from_messages([
                ("system", system_message),
                *history_messages,
                ("human", f"Pregunta: {query}")
            ])
        
        else:
            return ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", f"Pregunta: {query}")
            ])

    
    def _create_system_message(self, preprompt, format_instructions, type):
        """
        Crea el mensaje del sistema que le indica al modelo cómo estructurar su salida.

        Creates the system message that tells the LLM how to format its output.

        Args:
            preprompt: Introducción base / Base instructions
            format_instructions: Instrucciones generadas por el parser JSON / JSON format instructions
        """

        escaped_format_instructions = format_instructions.replace('{', '{{').replace('}', '}}')

        if type == "requerimientos":
            return (
                f"{preprompt} Use the following information to deepen and enrich your response "
                "or as a base to build your answer: \n\n{context}\n\n"
                "Generate your response in the following structured JSON format. Always make sure to include the '{{status}}' field:\n\n"
                f"{escaped_format_instructions}\n\n"
                "IMPORTANT: The '{{status}}' field is MANDATORY and must be one of the following values:\n"
                "- 'REQUERIMIENTOS_GENERADOS' if you can generate requirements based on the project description. Always use the fields id (REQ-### for functional and REQ-NF-### for non-functional), title, description, category (functional or non-functional depending on the type), and priority (High, Medium, Low)\n"
                "- 'INFORMACION_INSUFICIENTE' if you believe more information is needed, and list it under the 'missing_info' field\n"
                "- 'ERROR_PROCESAMIENTO' if an error occurs\n"
                "- 'RESPUESTA_GENERAL' for any answer outside of those attributes\n\n"
                "- If asked for anything that is not a software project, respond exactly with:\n"
                "- 'As a virtual assistant, I cannot provide a response for that. I can only assist with software project support.'\n"
                "Finally, always respond in the same language you are addressed in."
            )

        elif type == "epicas":
            return (
                f"{preprompt} Use the following information to deepen and enrich your response "
                "or as a base to build your answer: \n\n{context}\n\n"
                "Generate your response in the following structured JSON format. Always make sure to include the '{{status}}' field:\n\n"
                f"{escaped_format_instructions}\n\n"
                "IMPORTANT: The '{{status}}' field is MANDATORY and must be one of the following values:\n"
                "- 'EPICAS_GENERADAS' if you can generate epics based on the available requirements. Always use the fields id (EPIC-###), title, description, and related_requirements, where you list the requirement IDs (REQ-### for functional and REQ-NF-### for non-functional) along with their descriptions in a list\n"
                "- 'INFORMACION_INSUFICIENTE' if you believe more information is needed, and list it under the 'missing_info' field\n"
                "- 'ERROR_PROCESAMIENTO' if an error occurs\n"
                "- 'RESPUESTA_GENERAL' for any answer outside of those attributes\n\n"
                "- If asked for anything that is not a software project, respond exactly with:\n"
                "- 'As a virtual assistant, I cannot provide a response for that. I can only assist with software project support.'\n"
                "Finally, always respond in the same language you are addressed in."
            )

        elif type == "historias_usuario":
            return (
                f"{preprompt} Use the following information to deepen and enrich your response "
                "or as a base to build your answer: \n\n{context}\n\n"
                "Generate your response in the following structured JSON format. Always make sure to include the '{{status}}' field:\n\n"
                f"{escaped_format_instructions}\n\n"
                "IMPORTANT: The '{{status}}' field is MANDATORY and must be one of the following values:\n"
                "- 'HISTORIAS_GENERADAS' if you can generate user stories based on the available epics. Always use the fields id (US-###), title, description, priority (High, Medium, Low), and assigned_epic (EPIC-###) for the associated epic. Also include the acceptance_criteria field as a list of acceptance criteria for the user story\n"
                "- 'INFORMACION_INSUFICIENTE' if you believe more information is needed, and list it under the 'missing_info' field\n"
                "- 'ERROR_PROCESAMIENTO' if an error occurs\n"
                "- 'RESPUESTA_GENERAL' for any answer outside of those attributes\n\n"
                "- If asked for anything that is not a software project, respond exactly with:\n"
                "- 'As a virtual assistant, I cannot provide a response for that. I can only assist with software project support.'\n"
                "Finally, always respond in the same language you are addressed in."
            )

        else:
            return (
                f"{preprompt} Use the following information to deepen and enrich your response "
                "or as a base to build your answer: \n\n{context}\n\n"
                "Generate your response in the following structured JSON format. Always make sure to include the '{{status}}' field:\n\n"
                f"{escaped_format_instructions}\n\n"
                "IMPORTANT: The '{{status}}' field is MANDATORY and must be one of the following values:\n"
                "- 'REQUERIMIENTOS_GENERADOS' if you can generate requirements based on the project description. Always use the fields id (REQ-### for functional and REQ-NF-### for non-functional), title, description, category (functional or non-functional depending on the type), and priority (High, Medium, Low)\n"
                "- 'INSUFFICIENT_INFORMATION' if you believe more information is needed, and list it under the 'missing_info' field\n"
                "- 'ERROR_PROCESAMIENTO' if an error occurs\n"
                "- 'RESPUESTA_GENERAL' for any answer outside of those attributes\n\n"
                "- If asked for anything that is not a software project, respond exactly with:\n"
                "- 'As a virtual assistant, I cannot provide a response for that. I can only assist with software project support.'\n"
                "Finally, always respond in the same language you are addressed in."
            )



        '''
        if type == "requerimientos":
            return (
                f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
                "o como una base para construir lo que se te pide: \n\n{context}\n\n" 
                "Genera tu respuesta en el siguiente formato estructurado JSON. Asegúrate de incluir SIEMPRE el campo '{{status}}':\n\n" 
                f"{escaped_format_instructions}\n\n"
                "IMPORTANTE: El campo '{{status}}' es OBLIGATORIO y debe ser uno de estos valores:\n"
                "- 'REQUERIMIENTOS_GENERADOS si puedes generar requerimientos en base a la descripcion del proyecto si es posible, no olvides que SIEMPRE debes usar los campos id (REQ-###) para funcionales y REQ-NF-### para no funcionales, title,description,category(funcional o no funcional segun el tipo de requerimiento) y priority (Alta, Media, Baja)'\n"
                "- 'INFORMACION_INSUFICIENTE cuando consideres que falta informacion, y listala dentro del campo missing_info'\n"
                "- 'ERROR_PROCESAMIENTO cuando surja un error'\n"
                "- 'RESPUESTA_GENERAL para una respuesta fuera de esos atributos '\n\n"
                "- Si te piden cualquier cosa que no sea un proyecto de software, responde textualmente:\n"
                "- 'Como asistente virtual no puedo proporcionarte la respuesta para eso, solo puedo asistirte con asistencia de proyectos de software'\n"
                "Finalmente, responde siempre en el lenguaje que te hablen."
            )
        
        elif type == "epicas":
            return (
                f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
                "o como una base para construir lo que se te pide: \n\n{context}\n\n" 
                "Genera tu respuesta en el siguiente formato estructurado JSON. Asegúrate de incluir SIEMPRE el campo '{{status}}':\n\n" 
                f"{escaped_format_instructions}\n\n"
                "IMPORTANTE: El campo '{{status}}' es OBLIGATORIO y debe ser uno de estos valores:\n"
                "- 'EPICAS_GENERADAS si puedes generar epicas en base a los requerimientos que tienes si es posible, no olvides que SIEMPRE debes usar los campos id en formato obligatorio (EPIC-###) title,description, y related_requirements donde pondras el id del requerimiento con formato REQ-### para funcionales y REQ-NF-### para no funcionales y su descripcion como lista'\n"
                "- 'INFORMACION_INSUFICIENTE cuando consideres que falta informacion, y listala dentro del campo missing_info'\n"
                "- 'ERROR_PROCESAMIENTO cuando surja un error'\n"
                "- 'RESPUESTA_GENERAL para una respuesta fuera de esos atributos '\n\n"
                "- Si te piden cualquier cosa que no sea un proyecto de software, responde textualmente:\n"
                "- 'Como asistente virtual no puedo proporcionarte la respuesta para eso, solo puedo asistirte con asistencia de proyectos de software'\n"
                "Finalmente, responde siempre en el lenguaje que te hablen."
            )
        
        elif type == "historias_usuario":
            return (
                f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
                "o como una base para construir lo que se te pide: \n\n{context}\n\n" 
                "Genera tu respuesta en el siguiente formato estructurado JSON. Asegúrate de incluir SIEMPRE el campo '{{status}}':\n\n" 
                f"{escaped_format_instructions}\n\n"
                "IMPORTANTE: El campo '{{status}}' es OBLIGATORIO y debe ser uno de estos valores:\n"
                "- 'HISTORIAS_GENERADAS si puedes generar epicas en base a los requerimientos que tienes si es posible, no olvides que SIEMPRE debes usar los campos id en formato obligatorio (US-###) title, description,priority(Alta,Media,Baja), y assigned_epic donde pondras el id del la EPICA con formato EPIC-### para la epica asociada a la Historia de usuario, igualmente agrega el campo acceptance_criteria como una lista de criterios de aceptacion para la historia de usuario'\n"
                "- 'INFORMACION_INSUFICIENTE cuando consideres que falta informacion, y listala dentro del campo missing_info'\n"
                "- 'ERROR_PROCESAMIENTO cuando surja un error'\n"
                "- 'RESPUESTA_GENERAL para una respuesta fuera de esos atributos '\n\n"
                "- Si te piden cualquier cosa que no sea un proyecto de software, responde textualmente:\n"
                "- 'Como asistente virtual no puedo proporcionarte la respuesta para eso, solo puedo asistirte con asistencia de proyectos de software'\n"
                "Finalmente, responde siempre en el lenguaje que te hablen."
            )
        
        else:
            return (
                f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
                "o como una base para construir lo que se te pide: \n\n{context}\n\n" 
                "Genera tu respuesta en el siguiente formato estructurado JSON. Asegúrate de incluir SIEMPRE el campo '{{status}}':\n\n" 
                f"{escaped_format_instructions}\n\n"
                "IMPORTANTE: El campo '{{status}}' es OBLIGATORIO y debe ser uno de estos valores:\n"
                "- 'REQUERIMIENTOS_GENERADOS si puedes generar requerimientos en base a la descripcion del proyecto si es posible, no olvides que SIEMPRE debes usar los campos id (REQ-###) para funcionales y REQ-NF-### para no funcionales, title,description,category(funcional o no funcional segun el tipo de requerimiento) y priority (Alta, Media, Baja)'\n"
                "- 'INFORMACION_INSUFICIENTE cuando consideres que falta informacion, y listala dentro del campo missing_info'\n"
                "- 'ERROR_PROCESAMIENTO cuando surja un error'\n"
                "- 'RESPUESTA_GENERAL para una respuesta fuera de esos atributos '\n\n"
                "- Si te piden cualquier cosa que no sea un proyecto de software, responde textualmente:\n"
                "- 'Como asistente virtual no puedo proporcionarte la respuesta para eso, solo puedo asistirte con asistencia de proyectos de software'\n"
                "Finalmente, responde siempre en el lenguaje que te hablen."
            )
            '''
        

    async def _execute_rag_chain(self, query, retriever, qa_prompt):
        """
        Ejecuta la cadena RAG (Retrieval-Augmented Generation) para generar una respuesta.

        Executes the RAG (Retrieval-Augmented Generation) chain to generate a response.

        Args:
            query: Consulta original / Original query
            retriever: Sistema de recuperación de documentos / Document retriever
            qa_prompt: Prompt final para el modelo / Final prompt to be passed to the LLM
        """


        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        result = rag_chain.invoke({
            "input": query, 
            "\"description\"": "",
            "\"properties\"": "",
            "\"foo\"": ""
        })
    
        await self.thinking_manager.add_step("Analizando la información recuperada", 1.2)
        await self.thinking_manager.add_step("Sintetizando respuesta basada en el conocimiento disponible", 1.5)

        return result
    
    def _update_conversation_history(self, session_id, query, standardized_answer, response,final_response=None):
        """
        Actualiza el historial de conversación con la nueva entrada y guarda contexto recuperado.

        Updates conversation history with the new entry and stores retrieved context.

        Args:
            session_id: ID de la sesión / Session ID
            query: Pregunta del usuario / User query
            standardized_answer: Respuesta formateada / Standardized answer
            response: Respuesta cruda del modelo / Raw response from the model
        """

        response_to_save = final_response if final_response is not None else standardized_answer

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.conversation_manager.conversations[session_id]["history"].append({
            "query": query,
            "response": response_to_save,
            "timestamp": timestamp,
            "raw_response": response.get('answer', 'No se encontró respuesta')
        })
            
        if "context" in response:
            self.conversation_manager.conversations[session_id]["last_context"] = response["context"]
        

        self.conversation_manager.auto_save_history(session_id)
