"""
The overall RAG process is the following:

1. Retrieve embeddings from knowledge library
2. Create embedding from user query
3. Perform relevancy search of user query embedding vs retrieved embeddings
   from the knowledge library
4. Augment user query with relevant information from the knowledge library
   based on the previous relevancy search
5. Send augmented prompt to the foundational model
"""

from __future__ import annotations

from typing import Any, Dict

import chromadb
import langchain
from langchain_chroma import Chroma
import langchain_classic
from langchain_classic.chains import RetrievalQA
from langchain_classic.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_ollama.embeddings import OllamaEmbeddings

from gen3discoveryai import logging
from gen3discoveryai.topic_chains.base import TopicChain
from gen3discoveryai.topic_chains.utils import get_from_cfg_metadata


class TopicChainOllamaQuestionAnswerRAG(TopicChain):
    """
    This implementation uses `langchain`'s abstraction of `chromadb`.
    `chromadb` implements an in-mem vector database with local file(s) for persistence.

    NOTE: vectorstore is a `langchain.vectorstores.chroma.Chroma`
          and inherits from `langchain.vectorstores.base.VectorStore`

    Class Attributes:
        topic (str): configurable topic name using this chain
        name (str): name for this TopicChain used to map from configuration
        vectorstore (langchain.vectorstores.chroma.Chroma): langchain `vectorstore`,
            gets setup in initialization
        chroma_client (chromadb.PersistentClient): Chromadb client initialized
            outside langchain for better configuration options
        llm (langchain.llms.base.LLM): langchain `LLM`, gets setup in
            initialization
        chain (langchain.chains.base.Chain): langchain `chain`, gets setup in
            initialization after the vectorstore and llm
    """

    NAME = "TopicChainOllamaQuestionAnswerRAG"

    def __init__(self, topic: str, metadata: Dict[str, Any] = None) -> None:
        logging.debug(f"initializing topic chain {self.NAME} for topic: {topic}")

        metadata = metadata or {}

        llm_model_name = get_from_cfg_metadata(
            "model_name", metadata, default="llama3.2", type_=str
        )
        llm_model_temperature = get_from_cfg_metadata(
            "model_temperature", metadata, default=0, type_=float
        )
        llm_max_output_tokens = get_from_cfg_metadata(
            "max_output_tokens", metadata, default=128, type_=int
        )
        llm_top_p = get_from_cfg_metadata("top_p", metadata, default=0.9, type_=float)
        llm_top_k = get_from_cfg_metadata("top_k", metadata, default=40, type_=int)
        ollama_model_base_url = get_from_cfg_metadata(
            "ollama_model_base_url", metadata, default="localhost:11434", type_=str
        )

        system_prompt = metadata.get("system_prompt", "")

        self.llm = ChatOllama(
            model=llm_model_name,
            temperature=llm_model_temperature,
            num_predict=llm_max_output_tokens,
            top_p=llm_top_p,
            top_k=llm_top_k,
        )

        template = (
            system_prompt
            + "\nContext: {context}\n"
            + "Question: {question}\n"
            + "Answer:"
        )

        logging.debug(f"prompt template: {template}")

        prompt = PromptTemplate.from_template(template)

        num_similar_docs_to_find = get_from_cfg_metadata(
            "num_similar_docs_to_find", metadata, default=7, type_=int
        )
        similarity_score_threshold = get_from_cfg_metadata(
            "similarity_score_threshold", metadata, default=0.7, type_=float
        )
        # langchain/chroma recommend a separate client per persisted path
        # to avoid potential collisions. We will separate on topic
        settings = chromadb.Settings(
            migrations_hash_algorithm="sha256",
            anonymized_telemetry=False,
        )

        persistent_client = chromadb.PersistentClient(
            path=f"./knowledge/{topic}",
            settings=settings,
        )
        vectorstore = Chroma(
            client=persistent_client,
            collection_name=topic,
            embedding_function=OllamaEmbeddings(
                model=llm_model_name, base_url=ollama_model_base_url
            ),
            persist_directory=f"./knowledge/{topic}",
            client_settings=settings,
        )

        logging.debug(
            f"chroma vectorstore initialized from ./knowledge/{topic} with docs"
        )

        retriever_cfg = {
            "k": num_similar_docs_to_find,
            "score_threshold": similarity_score_threshold,
        }
        logging.debug(f"retreiver search_kwargs: {retriever_cfg}")

        retrieval_qa_chain = RetrievalQA.from_chain_type(
            self.llm,
            retriever=vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs=retriever_cfg,
            ),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True,
        )

        super().__init__(
            name=self.NAME,
            topic=topic,
            chain=retrieval_qa_chain,
            vectorstore=vectorstore,
        )

    def store_knowledge(
        self, documents: list[langchain_classic.schema.document.Document]
    ) -> None:
        """
        Delete and replace knowledge store under the topic provided (or default if not provided)
        with the provided documents.

        https://api.python.langchain.com/en/latest/schema/langchain_classic.schema.document.Document.html#langchain-schema-document-document

        Args:
            documents (list[langchain_classic.schema.document.Document]): documents to store in the knowledge store
        """
        # try:
        # get all docs but don't include anything other than ids
        docs = self.vectorstore.get(include=[])
        if docs["ids"]:
            logging.debug(
                f"Deleting current knowledge store collection for {self.topic}..."
            )
            self.vectorstore.delete(ids=docs["ids"])

        self.insert_documents_into_vectorstore(documents)
