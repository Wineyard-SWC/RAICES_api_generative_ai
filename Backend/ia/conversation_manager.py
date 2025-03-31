"""
Nombre: 
    conversation_manager.py

Descripción:
    Este módulo gestiona las sesiones de conversación, historial de interacciones y su almacenamiento persistente.

    This module handles conversation sessions, interaction history, and persistent storage.

Autor / Author: 
    Abdiel Fritsche Barajas

Fecha de creación / Created: 2025-03-28  
Última modificación / Last modified: 2025-03-29  
Versión / Version: 1.0.0
"""

# ────────────────────────────────
# Librerías estándar / Standard libraries
import uuid
import os

# ────────────────────────────────
# Librerías de terceros / Third-party libraries
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_google_genai import ChatGoogleGenerativeAI



class ConversationManager:
    """
    Clase que administra múltiples sesiones de conversación con historial y contexto.

    Class that manages multiple conversation sessions with history and context.
    """

    __slots__ = ["llm",
                  "document_manager",
                  "conversations"
                  ]

    def __init__(
            self,
            llm: ChatGoogleGenerativeAI,
            document_manager,
    
        ):
        """
        Inicializa el administrador de conversaciones.

        Initializes the conversation manager.

        Args:
            llm (ChatGoogleGenerativeAI): Modelo de lenguaje / Language model
            document_manager: Manejador de documentos / Document manager
        """

        self.llm = llm
        self.document_manager = document_manager
        self.conversations = {}

        # Carga historiales guardados al iniciar
        # Load saved conversation history on startup
        self.load_conversation_histories()
    
    
    
    def create_conversation(self, session_id=None):
        """
        Crea o recupera una sesión de conversación con un ID único.

        Creates or retrieves a conversation session using a unique ID.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
            
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                "history": [],
                "last_context": None
            }

        return session_id
    
    def get_conversation_history(self, session_id):
        """
        Recupera el historial de conversación de una sesión dada.

        Retrieves the conversation history of a given session.
        """
        if session_id in self.conversations:
            return self.conversations[session_id]["history"]
        
        return []
    
    def format_chat_history(self, session_id):
        """
        Formatea el historial para LangChain, escapando caracteres especiales.

        Formats the conversation history for LangChain, escaping special characters.
        """
        history = self.get_conversation_history(session_id)        
        formatted_history = []
        
        for entry in history:
            # Parsear llaves que puedan romper el template
            # Parse curly braces to avoid prompt formatting issues
            query = entry["query"].replace("{", "{{").replace("}", "}}")
            response = entry["response"].replace("{", "{{").replace("}", "}}")
            
            formatted_history.append(("human", query))
            formatted_history.append(("ai", response))
        
        return formatted_history
        
    def create_history_aware_retriever(self, session_id):
        """
        Crea un retriever consciente del historial conversacional.

        Creates a history-aware retriever using LangChain tools.
        """
        base_retriever = self.document_manager.vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 5}
        )
        
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", "Dada la historia de chat y la última pregunta del usuario que podría hacer referencia al "
                      "contexto previo, formula una pregunta independiente que pueda entenderse sin el historial. "
                      "NO respondas la pregunta, solo reformúlala si es necesario o devuélvela tal como está."),
            *self.format_chat_history(session_id),
            ("human", "{input}")
        ])
                
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            base_retriever,
            contextualize_q_prompt
        )
        
        return history_aware_retriever
    
    def save_conversation_history(self,session_id):
        """
        Guarda el historial de conversación en un archivo de texto.

        Saves the conversation history to a .txt file.

        Args:
            session_id (str): ID de la sesión a guardar / Session ID to save

        Returns:
            bool: True si se guardó correctamente / True if saved successfully
        """

        # Crear directorio para historiales si no existe
        if session_id not in self.conversations:
            print(f"No existe historial para la sesion {session_id}")
            return False
        
        history_dir = os.path.join(os.path.dirname(__file__),'conversation_histories')
        os.makedirs(history_dir, exist_ok=True)

        history_file = os.path.join(history_dir,f"{session_id}.txt")

        try:
            with open(history_file,'a',encoding='utf-8') as f:
                current_history = self.conversations[session_id]["history"]

                saved_count = 0
                
                if os.path.exists(history_file):
                    with open(history_file,'r',encoding='utf-8') as read_file:
                        saved_count = read_file.read().count("--- Fin de respuesta ---")
                
                for i in range(saved_count, len(current_history)):
                    entry = current_history[i]
                    timestamp = entry.get("timestamp","N/A")
                    query = entry["query"]
                    response = entry["response"]

                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Pregunta: {query}\n\n")
                    f.write(f"Respuesta: {response}\n")
                    f.write(f"--- Fin de respuesta ---\n\n")
            return True
        
        except Exception as e:
            print(f"Error al guardar historal: {str(e)}")
            return False
        
    
    def load_conversation_histories(self):
        """
        Carga los historiales de conversación guardados desde disco.

        Loads saved conversation histories from disk.
        """
        history_dir = os.path.join(os.path.dirname(__file__), 'conversation_histories')

        if not os.path.exists(history_dir):
            print("No existe directorio de historiales")
            return
        
        for filename in os.listdir(history_dir):
            if not filename.endswith('.txt'):
                continue
                
            session_id = filename.replace('.txt', '')
            self._load_single_conversation_history(session_id, os.path.join(history_dir, filename))

    def _load_single_conversation_history(self, session_id, history_file):
        """
        Carga el historial de una sesión específica.

        Loads the history of a specific session.
        """
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if session_id not in self.conversations:
                self.conversations[session_id] = {
                    "history": [],
                    "last_context": None
                }
            
            entries = content.split("--- Fin de respuesta ---\n\n")
            
            for entry in entries:
                conversation_entry = self._parse_conversation_entry(entry)
                if conversation_entry:
                    self._add_unique_entry_to_history(session_id, conversation_entry)
            
            print(f"Cargando historial para sesión {session_id} con {len(self.conversations[session_id]['history'])} entradas")
        
        except Exception as e: 
            print(f"Error al cargar historial {os.path.basename(history_file)}: {str(e)}")

    def _parse_conversation_entry(self, entry):
        """
        Parsea una entrada de historial desde texto plano.

        Parses a conversation entry from plain text.
        """
        if not entry.strip():
            return None
        
        parts = entry.split("Pregunta: ", 1)
        if len(parts) < 2:
            return None
        
        timestamp_and_query = parts[1]
        timestamp_parts = timestamp_and_query.split("\n\n", 1)
        query = timestamp_parts[0]
        
        if len(timestamp_parts) < 2:
            return None
        
        response_parts = timestamp_parts[1].split("Respuesta: ", 1)
        if len(response_parts) < 2:
            return None
        
        response = response_parts[1].strip()
        
        return {
            "query": query,
            "response": response,
            "timestamp": "Imported"
        }

    def _add_unique_entry_to_history(self, session_id, entry):
        """
        Añade una entrada única al historial, evitando duplicados.

        Adds a unique entry to history, avoiding duplicates.
        """
        existing_entries = [e["query"] for e in self.conversations[session_id]["history"]]
        
        if entry["query"] not in existing_entries:
            self.conversations[session_id]["history"].append(entry)

    def auto_save_history(self, session_id):
        """
        Guarda automaticamente el historial despues de cada actualizacion. 
        Este metodo debe ser llamado despues de actualizar el historial de conversacion

        Args: 
            seesion_id (str): ID de la sesion cuyo historial se guardara
        """

        return self.save_conversation_history(session_id)

    def delete_conversation_history(self, session_id):
        """
        Elimina el historial de una conversacion especifica tanto de la memoria como del archivo

        Args: 
            session_id (str): ID de la sesion cuyo historial se desea eliminar

        Returns:
            bool: True si se elimino correctamente, False en lo contrario.
        """

        history_dir = os.path.join(os.path.dirname(__file__), 'conversation_histories')
        history_file = os.path.join(history_dir, f"{session_id}.txt")

        if session_id in self.conversations:
            del self.conversations[session_id]

        if os.path.exists(history_file):
            try:
                os.remove(history_file)
                return True
            except Exception as e:
                print(f"Error al eliminar archivo de historial: {str(e)}")
                return False
        return True