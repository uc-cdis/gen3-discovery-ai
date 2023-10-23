"""
Super simple wrapper over langchain chain to:
 - force a high-level name and topic for the chain
 - provide an easier interface for storing documents in the appropriately name-spaced vectorstore (likely by topic)
 - preconfigure the llm and prompt
"""
from abc import ABC, abstractmethod

from langchain.chains.base import Chain
from langchain.schema.document import Document


class TopicChain(ABC):
    def __init__(self, name: str, topic: str, chain: Chain) -> None:
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

    @abstractmethod
    def store_knowledge(self, documents: list[Document]) -> None:
        """
        Update knowledge store under the topic provided (or default if not provided)
        with the provided documents.

        Args:
            documents (list[langchain.schema.document.Document]): IDs to Documents to store in the knowledge store
        """
        raise NotImplementedError()

    @abstractmethod
    def run(self, query: str, *args, **kwargs):
        """
        Run the query on the underlying chain

        Args:
            query (str): query to provide to chain
        """
        raise NotImplementedError()
