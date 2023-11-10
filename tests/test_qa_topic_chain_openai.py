from unittest.mock import MagicMock, patch

import chromadb
import pytest

from gen3discoveryai.topic_chains.question_answer_openai import (
    TopicChainOpenAiQuestionAnswerRAG,
)


def test_qa_topic_chain_openai_init_defaults():
    """
    Ensure that initialization happens successfully with all defaults
    """
    topic_chain = TopicChainOpenAiQuestionAnswerRAG("test")
    assert topic_chain.topic == "test"
    assert topic_chain.NAME == "TopicChainOpenAiQuestionAnswerRAG"
    assert topic_chain.vectorstore
    assert topic_chain.chain
    assert topic_chain.llm


def test_qa_topic_chain_init_provided_metadata():
    """
    Ensure that initialization happens successfully with provided metadata
    """
    metadata = {
        "model_name": "gpt-3.5-turbo",
        "model_temperature": "0.45",
        "num_similar_docs_to_find": "5",
        "similarity_score_threshold": "0.75",
    }
    topic_chain = TopicChainOpenAiQuestionAnswerRAG("test", metadata=metadata)
    assert topic_chain.topic == "test"
    assert topic_chain.NAME == "TopicChainOpenAiQuestionAnswerRAG"
    assert topic_chain.vectorstore
    assert topic_chain.chain

    assert topic_chain.chain.retriever.search_kwargs.get("k") == int(
        metadata["num_similar_docs_to_find"]
    )
    assert topic_chain.chain.retriever.search_kwargs.get("score_threshold") == float(
        metadata["similarity_score_threshold"]
    )
    assert topic_chain.llm.model_name == metadata["model_name"]
    assert topic_chain.llm.temperature == float(metadata["model_temperature"])


def test_qa_topic_chain_run():
    """
    Test that topic chain .run calls the chain with the query, args, and kwargs provided
    """
    topic_chain = TopicChainOpenAiQuestionAnswerRAG("test")
    topic_chain.chain = MagicMock()

    query = "some query"
    topic_chain.run(query, "an arg", another_thing="a kwarg")

    assert topic_chain.chain.called_with(
        {"query": query}, "an arg", another_thing="a kwarg"
    )


@pytest.mark.parametrize("does_chroma_collection_exist", [True, False])
@patch("gen3discoveryai.topic_chains.question_answer_openai.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_openai.Chroma")
def test_qa_topic_chain_store_knowledge(chroma, _, does_chroma_collection_exist):
    """
    Test storing documents into the vectorstore
    """
    topic_chain = TopicChainOpenAiQuestionAnswerRAG("test")
    topic_chain.vectorstore = MagicMock()

    # even if it already exists, the chromadb library may error, but the code should
    # handle this gracefully and just reuse the existing collection
    # in other words, this shouldn't have any result on the assertion made
    if does_chroma_collection_exist:
        chroma.side_effect = Exception

    topic_chain.store_knowledge(documents=["doc1", "doc2"])

    assert topic_chain.vectorstore.add_documents.called_with(documents=["doc1", "doc2"])
