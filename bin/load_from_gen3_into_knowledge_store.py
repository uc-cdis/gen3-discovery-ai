#!/usr/bin/sudo python
"""
Usage:
- Run app: poetry run python run.py
"""
from gen3.auth import Gen3Auth
from gen3.tools.metadata.discovery import output_expanded_discovery_metadata
from gen3.utils import get_or_create_event_loop_for_thread
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import TokenTextSplitter

from gen3discoveryai.topic_chains.question_answer import TopicChainQuestionAnswerRAG


def main():
    """
    Get all discovery metadata and load into knowledge library based on GUID.

    This relies on using the commons from whatever API Key you have configured. See the Gen3 SDK's `Gen3Auth` class
    for info.
    """
    auth = Gen3Auth()
    loop = get_or_create_event_loop_for_thread()
    output_file = loop.run_until_complete(
        output_expanded_discovery_metadata(auth, output_format="tsv")
    )

    # Load the document, split it into chunks, embed each chunk and load it into the vector store.
    loader = CSVLoader(
        source_column="guid",
        file_path=output_file,
        csv_args={
            "delimiter": "\t",
            "quotechar": '"',
        },
    )
    data = loader.load()

    # 4097 is OpenAI's max, so if we split into 1000, we can get 4 results with
    # 97 tokens left for the query?
    text_splitter = TokenTextSplitter.from_tiktoken_encoder(
        chunk_size=1000, chunk_overlap=0
    )
    documents = text_splitter.split_documents(data)

    topic_chain = TopicChainQuestionAnswerRAG(
        topic="default",
        metadata={"model_name": "gpt-3.5-turbo", "model_temperature": 0.33},
    )

    topic_chain.store_knowledge(documents)


if __name__ == "__main__":
    main()
