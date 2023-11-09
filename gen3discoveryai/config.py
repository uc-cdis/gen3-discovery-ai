import cdislogging
from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")
if not config.file_values:
    config = Config("env")

DEBUG = config("DEBUG", cast=bool, default=False)
VERBOSE_LLM_LOGS = config("VERBOSE_LLM_LOGS", cast=bool, default=False)

logging = cdislogging.get_logger(__name__, log_level="debug" if DEBUG else "info")

# will skip authorization when a token is not provided. note that if a token is provided, then
# auth will still occur
DEBUG_SKIP_AUTH = config("DEBUG_SKIP_AUTH", cast=bool, default=False)

# this will effectively turn off authorization checking,
# allowing for anyone to use the AI functionality
ALLOW_ANONYMOUS_ACCESS = config("ALLOW_ANONYMOUS_ACCESS", cast=bool, default=False)

if DEBUG:
    logging.info(f"DEBUG is {DEBUG}")
if VERBOSE_LLM_LOGS:
    logging.info(f"VERBOSE_LLM_LOGS is {VERBOSE_LLM_LOGS}")
if DEBUG_SKIP_AUTH:
    logging.warning(
        f"DEBUG_SKIP_AUTH is {DEBUG_SKIP_AUTH}. Authorization will be SKIPPED if no token is provided. "
        "FOR NON-PRODUCTION USE ONLY!! USE WITH CAUTION!!"
    )
if ALLOW_ANONYMOUS_ACCESS:
    logging.warning(
        f"ALLOW_ANONYMOUS_ACCESS is {ALLOW_ANONYMOUS_ACCESS}. Authorization will be SKIPPED. "
        "ENSURE THIS IS ACCEPTABLE!!"
    )

# ensure you set this env var with the path to the .json Google application credentials
# https://cloud.google.com/docs/authentication/application-default-credentials#GAC
#
GOOGLE_APPLICATION_CREDENTIALS = config(
    "GOOGLE_APPLICATION_CREDENTIALS", cast=Secret, default="credentials.json"
)

OPENAI_API_KEY = config("OPENAI_API_KEY", cast=Secret, default=None)
URL_PREFIX = config("URL_PREFIX", default="/")

# csv strings for all topic names
#
# topics are a logical combination of the following:
#     - langchain chain
#     - system prompt
#
# To specify the above, you must supply more configuration than just the topic name here
# .env should also include:
#   - {{`topic_name`.upper()}}_CHAIN_NAME
#   - {{`topic_name`.upper()}}_SYSTEM_PROMPT
TOPICS = config("TOPICS", cast=str, default="default")

DEFAULT_CHAIN_NAME = config(
    "DEFAULT_CHAIN_NAME",
    cast=str,
    default="TopicChainGoogleQuestionAnswerRAG",
)
# you can configure other topics like this: {{`topic_name`.upper()}}_CHAIN_NAME
# requests to /ask?topic=gen3docs will use these instead of the default
#
# NOTE: the provided value must be an available one from the `gen3discoveryai.knowledge_store`
#
#   GEN3DOCS_CHAIN_NAME = config(
#       "GEN3DOC_CHAIN_NAME",
#       cast=str,
#       default=(
#           "..."
#       ),
#   )
#


DEFAULT_SYSTEM_PROMPT = config(
    "DEFAULT_SYSTEM_PROMPT",
    cast=str,
    default=(
        "You answer questions about a specific topic. You'll be given relevant "
        "context for that topic. You are acting as a search assistant "
        "for a researcher who will be asking you questions. "
        "The researcher is likely trying to find data of "
        "interest for a particular reason or with specific criteria. You answer and "
        "recommend information that may be of interest to that researcher. "
        "If you are using any particular context to answer, you should cite that "
        "and tell the user where they can find more information. "
        "The user may not be able to see the documents you are citing, so provide "
        "the relevant information in your response. "
        "If you don't know the answer, just say that you don't know, don't try to make up an answer. "
        "If you don't believe what the user is looking for is available in the context, say so. "
    ),
)

# you can configure system prompts for other topics like this: {{`topic_name`.upper()}}_SYSTEM_PROMPT
# requests to /ask?topic=gen3docs will use this prompt instead of the default
#
#   GEN3DOCS_SYSTEM_PROMPT = config(
#       "GEN3DOCS_SYSTEM_PROMPT",
#       cast=str,
#       default=(
#           "..."
#       ),
#   )
#

# this gets populated later by parsing the DEFAULT_RAW_METADATA
DEFAULT_METADATA = {}

# NOTE: when changing the `num_similar_docs_to_find` metadata you need to consider the token limits of the model you're
# using and potentially adjust the token size of the split documents in the vectorstore. This is tuned right now for
# 4 documents around 1000 tokens to be sent alongside a max 97 token query (to hit the max tokens for
# gpt-3.5-turbo of 4097). So if you want to adjust this metadata, you need to consider adjusting them in tandem
# (e.g. you can't just bump the num_similar_docs_to_find to 10).
DEFAULT_RAW_METADATA = config(
    "DEFAULT_RAW_METADATA",
    cast=str,
    default="model_name:gpt-3.5-turbo,model_temperature:0.33,num_similar_docs_to_find:4,similarity_score_threshold:0.5",
)
DEFAULT_DESCRIPTION = config(
    "DEFAULT_DESCRIPTION",
    cast=str,
    default="",
)

# set global var explicitly here, so you can still do config.THING elsewhere
for topic in TOPICS.split(","):
    globals()[f"{topic.upper()}_CHAIN_NAME"] = config(
        f"{topic.upper()}_CHAIN_NAME",
        cast=str,
        default=DEFAULT_CHAIN_NAME,
    )
    globals()[f"{topic.upper()}_SYSTEM_PROMPT"] = config(
        f"{topic.upper()}_SYSTEM_PROMPT", cast=str, default=DEFAULT_SYSTEM_PROMPT
    )
    globals()[f"{topic.upper()}_DESCRIPTION"] = config(
        f"{topic.upper()}_DESCRIPTION", cast=str, default=DEFAULT_DESCRIPTION
    )

    metadata = {}
    try:
        RAW_METADATA = (
            config(
                f"{topic.upper()}_RAW_METADATA", cast=str, default=DEFAULT_RAW_METADATA
            )
            or ""
        )
        logging.debug(f"Metadata for: {topic.upper()}_RAW_METADATA: {RAW_METADATA}")
        for metadata_entry in [item for item in RAW_METADATA.split(",") if item]:
            name, value = metadata_entry.split(":")
            metadata[name] = value
    except Exception as exc:
        logging.error(
            f"Cannot parse provided metadata for: {topic.upper()}_METADATA. "
            f"Ensure that it's a comma-separated list of entries where each "
            "entry is a `{name}:{value}` with the colon."
        )
        logging.debug(f"exc: {exc}")
        raise

    globals()[f"{topic.upper()}_METADATA"] = metadata

# Note: this gets populated in main
topics = {}
