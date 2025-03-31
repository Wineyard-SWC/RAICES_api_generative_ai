"""
Nombre: 
    assistant.py

Descripción:
    Módulo principal que coordina la interacción entre los distintos componentes del asistente inteligente,
    incluyendo el modelo LLM, gestor de documentos, historial conversacional, generador de contenido, etc.

    Main module that coordinates the interaction between the main components of the intelligent assistant,
    including the LLM model, document manager, conversation history, and content generator.

Autor / Author: 
    Abdiel Fritsche Barajas

Fecha de creación / Created: 2025-03-25  
Última modificación / Last modified: 2025-03-29  
Versión / Version: 1.0.0  

Notas:
    Este script es resultado de la refactorización de una versión anterior old__init__.py
    This script is the result of refactoring a previous version: old__init__.py
"""


# ────────────────────────────────
# Librerías estándar / Standard libraries
import os


# ────────────────────────────────
# Librerías de terceros / Third-party libraries
from langchain_google_genai import ChatGoogleGenerativeAI

# ────────────────────────────────
# Imports locales / Local imports
from .document_manager import DocumentManager
from .conversation_manager import ConversationManager
from .llm_response_manager import LLMResponseProcessor
from .content_generator import ContentGenerator
from .thinking_steps import ThinkingSteps 



# Claves de entorno para configuración del LLM y embeddings
Key = os.getenv("GEMINI_API_KEY")
Embedding = os.getenv("EMBEDDING")


class Assistant:
    """
    Clase principal que encapsula la lógica del asistente inteligente.

    Main class that encapsulates the logic of the intelligent assistant.

    Coordina la interacción entre el modelo de lenguaje, la gestión de documentos,
    el historial conversacional y la generación de contenido.

    Coordinates the interaction between the LLM, document management,
    conversation history, and content generation.

    Atributos / Attributes:
        llm: Modelo de lenguaje generativo (Generative language model)
        llm_response_manager: Procesador de respuestas del LLM (LLM response processor)
        document_manager: Administrador de documentos y embeddings (Document and embedding manager)
        conversation_manager: Maneja el historial de conversación (Conversation history handler)
        thinking_manager: Simulación de pasos de pensamiento (Simulates reasoning steps)
        content_generator: Orquestador de generación de contenido (Content generation orchestrator)
    """


    __slots__ = ["llm",
                 "llm_response_manager",
                 "document_manager",
                 "conversation_manager",
                 "thinking_manager",
                 "content_generator"
                    ]
    def __init__(
            self, 
            subdirectory:str,
            embedding_model:str = Embedding, 
            persist_directory:str = os.path.join(os.path.dirname(__file__), "/chroma_db"),
            filter_directories:str = None,
            thinking_callback:str = None
        ):

        """
        Inicializa los componentes del asistente.

        Initializes the assistant components.

        Args:
            subdirectory (str): Subdirectorio con los PDFs / Subdirectory containing the PDFs
            embedding_model (str): Modelo de embeddings a utilizar / Embedding model to use
            persist_directory (str): Carpeta donde se guardan los vectores / Vector storage directory
            filter_directories (str): Filtros opcionales por subdirectorios / Optional subdirectory filters
            thinking_callback (str): Función para simular pasos mentales / Optional callback for thought simulation
        """

        # Inicializa el modelo LLM (Gemini)
        # Initialize the LLM (Gemini)
        self.llm = ChatGoogleGenerativeAI(
            api_key=Key,
            model="gemini-2.0-flash",
            temperature=0.2,
            max_tokens=None,
            timeout=None,
        )
        
        # Procesador de respuestas del LLM
        # LLM response post-processor
        self.llm_response_manager = LLMResponseProcessor(
            llm= self.llm
        )
        
        # Administra documentos y embeddings
        # Manages documents and embeddings
        self.document_manager = DocumentManager(
            KEY= Key,
            pdf_directory= os.path.join(os.path.dirname(__file__), 'pdfs', subdirectory),
            persist_directory=persist_directory,
            embedding= embedding_model,
            filter_directories=filter_directories
        )

        # Controlador del historial de conversación
        # Conversation history handler
        self.conversation_manager = ConversationManager(
            document_manager= self.document_manager,
            llm = self.llm
        )

        # Simula pensamiento paso a paso para mejor UX
        # Simulates step-by-step reasoning (for better UX)
        self.thinking_manager = ThinkingSteps(
            callback=thinking_callback
        )
        
        # Encargado de generar el contenido final
        # Handles final content generation with prompts, retrieval, etc.
        self.content_generator = ContentGenerator(
            conversation_manager= self.conversation_manager,
            document_manager= self.document_manager,
            llm= self.llm,
            thinking_manager= self.thinking_manager
        )


    async def generate_content(self, query, preprompt, session_id=None, newchat=False): 
        """
        Genera contenido en base a una consulta del usuario, utilizando contexto y documentos relacionados.

        Generates content based on a user query, using context and related documents.

        Args:
            query (str): Consulta del usuario / User's question or request
            preprompt (str): Instrucción base o introducción / Instructional context (pre-prompt)
            session_id (str, optional): ID de sesión / Session ID
            newchat (bool): Reiniciar conversación / Start a new conversation

        Returns:
            str: Respuesta generada en formato estándar / Generated response in standardized format
        """

        # Asegura que exista o se cree una sesión
        # Ensure session exists or create a new one
        session_id = self.content_generator._manage_session(session_id, newchat)
        
        # Configura el sistema de recuperación de contexto (aware retriever)
        # Set up context-aware retriever
        retriever = self.content_generator._configure_retriever(session_id, newchat) 
        
        # Prepara el prompt con la conversación e instrucciones
        # Prepare full prompt with history and instructions
        await self.thinking_manager.add_step("Analizando la consulta...", 1.5)
        qa_prompt = self.content_generator._prepare_prompt(query, preprompt, session_id, newchat)
        
        # Simula razonamiento para mejorar experiencia de usuario
        # Simulate step-by-step reasoning
        await self.thinking_manager.add_step("Buscando información relevante en la base de conocimiento", 2.0)
        await self.thinking_manager.add_step("Procesando documentos recuperados y generando respuesta", 2.5)

        # Ejecuta la cadena RAG (retrieval-augmented generation)
        # Run RAG chain to generate response
        response = await self.content_generator._execute_rag_chain(query, retriever, qa_prompt)
        
        # Procesa y normaliza la salida del modelo
        # Process and standardize model response
        standardized_answer = self.llm_response_manager.process_llm_response(response,query)
        
        # Actualiza el historial de conversación con la nueva interacción
        # Update conversation history with this interaction
        self.content_generator._update_conversation_history(session_id, query, standardized_answer, response)
        
        await self.thinking_manager.complete()

        return standardized_answer
