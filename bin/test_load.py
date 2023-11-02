import os
from unittest.mock import MagicMock, patch

from load_into_knowledge_store import load_tsvs_from_dir

from gen3discoveryai import config


@patch("load_into_knowledge_store._store_documents_in_chain")
@patch("load_into_knowledge_store.get_topics_from_config")
def test_load_from_tsvs(config_topics, store_documents_in_chain):
    """
    Test that the loading from TSVs pulls the correct information from various files and
    aggregates files that begin with the same topic name.
    """
    config_topics.return_value = {
        "default": {"topic_chain": MagicMock()},
        "bdc": {"topic_chain": MagicMock()},
    }

    directory = os.path.abspath(
        os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/../tests/tsvs"
    )

    load_tsvs_from_dir(
        directory=directory,
        source_column_name="guid",
        token_splitter_chunk_size=1000,
        delimiter="\t",
    )

    assert config_topics.called
    assert store_documents_in_chain.call_count == 2

    for item in store_documents_in_chain.call_args_list:
        assert len(item.args[1]) > 0  # documents

    config.TOPICS = "default"
