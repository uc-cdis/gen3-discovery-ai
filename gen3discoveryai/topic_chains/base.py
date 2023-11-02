"""
Super simple wrapper over langchain chain to:
 - force a high-level name and topic for the chain
 - provide an easier interface for storing documents in the appropriately name-spaced vectorstore (likely by topic)
 - preconfigure the llm and prompt
"""
from langchain.chains.base import Chain
from langchain.vectorstores.base import VectorStore
from langchain.schema.document import Document

from gen3discoveryai import logging


class TopicChain:
    def __init__(
        self,
        name: str,
        topic: str,
        chain: Chain,
        vectorstore: VectorStore = None,
    ) -> None:
        """
        Initialize the topic chain with provided name, topic, and langchain

        Args:
            name (str): Description
            topic (str): Description
            chain (langchain.chains.base.Chain): Description
        """
        self.name = name
        self.topic = topic
        # do setup to create a langchain.chains.base.Chain
        self.chain = chain
        # optional vectorstore, may be used if chain requires it
        self.vectorstore = vectorstore

    def store_knowledge(self, documents: list[Document]) -> None:
        """
        Update knowledge store under the topic provided (or default if not provided)
        with the provided documents.

        Args:
            documents (list[langchain.schema.document.Document]): IDs to Documents to store in the knowledge store
        """
        raise NotImplementedError()

    def insert_documents_into_vectorstore(
        self, documents: list[Document], persist: bool = True
    ) -> None:
        """
        Update vectorstore under the topic provided with the provided documents. This is lower-level than store_knowledge
        and requires that the `self.vectorstore` be configured.

        Args:
            persist: whether or not to persist to disk if the vectorstore supports it
            documents (list[langchain.schema.document.Document]): IDs to Documents to store in the knowledge store
        """
        if not self.vectorstore:
            logging.warning(
                f"Attempted to insert documents into a TopicChain {self.name} "
                f"for topic {self.topic} that doesn't have a configured vectorstore"
            )
            return

        logging.info(
            f"Recreating knowledge store collection for {self.topic} from documents..."
        )
        self.vectorstore.add_documents(documents)

        logging.debug(f"Added {len(documents)} documents")

        if persist and "persist" in dir(self.vectorstore):
            logging.info(
                f"Persisting knowledge store collection for {self.topic} to disk..."
            )
            self.vectorstore.persist()

    def run(self, query: str, *args, **kwargs):
        """
        Run the query on the underlying chain

        Args:
            query (str): query to provide to chain
        """
        return self.chain(
            {"query": query},
            *args,
            include_run_info=True,
            **kwargs,
        )
