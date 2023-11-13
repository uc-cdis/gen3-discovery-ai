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
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.vectorstores.chroma import Chroma

from gen3discoveryai import config, logging
from gen3discoveryai.topic_chains.base import TopicChain
from gen3discoveryai.topic_chains.utils import get_from_cfg_metadata


class TopicChainOpenAiQuestionAnswerRAG(TopicChain):
    """
    This implementation uses `langchain`'s abstraction of `chromadb`.
    `chromadb` implements an in-mem vector database with local file(s) for persistence.
    This class uses OpenAI's embedding capabilities.

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

    NAME = "TopicChainOpenAiQuestionAnswerRAG"

    def __init__(self, topic: str, metadata: Dict[str, Any] = None) -> None:
        logging.debug(f"initializing topic chain {self.NAME} for topic: {topic}")

        metadata = metadata or {}
        # gpt-3.5-turbo-instruct is double the price but instead of 4K context
        # you get 16K (as of 6 OCT 2023, see https://openai.com/pricing)
        llm_model_name = get_from_cfg_metadata(
            "model_name", metadata, default="gpt-3.5-turbo", type_=str
        )

        llm_model_temperature = get_from_cfg_metadata(
            "model_temperature", metadata, default=0.3, type_=float
        )

        system_prompt = metadata.get("system_prompt", "")

        self.llm = ChatOpenAI(
            openai_api_key=str(config.OPENAI_API_KEY),
            model_name=llm_model_name,
            temperature=llm_model_temperature,
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
            "num_similar_docs_to_find", metadata, default=4, type_=int
        )
        similarity_score_threshold = get_from_cfg_metadata(
            "similarity_score_threshold", metadata, default=0.5, type_=float
        )
        # langchain/chroma recommend a separate client per persisted path
        # to avoid potential collisions. We will separate on topic
        vectorstore = Chroma(
            collection_name=topic,
            embedding_function=OpenAIEmbeddings(
                openai_api_key=str(config.OPENAI_API_KEY)
            ),
            # We've heard the `cosine` distance function performs better
            # https://docs.trychroma.com/usage-guide#changing-the-distance-function
            collection_metadata={"hnsw:space": "cosine"},
            persist_directory=f"./knowledge/{topic}",
            client_settings=chromadb.Settings(migrations_hash_algorithm="sha256"),
        )

        logging.debug("chroma vectorstore initialized")

        retriever_cfg = {
            "k": num_similar_docs_to_find,
            "score_threshold": similarity_score_threshold,
        }
        logging.debug(f"retreiver search_kwargs: {retriever_cfg}")

        retreival_qa_chain = RetrievalQA.from_chain_type(
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
            chain=retreival_qa_chain,
            vectorstore=vectorstore,
        )

    def store_knowledge(
        self, documents: list[langchain.schema.document.Document]
    ) -> None:
        """
        Delete and replace knowledge store under the topic provided (or default if not provided)
        with the provided documents.

        https://api.python.langchain.com/en/latest/schema/langchain.schema.document.Document.html#langchain-schema-document-document

        Args:
            documents (list[langchain.schema.document.Document]): documents to store in the knowledge store
        """
        try:
            logging.debug(
                f"Deleting current knowledge store collection for {self.topic}..."
            )
            self.vectorstore.delete_collection()

            self.vectorstore = Chroma(
                collection_name=self.topic,
                embedding_function=OpenAIEmbeddings(
                    openai_api_key=str(config.OPENAI_API_KEY)
                ),
                # We've heard the `cosine` distance function performs better
                # https://docs.trychroma.com/usage-guide#changing-the-distance-function
                collection_metadata={"hnsw:space": "cosine"},
                persist_directory=f"./knowledge/{self.topic}",
                client_settings=chromadb.Settings(migrations_hash_algorithm="sha256"),
            )
        except Exception as exc:
            logging.debug(
                "Exception while deleting collection and recreating client, "
                "assume the collection just didn't exist and continue. Exc: {exc}"
            )
            # doesn't exist so just continue adding
            pass

        self.insert_documents_into_vectorstore(documents)
