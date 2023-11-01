import os
from unittest.mock import patch, MagicMock

from gen3discoveryai import config

from load_into_knowledge_store import load_tsvs_from_dir


@patch("load_into_knowledge_store._store_documents_in_chain")
@patch("load_into_knowledge_store.get_topic_chain_factory")
def test_load_from_tsvs(chain_factory, store_documents_in_chain):
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

    assert chain_factory.called
    assert store_documents_in_chain.call_count == 2

    for item in store_documents_in_chain.call_args_list:
        assert len(item.args[1]) > 0  # documents

    config.TOPICS = "default"
