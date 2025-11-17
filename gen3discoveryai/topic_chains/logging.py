from typing import Any, Dict, List, Union

from langchain_classic.callbacks.base import BaseCallbackHandler
from langchain_classic.schema import AgentAction, AgentFinish, BaseMessage, LLMResult

from gen3discoveryai import config, logging


class LoggingCallbackHandler(BaseCallbackHandler):
    """
    Custom Callback handles all possible callbacks from chains and allows for our
    own handing. For now, this just ensures the use of our logging library
    and provides configuration for verbose/less-verbose options.
    """

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Print out the prompts."""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(f"Starting LLM: {serialized}, with prompts: {prompts}")

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ) -> Any:
        """Run when Chat Model starts running."""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(
                f"Starting Chat Model: {serialized}, with messages: {messages}"
            )

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Log if verbose on new token"""
        logging.debug(f"on_llm_new_token: {token}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log if verbose on llm end"""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(f"End of LLM. Response: {response}")

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Log error."""
        logging.error(f"on_llm_error: {error}")

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Print out that we are entering a chain."""
        class_name = serialized.get("name", serialized.get("id", ["<unknown>"])[-1])
        logging.debug(f"Entering new {class_name} chain...")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Print out that we finished a chain."""
        logging.debug(f"Finished chain. Outputs: {outputs}")

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        """Log error."""
        logging.error(f"on_chain_error: {error}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Run when tool starts running."""
        if config.VERBOSE_LLM_LOGS:
            class_name = serialized.get("name", serialized.get("id", ["<unknown>"])[-1])
            logging.debug(f"on_tool_start: {class_name}, input: {input_str}")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Run when tool ends running."""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(f"on_tool_end: {output}")

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when tool errors."""
        logging.error(f"on_tool_error: {error}")

    def on_text(self, text: str, **kwargs: Any) -> Any:
        """Run on arbitrary text."""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(f"on_text: {text}")

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run on agent action."""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(f"on_agent_action: {action}")

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """Run on agent end."""
        if config.VERBOSE_LLM_LOGS:
            logging.debug(f"on_agent_finish: {finish}")
