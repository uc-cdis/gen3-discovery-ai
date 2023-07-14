import os

from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=True)
OPENAI_API_KEY = config("OPENAI_API_KEY", cast=Secret, default=None)
URL_PREFIX = config("URL_PREFIX", default="/")

DEFAULT_EMBEDDINGS_PATH = config(
    "DEFAULT_EMBEDDINGS_PATH", cast=str, default="embeddings/embeddings.csv"
)

# csv string for all topics, associated topics can have system prompt and embeddings
# by having .env include {{`topic`.UPPER()}}_EMBEDDINGS_MODEL and
# {{`topic`.UPPER()}}_SYSTEM_PROMPT
TOPICS = config("TOPICS", cast=str, default="default")

# Note that changing this might require updating the Dockerfile caching
EMBEDDINGS_MODEL = config(
    "EMBEDDINGS_MODEL", cast=str, default="text-embedding-ada-002"
)
# This gets setup in the Dockerfile
if "TIKTOKEN_CACHE_DIR" not in os.environ:
    os.environ["TIKTOKEN_CACHE_DIR"] = "../cache"


# you can configure other embeddings for other topics like this: {{TOPIC}}_EMBEDDINGS_PATH
# requests to /ask/gen3docs will use these instead of the default
#
# GEN3DOCS_EMBEDDINGS_MODEL = config(
#     "GEN3DOC_SEMBEDDINGS_MODEL",
#     cast=str,
#     default=(
#         "..."
#     ),
# )
#

CHAT_MODEL = config("CHAT_MODEL", cast=str, default="gpt-3.5-turbo")

DEFAULT_SYSTEM_PROMPT = config(
    "DEFAULT_SYSTEM_PROMPT",
    cast=str,
    default=(
        "You answer questions about a specific topic. You'll be given relevant "
        "information for that topic. You are acting as a search assistant "
        "for a user who will be asking you questions. "
        "The user is likely trying to find data of "
        "interest for a particular reason. You should try to answer and "
        "recommend information that may be of interest to that researcher. "
        "If you are using any particular source to answer, you should cite that "
        "and tell the user where they can find more information."
    ),
)

# you can configure system prompts for other topics like this: {{TOPIC}}_SYSTEM_PROMPT
# requests to /ask/gen3docs will use this prompt instead of the default
#
# GEN3DOCS_SYSTEM_PROMPT = config(
#     "GEN3DOCS_SYSTEM_PROMPT",
#     cast=str,
#     default=(
#         "..."
#     ),
# )
#

# set global var explicitly here so you can still do config.THING elsewhere
for topic in TOPICS.split(","):
    if topic == "default":
        continue

    globals()[f"{topic.upper()}_EMBEDDINGS_PATH"] = config(
        f"{topic.upper()}_EMBEDDINGS_PATH", cast=str, default=DEFAULT_EMBEDDINGS_PATH
    )
    globals()[f"{topic.upper()}_SYSTEM_PROMPT"] = config(
        f"{topic.upper()}_SYSTEM_PROMPT", cast=str, default=DEFAULT_SYSTEM_PROMPT
    )
