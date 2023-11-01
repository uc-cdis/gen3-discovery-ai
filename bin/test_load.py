import os
from unittest.mock import patch, MagicMock

from gen3discoveryai import config

from load_into_knowledge_store import load_tsvs_from_dir


@patch("load_into_knowledge_store._store_documents_in_chain")
@patch("load_into_knowledge_store.TopicChainQuestionAnswerRAG")
def test_load_from_tsvs(topic_chain, store_documents_in_chain):
    """
    Test that the loading from TSVs pulls the correct information from various files and
    aggregates files that begin with the same topic name.
    """
    config.TOPICS = "default,bdc"

    directory = os.path.abspath(
        os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/../tests/tsvs"
    )

    load_tsvs_from_dir(
        directory=directory,
        source_column_name="guid",
        token_splitter_chunk_size=1000,
        delimiter="\t",
    )

    config.TOPICS = "default"

    topic_chain.store_knowledge.return_value = True

    assert topic_chain.call_count == 2
    assert store_documents_in_chain.call_count == 2

    for item in store_documents_in_chain.call_args_list:
        assert len(item.args[1]) > 0  # documents
