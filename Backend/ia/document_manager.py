"""
Nombre:
    document_manager.py

Descripción:
    Módulo encargado de gestionar la carga, división, almacenamiento y recuperación de documentos
    para un sistema de generación aumentada por recuperación (RAG).

    Module responsible for loading, splitting, storing, and retrieving documents
    for a Retrieval-Augmented Generation (RAG) system.

Autor / Author:
    Abdiel Fritsche Barajas

Fecha de creación / Created: 2025-03-26
Última modificación / Last modified: 2025-03-29
Versión / Version: 1.0.0
"""

# ────────────────────────────────
# Librerías estándar / Standard libraries
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# ────────────────────────────────
# Librerías de terceros / Third-party libraries
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document


class DocumentManager:
    """
    Clase que administra los documentos usados en el pipeline de RAG.

    Class that manages documents used in the RAG pipeline.
    """
    __slots__ = ["KEY",
                 "pdf_directory",
                 "persist_directory",
                 "filter_directories",
                 "chunk_size",
                 "chunk_overlap",
                 "embedding_model",
                 "vectorstore",
                 "text_splitter",
                 "pdf_paths"]

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
        """
        Inicializa el gestor de documentos con configuración para embeddings y directorios.

        Initializes the document manager with embedding and directory settings.
        """

        self.KEY = KEY

        self.pdf_directory = pdf_directory
        self.persist_directory = persist_directory
        self.filter_directories = filter_directories
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embedding_model = embedding
        
        # Vectorstore y splitter iniciales
        self.vectorstore = None 
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        
        # Determinar qué archivos cargar
        self.pdf_paths = self._get_filtered_pdf_paths()

        # Inicializar vectorstore
        self.initialize_vectorstore()

    def _get_filtered_pdf_paths(self):
        """
        Obtiene las rutas de los PDFs aplicando filtros si están configurados.

        Gets the PDF file paths, applying filters if configured.
        """
        all_files = []
        
        
        if self.filter_directories is None:
            return [os.path.join(self.pdf_directory, f) for f in os.listdir(self.pdf_directory) 
                    if f.endswith('.pdf') and os.path.isfile(os.path.join(self.pdf_directory, f))]
        
        for subdir in self.filter_directories:
            subdir_path = os.path.join(self.pdf_directory, subdir)
            
            if os.path.isdir(subdir_path):
                all_files.extend([
                    os.path.join(subdir_path, f) 
                    for f in os.listdir(subdir_path) 
                    if f.endswith('.pdf') and os.path.isfile(os.path.join(subdir_path, f))
                ])
        
        return all_files

    
    # ────────────────────────────────
    # FUNCIONES PARA AGREGAR Y CARGAR CONTENIDO AL VECTORSTORE (RAG)
    # FUNCTIONS FOR LOADING AND ADDING CONTENT TO THE VECTORSTORE (RAG)

    def initialize_vectorstore(self) -> None:
        """
        Inicializa o carga el almacén de vectores desde la persistencia.

        Initializes or loads the vector store from persistence.
        """
        embeddings = self._create_embedings()
        
        if self._vectorstore_exist():
            self._load_existing_vectorstore(embeddings)
            return
        
        self._create_new_vectorstore(embeddings)
    
    def _create_embedings(self):
        """
        Crea el modelo de embeddings de Google Generative AI.

        Creates the embedding model from Google Generative AI.
        """
        embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=self.KEY,
            model=self.embedding_model
        )
        return embeddings
    
    def _vectorstore_exist(self):
        """
        Verifica si existe un almacén de vectores persistente.

        Checks whether a persistent vector store already exists.
        """
        return os.path.exists(self.persist_directory) and len(os.listdir(self.persist_directory)) > 0

    def _load_existing_vectorstore(self, embeddings):
        """
        Carga vectores existentes desde el directorio persistente.

        Loads existing vectors from the persistence directory.
        """
        print(f"Cargando vectores existentes desde {self.persist_directory}")
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=embeddings
        )

    def _create_new_vectorstore(self, embeddings):
        """
        Crea un nuevo vectorstore desde cero a partir de los documentos cargados.

        Creates a new vectorstore from scratch using loaded documents.
        """
        print("Vectorizando documentos por primera vez...")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        documents = self.load_documents_from_directory(self.pdf_directory)
        
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=self.persist_directory
        )
        print(f"Vectores guardados en {self.persist_directory}")    

    def load_documents_from_directory(self, directory):
        """
        Carga documentos desde un directorio aplicando filtros si están definidos.

        Loads documents from a directory, applying filters if defined.

        Args:
            directory (str): Ruta base / Base directory path
        """
        if not os.path.exists(directory):
            print(f"El directorio {directory} no existe.")
            return []
        
        documents = []
        
        if self.filter_directories is not None:
            
            for filepath in self.pdf_paths:
                
                if os.path.isfile(filepath):
                    filename = os.path.basename(filepath)
                    docs = self._load_file_by_type(filepath, filename)
                    
                    if docs:
                        documents.extend(docs)

        else:
            for filename in os.listdir(directory):
                
                filepath = os.path.join(directory, filename)
                
                if os.path.isfile(filepath):
                    docs = self._load_file_by_type(filepath, filename)
                    
                    if docs:
                        documents.extend(docs)
        
        return self._split_documents(documents)


    def _load_file_by_type(self, filepath, filename):
        """
        Carga un archivo por tipo (PDF o TXT) y retorna documentos LangChain.

        Loads a file by type (PDF or TXT) and returns LangChain documents.
        """
        if filename.endswith('.pdf'):
            return PyPDFLoader(filepath).load()
        elif filename.endswith('.txt'):
            return TextLoader(filepath).load()
        return []

    def _split_documents(self, documents):
        """
        Divide documentos en chunks de texto para embeddings.

        Splits documents into text chunks for embedding.
        """
        if not documents:
            return []
            
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        return text_splitter.split_documents(documents)
    

    def add_document(self, content, metadata=None):
        """
        Añade un nuevo documento (contenido generado, por ejemplo) al vectorstore.

        Adds a new document (e.g., generated content) to the vectorstore.

        Args:
            content (str): Contenido textual a añadir / Text content to add
            metadata (dict): Metadatos opcionales / Optional metadata
        """
        if metadata is None:
            metadata = {"source": "generated_content"}
        
        document = Document(page_content=content, metadata=metadata)
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents([document])
        
        ids = self.vectorstore.add_documents(docs)
                
        return len(docs)
    
    def add_content_to_knowledge_base(self, content, source_name=None):
        """
        Añade contenido generado al sistema de conocimiento y lo persiste en archivo.

        Adds generated content to the knowledge base and persists it to file.
        """
        if not source_name:
            source_name = f"generado_{len(os.listdir(self.pdf_directory)) + 1}.txt"
        
        output_path = os.path.join(self.pdf_directory, source_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return self.add_document(content, metadata={"source": output_path})