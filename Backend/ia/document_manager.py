import os
from typing import List, Dict, Any, Optional
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document


class DocumentManager:
    def __init__(
            self,
            KEY: str,
            pdf_directory: str,
            persist_directory: str,
            embedding: str,
            filter_directories: Optional[List[str]] = None,
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
            
        ) -> None:
        
        self.KEY = KEY

        self.pdf_directory = pdf_directory
        self.persist_directory = persist_directory
        self.filter_directories = filter_directories
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embedding_model = embedding

        self.vectorstore = None 
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        
        self.pdf_paths = self._get_filtered_pdf_paths()

        self.initialize_vectorstore()

    def _get_filtered_pdf_paths(self):
        """
        Obtiene las rutas de los PDFs aplicando filtros si están configurados.
        """
        all_files = []
        
        # Si no hay filtros, incluir todos los PDFs del directorio principal
        if self.filter_directories is None:
            return [os.path.join(self.pdf_directory, f) for f in os.listdir(self.pdf_directory) 
                    if f.endswith('.pdf') and os.path.isfile(os.path.join(self.pdf_directory, f))]
        
        # Procesar solo los subdirectorios especificados
        for subdir in self.filter_directories:
            subdir_path = os.path.join(self.pdf_directory, subdir)
            if os.path.isdir(subdir_path):
                all_files.extend([
                    os.path.join(subdir_path, f) 
                    for f in os.listdir(subdir_path) 
                    if f.endswith('.pdf') and os.path.isfile(os.path.join(subdir_path, f))
                ])
        
        return all_files

    """
    FUNCIONES PARA AGREGAR Y CARGAR CONTENIDO AL RAG (GENERACION AUMENTADA POR RECUPERACION)
    """
    def initialize_vectorstore(self):
        """Inicializa o carga el almacén de vectores desde la persistencia"""
        # Crear embeddings
        embeddings = self._create_embedings()
        
        if self._vectorstore_exist():
            self._load_existing_vectorstore(embeddings)
        else:
            self._create_new_vectorstore(embeddings)
    
    #FUNCIONES PRIVADAS PARA INITIALIZE VECTORSTORE
    def _create_embedings(self):
        # Crear embeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=self.KEY,
            model=self.embedding_model
        )
        return embeddings
    
    def _vectorstore_exist(self):
        """Verifica si existe un almacén de vectores persistente"""
        return os.path.exists(self.persist_directory) and len(os.listdir(self.persist_directory)) > 0

    def _load_existing_vectorstore(self, embeddings):
        """Carga vectores existentes desde el directorio persistente"""
        print(f"Cargando vectores existentes desde {self.persist_directory}")
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=embeddings
        )

    def _create_new_vectorstore(self, embeddings):
        """Crea un nuevo almacén de vectores con los documentos cargados"""
        print("Vectorizando documentos por primera vez...")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        documents = self.load_documents_from_directory(self.pdf_directory)
        
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=self.persist_directory
        )
        print(f"Vectores guardados en {self.persist_directory}")    

    # Modificar la carga de documentos para respetar los filtros
    def load_documents_from_directory(self, directory):
        """
        Carga documentos desde un directorio, aplicando filtros si están configurados.
        Si filter_directories está definido, solo carga documentos de esos subdirectorios.
        """
        if not os.path.exists(directory):
            print(f"El directorio {directory} no existe.")
            return []
        
        documents = []
        
        # Si hay filtros específicos, usar pdf_paths que ya está filtrado
        if self.filter_directories is not None:
            for filepath in self.pdf_paths:
                if os.path.isfile(filepath):
                    filename = os.path.basename(filepath)
                    docs = self._load_file_by_type(filepath, filename)
                    if docs:
                        documents.extend(docs)
        else:
            # Comportamiento original si no hay filtros
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                if os.path.isfile(filepath):
                    docs = self._load_file_by_type(filepath, filename)
                    if docs:
                        documents.extend(docs)
        
        return self._split_documents(documents)

    #FUNCIONES PRIVADAS PARA LOAD DOCUMENTS FROM DIRECTORY

    def _load_file_by_type(self, filepath, filename):
        """Carga un archivo según su tipo y retorna los documentos"""
        if filename.endswith('.pdf'):
            return PyPDFLoader(filepath).load()
        elif filename.endswith('.txt'):
            return TextLoader(filepath).load()
        return []

    def _split_documents(self, documents):
        """División de documentos en chunks si hay documentos para procesar"""
        if not documents:
            return []
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        return text_splitter.split_documents(documents)
    

    def add_document(self, content, metadata=None):
        """Añade un nuevo documento al almacén de vectores"""
        if metadata is None:
            metadata = {"source": "generated_content"}
        
        # Crear documento
        document = Document(page_content=content, metadata=metadata)
        
        # Dividir en chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents([document])
        
        # Añadir al almacén de vectores
        ids = self.vectorstore.add_documents(docs)
                
        return len(docs)
    
    def add_content_to_knowledge_base(self, content, source_name=None):
        """Añade contenido generado a la base de conocimientos"""
        if not source_name:
            source_name = f"generado_{len(os.listdir(self.pdf_directory)) + 1}.txt"
        
        # Guardar en archivo
        output_path = os.path.join(self.pdf_directory, source_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Añadir al vectorstore
        return self.add_document(content, metadata={"source": output_path})