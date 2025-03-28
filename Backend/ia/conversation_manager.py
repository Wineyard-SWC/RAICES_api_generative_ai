import uuid
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_google_genai import ChatGoogleGenerativeAI



class ConversationManager:
    def __init__(
            self,
            llm: ChatGoogleGenerativeAI,
            document_manager,
    
        ):
        
        self.llm = llm
        self.document_manager = document_manager
        self.conversations = {}

        self.load_conversation_histories()
    
    
    """
    FUNCIONES PARA CREACION, MANIPULACION, ACCESO Y EDICION DEL HISTORIAL DE CONVERSACIONES CON LA IA
    """
    def create_conversation(self, session_id=None):
        """Crea o recupera una sesión de conversación con un ID único"""
        if session_id is None:
            session_id = str(uuid.uuid4())
            
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                "history": [],
                "last_context": None
            }
        return session_id
    
    def get_conversation_history(self, session_id):
        """Recupera el historial de conversación para un ID de sesión"""
        if session_id in self.conversations:
            return self.conversations[session_id]["history"]
        return []
    
    def format_chat_history(self, session_id):
        """Convierte el historial de conversación al formato necesario para LangChain"""
        history = self.get_conversation_history(session_id)        
        formatted_history = []
        
        for entry in history:
            # Escapar llaves en query y response
            query = entry["query"].replace("{", "{{").replace("}", "}}")
            response = entry["response"].replace("{", "{{").replace("}", "}}")
            formatted_history.append(("human", query))
            formatted_history.append(("ai", response))
        return formatted_history
        
    def create_history_aware_retriever(self, session_id):
        """Crea un retriever que es consciente del contexto de la conversación"""
        base_retriever = self.document_manager.vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 5}
        )
        
        # Prompt para contextualizar la pregunta basada en el historial
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", "Dada la historia de chat y la última pregunta del usuario que podría hacer referencia al "
                      "contexto previo, formula una pregunta independiente que pueda entenderse sin el historial. "
                      "NO respondas la pregunta, solo reformúlala si es necesario o devuélvela tal como está."),
            *self.format_chat_history(session_id),
            ("human", "{input}")
        ])
        
        # Crear un retriever consciente del historial usando LangChain
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            base_retriever,
            contextualize_q_prompt
        )
        
        return history_aware_retriever
    
    def save_conversation_history(self,session_id):
        """
        Guarda el historial de una conversacion especifica en un archivo txt
        Args:
            session_id(str): ID de la sesion cuyo historial se desea
        Returns:
            bool: True si se guardo correctamente, False en caso contrario
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
        
    
    #FUNCIONES PRIVADAS PARA LOAD CONVERSATION HISTORIES
    def load_conversation_histories(self):
        """
        Carga todos los historiales de conversación desde los archivos de texto.
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
        """Carga el historial de una conversación específica"""
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
        """Parsea una entrada de conversación desde el texto guardado"""
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
        """Añade una entrada única al historial (evita duplicados)"""
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