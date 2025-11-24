from unittest.mock import MagicMock, patch

import pytest

from gen3discoveryai.topic_chains.question_answer_google import (
    TopicChainGoogleQuestionAnswerRAG,
)


@patch("gen3discoveryai.topic_chains.question_answer_google.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_google.VertexAIEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_google.ChatVertexAI")
def test_qa_topic_chain_google_init_defaults(vertexai, embeddings, _):
    """
    Ensure that initialization happens successfully with all defaults
    """
    topic_chain = TopicChainGoogleQuestionAnswerRAG("test")
    assert topic_chain.topic == "test"
    assert topic_chain.NAME == "TopicChainGoogleQuestionAnswerRAG"
    assert topic_chain.vectorstore.embeddings
    assert topic_chain.chain
    assert topic_chain.llm

    assert vertexai.called
    assert embeddings.called


@patch("gen3discoveryai.topic_chains.question_answer_google.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_google.VertexAIEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_google.ChatVertexAI")
def test_qa_topic_chain_init_provided_metadata(vertexai, embeddings, retrievalqa):
    """
    Ensure that initialization happens successfully with provided metadata
    """
    metadata = {
        "model_name": "chat-bison",
        "model_temperature": "0.45",
        "num_similar_docs_to_find": "5",
        "similarity_score_threshold": "0.75",
        "location": "us-east4",
        "max_output_tokens": "1001",
        "top_p": "0.70",
        "top_k": "50",
    }
    topic_chain = TopicChainGoogleQuestionAnswerRAG("test", metadata=metadata)
    assert topic_chain.topic == "test"
    assert topic_chain.NAME == "TopicChainGoogleQuestionAnswerRAG"
    assert topic_chain.vectorstore.embeddings
    assert topic_chain.chain

    assert vertexai.call_args.kwargs.get("model_name") == metadata["model_name"]
    assert vertexai.call_args.kwargs.get("temperature") == float(
        metadata["model_temperature"]
    )
    assert vertexai.call_args.kwargs.get("location") == metadata["location"]
    assert vertexai.call_args.kwargs.get("max_output_tokens") == int(
        metadata["max_output_tokens"]
    )
    assert vertexai.call_args.kwargs.get("top_p") == float(metadata["top_p"])
    assert vertexai.call_args.kwargs.get("top_k") == int(metadata["top_k"])

    assert vertexai.called
    assert embeddings.called


@patch("gen3discoveryai.topic_chains.question_answer_google.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_google.VertexAIEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_google.ChatVertexAI")
def test_qa_topic_chain_run(vertexai, embeddings, _):
    """
    Test that topic chain .run calls the chain with the query, args, and kwargs provided
    """
    topic_chain = TopicChainGoogleQuestionAnswerRAG("test")
    topic_chain.chain = MagicMock()

    query = "some query"
    topic_chain.run(query, "an arg", another_thing="a kwarg")

    topic_chain.chain.invoke.assert_called_with(
        {"query": query}, "an arg", include_run_info=True, another_thing="a kwarg"
    )
    assert vertexai.called
    assert embeddings.called


@pytest.mark.parametrize("does_chroma_collection_exist", [True, False])
@patch("gen3discoveryai.topic_chains.question_answer_google.VertexAIEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_google.ChatVertexAI")
@patch("gen3discoveryai.topic_chains.question_answer_google.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_google.Chroma")
def test_qa_topic_chain_store_knowledge(
    chroma, _, vertexai, embeddings, does_chroma_collection_exist
):
    """
    Test storing documents into the vectorstore
    """
    topic_chain = TopicChainGoogleQuestionAnswerRAG("test")
    topic_chain.vectorstore = MagicMock()

    # even if it already exists, the chromadb library may error, but the code should
    # handle this gracefully and just reuse the existing collection
    # in other words, this shouldn't have any result on the assertion made
    if does_chroma_collection_exist:
        chroma.side_effect = Exception

    topic_chain.store_knowledge(documents=["doc1", "doc2"])

    topic_chain.vectorstore.add_documents.assert_called_with(["doc1", "doc2"])

    assert vertexai.called
    assert embeddings.called
