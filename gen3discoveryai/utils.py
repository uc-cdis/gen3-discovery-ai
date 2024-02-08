from gen3discoveryai.factory import Factory
from gen3discoveryai.topic_chains import (
    TopicChainGoogleQuestionAnswerRAG,
    TopicChainOpenAiQuestionAnswerRAG,
)

# ... import more here as implemented


def get_topic_chain_factory():
    """
    Return a factory ready to generate instances of available topic chains

    Returns:
        gen3discoveryai.factory.Factory: A factory class with all the allowed topic chains registered
    """
    chain_factory = Factory()
    chain_factory.register(
        TopicChainOpenAiQuestionAnswerRAG.NAME,
        TopicChainOpenAiQuestionAnswerRAG,
    )
    chain_factory.register(
        TopicChainGoogleQuestionAnswerRAG.NAME,
        TopicChainGoogleQuestionAnswerRAG,
    )
    # ... register more here as implemented
    return chain_factory
