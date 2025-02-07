from unittest.mock import MagicMock, patch

import pytest

from gen3discoveryai.topic_chains.question_answer_ollama import (
    TopicChainOllamaQuestionAnswerRAG,
)


@patch("gen3discoveryai.topic_chains.question_answer_ollama.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.OllamaEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.ChatOllama")
def test_qa_topic_chain_ollama_init_defaults(ollama, embeddings, _):
    """
    Ensure that initialization happens successfully with all defaults
    """
    topic_chain = TopicChainOllamaQuestionAnswerRAG("test")
    assert topic_chain.topic == "test"
    assert topic_chain.NAME == "TopicChainOllamaQuestionAnswerRAG"
    assert topic_chain.vectorstore.embeddings
    assert topic_chain.chain
    assert topic_chain.llm

    assert ollama.called
    assert embeddings.called


@patch("gen3discoveryai.topic_chains.question_answer_ollama.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.OllamaEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.ChatOllama")
def test_qa_topic_chain_init_provided_metadata(ollama, embeddings, retrievalqa):
    """
    Ensure that initialization happens successfully with provided metadata
    """
    metadata = {
        "model_name": "starcoder2:3b",
        "model_temperature": "0.45",
        "num_similar_docs_to_find": "5",
        "similarity_score_threshold": "0.75",
        "max_output_tokens": "1001",
        "top_p": "0.70",
        "top_k": "50",
    }
    topic_chain = TopicChainOllamaQuestionAnswerRAG("test", metadata=metadata)
    assert topic_chain.topic == "test"
    assert topic_chain.NAME == "TopicChainOllamaQuestionAnswerRAG"
    assert topic_chain.vectorstore.embeddings
    assert topic_chain.chain

    assert ollama.call_args.kwargs.get("model") == metadata["model_name"]
    assert ollama.call_args.kwargs.get("temperature") == float(
        metadata["model_temperature"]
    )
    assert ollama.call_args.kwargs.get("num_predict") == int(
        metadata["max_output_tokens"]
    )
    assert ollama.call_args.kwargs.get("top_p") == float(metadata["top_p"])
    assert ollama.call_args.kwargs.get("top_k") == int(metadata["top_k"])

    assert ollama.called
    assert embeddings.called


@patch("gen3discoveryai.topic_chains.question_answer_ollama.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.OllamaEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.ChatOllama")
def test_qa_topic_chain_run(ollama, embeddings, _):
    """
    Test that topic chain .run calls the chain with the query, args, and kwargs provided
    """
    topic_chain = TopicChainOllamaQuestionAnswerRAG("test")
    topic_chain.chain = MagicMock()

    query = "some query"
    topic_chain.run(query, "an arg", another_thing="a kwarg")

    assert topic_chain.chain.called_with(
        {"query": query}, "an arg", another_thing="a kwarg"
    )
    assert ollama.called
    assert embeddings.called


@pytest.mark.parametrize("does_chroma_collection_exist", [True, False])
@patch("gen3discoveryai.topic_chains.question_answer_ollama.OllamaEmbeddings")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.ChatOllama")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.RetrievalQA")
@patch("gen3discoveryai.topic_chains.question_answer_ollama.Chroma")
def test_qa_topic_chain_store_knowledge(
    chroma, _, ollama, embeddings, does_chroma_collection_exist
):
    """
    Test storing documents into the vectorstore
    """
    topic_chain = TopicChainOllamaQuestionAnswerRAG("test")
    topic_chain.vectorstore = MagicMock()

    # even if it already exists, the chromadb library may error, but the code should
    # handle this gracefully and just reuse the existing collection
    # in other words, this shouldn't have any result on the assertion made
    if does_chroma_collection_exist:
        chroma.side_effect = Exception

    topic_chain.store_knowledge(documents=["doc1", "doc2"])

    assert topic_chain.vectorstore.add_documents.called_with(documents=["doc1", "doc2"])

    assert ollama.called
    assert embeddings.called
