import os
from langchain.chains import RetrievalQA
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct

from langchain.prompts import PromptTemplate


class LangChainContainer:
    def __init__(self):
        self.api_key = os.environ["OPENAI_API_KEY"]
        self.embedding_model_name = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.chat_model_name = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4")
        self.top_k = int(os.environ.get("TOP_K", 5))  # Número de documentos a retornar

        # 🔌 Inicializa cliente Qdrant
        self.qdrant_client = QdrantClient(host="vector_db", port=6333)

        # 🔤 Embedding
        self.embedding_model = OpenAIEmbeddings(
            model=self.embedding_model_name,
            openai_api_key=self.api_key
        )

        # 💬 LLM para geração de respostas
        self.chat_model = ChatOpenAI(
            model=self.chat_model_name,
            temperature=0,
            openai_api_key=self.api_key
        )

        # Variáveis internas que mudam com a coleção
        self.vectorstore = None
        self.retriever = None
        self.qa_chain = None

        # Prompt para a cadeia de QA
        # Usado para formatar a pergunta e o contexto
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""Use as informações a seguir para responder com precisão.

        Contexto:
        {context}

        Pergunta:
        {question}
        """
        )

    def set_collection(self, collection_name: str):
        existing = [col.name for col in self.qdrant_client.get_collections().collections]
        if collection_name not in existing:
            # Cria a coleção com tamanho default (ex: 1536 se for OpenAI embeddings)
            embedding_dim = len(self.embedding_model.embed_documents(["teste"])[0])
            self.qdrant_client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE
                )
            )
        """
        Inicializa a cadeia de recuperação e resposta com a coleção escolhida.
        """
        self.vectorstore = Qdrant(
            client=self.qdrant_client,
            collection_name=collection_name,
            embeddings=self.embedding_model
        )

        self.retriever = self.vectorstore.as_retriever()

        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.chat_model,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": self.top_k}),
            memory=None,  # só será atribuído depois
            chain_type="stuff",
            input_key="query",
            output_key="result",  # 👈 ESSENCIAL
            chain_type_kwargs={"prompt": self.prompt},
            return_source_documents=True,
        )

        # self.qa_chain = RetrievalQA.from_chain_type(
        #     llm=self.chat_model,
        #     retriever=self.retriever,
        #     return_source_documents=True
        # )

    def store(self, collection_name, sentences, embeddings, metadata):
        """
        Armazena sentenças com embeddings e metadados no Qdrant.
        """
        if not embeddings:
            raise ValueError("Lista de embeddings vazia.")

        embedding_dim = len(embeddings[0])

        # (Re)criar coleção
        self.qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE
            )
        )

        # Criar pontos com payload
        points = [
            PointStruct(
                id=i,
                vector=embedding,
                payload={**metadata[i], "text": sentence}
            )
            for i, (sentence, embedding) in enumerate(zip(sentences, embeddings))
        ]

        self.qdrant_client.upsert(collection_name=collection_name, points=points)

    def answer(self, question: str) -> str:
        """
        Gera uma resposta com base na collection atual.
        """
        if not self.qa_chain:
            raise RuntimeError("Collection not set. Call `set_collection()` first.")
        return self.qa_chain.run(question)

    def ask_with_sources(self, question: str):
        """
        Gera uma resposta e retorna também os documentos fonte.
        """
        if not self.qa_chain:
            raise RuntimeError("Collection not set. Call `set_collection()` first.")
        result = self.qa_chain.invoke({"query": question})
        return {
            "result": result["result"],
            "sources": [doc.metadata for doc in result["source_documents"]]
        }

    def list_collections(self):
        """
        Lista as coleções disponíveis no Qdrant.
        """
        return [col.name for col in self.qdrant_client.get_collections().collections]

# import os
# from langchain.chains import RetrievalQA
# from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# from langchain_community.vectorstores import Qdrant
# from qdrant_client import QdrantClient
# from qdrant_client.http.models import VectorParams, Distance, PointStruct

# class LangChainContainer:
#     def __init__(self):
#         self.api_key = os.environ["OPENAI_API_KEY"]
#         self.embedding_model_name = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
#         self.qdrant_client = QdrantClient(host="vector_db", port=6333)
        
#         # Embedding model
#         self.embedding_model = OpenAIEmbeddings(
#             model=self.embedding_model_name,
#             openai_api_key=self.api_key
#         )

#         # Chat model
#         self.chat_model = ChatOpenAI(
#             model="gpt-4",
#             temperature=0,
#             openai_api_key=self.api_key
#         )

#         # Componentes que dependem da collection
#         self.vectorstore = None
#         self.retriever = None
#         self.qa_chain = None

#     def set_collection(self, collection_name: str):
#         """Inicializa o retriever e QA chain com a coleção desejada."""
#         self.vectorstore = Qdrant(
#             client=QdrantClient(host="vector_db", port=6333),
#             collection_name=collection_name,
#             embeddings=self.embedding_model
#         )

#         self.retriever = self.vectorstore.as_retriever()

#         self.qa_chain = RetrievalQA.from_chain_type(
#             llm=self.chat_model,
#             retriever=self.retriever,
#             return_source_documents=True
#         )

#     def store(self, collection_name, sentences, embeddings, metadata):
#         # 🧠 Detectar dimensão automaticamente
#         embedding_dim = len(embeddings[0])
        
#         # (Re)cria a coleção
#         self.qdrant_client.recreate_collection(
#             collection_name=collection_name,
#             vectors_config=VectorParams(
#                 size=embedding_dim,
#                 distance=Distance.COSINE
#             )
#         )

#         # Monta os pontos
#         points = [
#             PointStruct(
#                 id=i,
#                 vector=embedding,
#                 payload={**metadata[i], "text": sentence}
#             )
#             for i, (sentence, embedding) in enumerate(zip(sentences, embeddings))
#         ]

#         self.qdrant_client.upsert(collection_name=collection_name, points=points)

#     def answer(self, question: str) -> str:
#         """Executa a cadeia de QA. Certifique-se de definir uma collection antes."""
#         if not self.qa_chain:
#             raise RuntimeError("Collection not set. Call `set_collection()` first.")
#         return self.qa_chain.run(question)
