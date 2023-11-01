#!/usr/bin/sudo python
"""
Usage:
- Run app: poetry run python run.py
"""
import glob
import os
import sys

from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import TokenTextSplitter

from gen3discoveryai import config, logging
from gen3discoveryai.utils import get_topic_chain_factory


def load_tsvs_from_dir(
    directory,
    topic_chain_name="TopicChainQuestionAnswerRAG",
    source_column_name="guid",
    token_splitter_chunk_size=1000,
    delimiter="\t",
):
    """
    Load TSVs from specified directory in the knowledge database.

    This expects filenames to START with a configured topic and will aggregate
    documents from all files that begin with that topic name. This will recursively retrieve
    all filenames in the directory and subdirectories.

    In the following example, both TSVs starting with "default" would populate documents
    for the "default" topic knowledge store and the nested "anothertopic.tsv" would populate
    documents for the "anothertopic" topic.

        - default_data_1.tsv
        - default_data_2.tsv
        - some folder
            - anothertopic.tsv

    Args:
        directory: path to directory where relevant TSVs are
        topic_chain_name: name for an available TopicChain
        source_column_name: what column to get the "source" information from for the document
        token_splitter_chunk_size: how many tokens to chunk the content into per doc
        delimiter: \t or , or whatever else is delimited the TSV/CSV-like file
    """
    logging.info(f"Loading TSVs for directory: {directory}")
    logging.info(f"TSV source_column_name: {source_column_name}")
    logging.info(f"token_splitter_chunk_size: {token_splitter_chunk_size}")
    logging.info(f"delimiter: {delimiter}")

    topic_chain_factory = get_topic_chain_factory()

    files = glob.glob(f"{directory.rstrip('/')}/**/*.*", recursive=True)
    topics = config.TOPICS.split(",")

    logging.info(f"Loading TSVs for topics: {topics}")

    topics_files = {}

    for topic in topics:
        topics_files[topic] = []
        for file in files:
            if os.path.basename(file).startswith(topic):
                topics_files[topic].append(file)

    for topic, files in topics_files.items():
        topic_documents = []
        for file in files:
            logging.info(f"Loading data from file: {file}, for topic: {topic}")

            # Load the document, split it into chunks, embed each chunk and load it into the vector store.
            loader = CSVLoader(
                source_column=source_column_name,
                file_path=file,
                csv_args={
                    "delimiter": delimiter,
                    "quotechar": '"',
                },
            )
            data = loader.load()

            # 4097 is OpenAI's max, so if we split into 1000, we can get 4 results with
            # 97 tokens left for the query?
            text_splitter = TokenTextSplitter.from_tiktoken_encoder(
                chunk_size=token_splitter_chunk_size, chunk_overlap=0
            )
            documents = text_splitter.split_documents(data)

            topic_documents.extend(documents)

        topic_chain = topic_chain_factory.get(
            topic_chain_name,
            topic=topic,
            # metadata shouldn't matter much here, we just need the topic chain initialized so we can store the data
            metadata={"model_name": "gpt-3.5-turbo", "model_temperature": 0.33},
        )

        logging.info(f"Storing {len(topic_documents)} documents for topic: {topic}")
        _store_documents_in_chain(topic_chain, topic_documents)


def _store_documents_in_chain(topic_chain, topic_documents):
    """
    Tiny helper to store documents in the provided chain. This makes the testing/mocking simpler in unit tests
    """
    topic_chain.store_knowledge(topic_documents)


if __name__ == "__main__":
    load_tsvs_from_dir(*sys.argv[1:])
