#!/usr/bin/env python
import glob
import os

import click
from langchain.text_splitter import TokenTextSplitter
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders.csv_loader import CSVLoader

from gen3discoveryai import logging
from gen3discoveryai.main import get_topics_from_config


@click.group()
def cli():
    """
    Main entry point for the CLI.
    """
    pass


@cli.command()
@click.argument("directory", type=str)
@click.option(
    "--source_column_name",
    type=str,
    default="guid",
    help="Column to get the 'source' information from.",
)
@click.option(
    "--token_splitter_chunk_size",
    type=int,
    default=1000,
    help="Number of tokens to chunk the content into per doc.",
)
@click.option(
    "--delimiter", type=str, default="\t", help="Delimiter for the TSV/CSV-like file."
)
def tsvs(directory, source_column_name, token_splitter_chunk_size, delimiter):
    """
    Load TSVs from a specified directory into the knowledge database.
    """
    load_tsvs_from_dir(
        directory, source_column_name, token_splitter_chunk_size, delimiter
    )


@cli.command()
@click.argument("directory", type=str)
@click.option(
    "--topic",
    type=str,
    required=True,
    help="Topic that all the Markdown files are about.",
)
@click.option(
    "--token_splitter_chunk_size",
    type=int,
    default=1000,
    help="Number of tokens to chunk the content into per doc.",
)
def markdown(directory, topic, token_splitter_chunk_size):
    """
    Load Markdown files from a specified directory into the knowledge database for the specified topic.
    """
    load_markdown_from_dir(directory, topic, token_splitter_chunk_size)


def load_tsvs_from_dir(
    directory,
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
        directory (str): path to directory where relevant TSVs are
        source_column_name (str): what column to get the "source" information from for the document
        token_splitter_chunk_size (int): how many tokens to chunk the content into per doc
        delimiter (str): \t or , or whatever else is delimited the TSV/CSV-like file
    """
    logging.info(f"Loading TSVs for directory: {directory}")
    logging.info(f"TSV source_column_name: {source_column_name}")
    logging.info(f"token_splitter_chunk_size: {token_splitter_chunk_size}")
    logging.info(f"delimiter: {delimiter}")

    files = glob.glob(f"{directory.rstrip('/')}/**/*.*", recursive=True)
    config_topics = get_topics_from_config()
    topics = config_topics.keys()

    logging.info(f"Loading {len(files)} TSVs for topics: {topics}")

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
            try:
                text_splitter = TokenTextSplitter.from_tiktoken_encoder(
                    chunk_size=token_splitter_chunk_size, chunk_overlap=0
                )
            except Exception as exc:
                logging.error(
                    "Unable to get a token splitter, "
                    "this could be b/c we couldn't find or download the necessary "
                    f"encoding file. Original exc: {exc}"
                )
                raise
            documents = text_splitter.split_documents(data)

            topic_documents.extend(documents)

        logging.info(f"Storing {len(topic_documents)} documents for topic: {topic}")

        if topic_documents:
            _store_documents_in_chain(
                config_topics[topic]["topic_chain"], topic_documents
            )


def load_markdown_from_dir(
    directory,
    topic,
    token_splitter_chunk_size=1000,
):
    """
    Load Markdown files from specified directory in the knowledge database for the specified topic.

    This expects filenames to START with a configured topic and will aggregate
    documents from all files that begin with that topic name. This will recursively retrieve
    all filenames in the directory and subdirectories.
    """
    logging.info(f"Loading Markdown for directory: {directory}")
    logging.info(f"token_splitter_chunk_size: {token_splitter_chunk_size}")

    files = glob.glob(f"{directory.rstrip('/')}/**/*.*", recursive=True)
    config_topics = get_topics_from_config()
    topics = config_topics.keys()

    if topic not in topics:
        raise KeyError(f"{topic} not in configured topics: {topics}")

    logging.info(f"Loading {len(files)} Markdown files for topic: {topic}")

    topics_files = {topic: []}

    for file in files:
        if os.path.isfile(file):
            topics_files[topic].append(file)

    for topic, files in topics_files.items():
        topic_documents = []
        for file in files:
            logging.info(f"Loading data from file: {file}, for topic: {topic}")

            # Load the document, split it into chunks, embed each chunk and load it into the vector store.
            loader = UnstructuredMarkdownLoader(file)
            data = loader.load()

            try:
                text_splitter = TokenTextSplitter.from_tiktoken_encoder(
                    chunk_size=token_splitter_chunk_size, chunk_overlap=0
                )
            except Exception as exc:
                logging.error(
                    "Unable to get a token splitter, "
                    "this could be b/c we couldn't find or download the necessary "
                    f"encoding file. Original exc: {exc}"
                )
                raise
            documents = text_splitter.split_documents(data)

            topic_documents.extend(documents)

        logging.info(f"Storing {len(topic_documents)} documents for topic: {topic}")

        if topic_documents:
            _store_documents_in_chain(
                config_topics[topic]["topic_chain"], topic_documents
            )


def _store_documents_in_chain(topic_chain, topic_documents):
    """
    Tiny helper to store documents in the provided chain. This makes the testing/mocking simpler in unit tests
    """
    topic_chain.store_knowledge(topic_documents)


if __name__ == "__main__":
    cli()
