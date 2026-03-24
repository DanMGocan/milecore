"""LLM abstraction layer for SaaS and BYOK deployments.

SaaS instances use the native Anthropic SDK directly (fast path, no LiteLLM
overhead).  BYOK instances use LiteLLM for multi-provider support.  Both paths
return normalised responses so that ``claude_client.py`` can process them
without knowing the provider.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Generator

import anthropic
import litellm

from backend.config import ANTHROPIC_API_KEY, ANTHROPIC_API_KEY_SPARE, CLAUDE_MODEL
from backend.database import execute_query
from backend.key_vault import decrypt_api_key

logger = logging.getLogger(__name__)

# Silence LiteLLM's noisy default logging
litellm.suppress_debug_info = True

# ---------------------------------------------------------------------------
# Supported models
# ---------------------------------------------------------------------------

SUPPORTED_MODELS: dict[str, list[dict[str, str]]] = {
    "anthropic": [
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "cost_tier": "mid", "tool_quality": "Excellent"},
        {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "cost_tier": "high", "tool_quality": "Excellent"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "cost_tier": "low", "tool_quality": "Good"},
    ],
    "openai": [
        {"id": "gpt-5.4", "name": "GPT-5.4", "cost_tier": "high", "tool_quality": "Excellent"},
        {"id": "gpt-5.4-mini", "name": "GPT-5.4 Mini", "cost_tier": "mid", "tool_quality": "Very Good"},
        {"id": "gpt-5.4-nano", "name": "GPT-5.4 Nano", "cost_tier": "low", "tool_quality": "Good"},
    ],
    "google": [
        {"id": "gemini-3.1-pro", "name": "Gemini 3.1 Pro", "cost_tier": "high", "tool_quality": "Very Good"},
        {"id": "gemini-3-flash", "name": "Gemini 3 Flash", "cost_tier": "mid", "tool_quality": "Good"},
        {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite", "cost_tier": "low", "tool_quality": "Moderate"},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "cost_tier": "low", "tool_quality": "Good"},
    ],
    "deepseek": [
        {"id": "deepseek-chat", "name": "DeepSeek V3", "cost_tier": "low", "tool_quality": "Good"},
        {"id": "deepseek-reasoner", "name": "DeepSeek R1", "cost_tier": "mid", "tool_quality": "Good"},
    ],
}

# ---------------------------------------------------------------------------
# Normalised response types
# ---------------------------------------------------------------------------


@dataclass
class NormalizedResponse:
    """Provider-agnostic response, normalised to Anthropic conventions."""

    stop_reason: str  # "end_turn" or "tool_use"
    content: list[dict]  # Anthropic-style content blocks
    usage: dict = field(default_factory=lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    })


# ---------------------------------------------------------------------------
# SaaS Anthropic client singleton with spare-key failover
# ---------------------------------------------------------------------------

_primary_client: anthropic.Anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_spare_client: anthropic.Anthropic | None = (
    anthropic.Anthropic(api_key=ANTHROPIC_API_KEY_SPARE) if ANTHROPIC_API_KEY_SPARE else None
)
_active_client: anthropic.Anthropic = _primary_client


def _get_saas_client() -> anthropic.Anthropic:
    """Return the active SaaS Anthropic client."""
    return _active_client


def _swap_to_spare() -> bool:
    """Switch to the spare API key.  Returns True if swap succeeded."""
    global _active_client
    if _spare_client and _active_client is _primary_client:
        _active_client = _spare_client
        logger.warning("Switched to spare Anthropic API key")
        return True
    return False


# ---------------------------------------------------------------------------
# LLM config cache (per-instance, 60 s TTL)
# ---------------------------------------------------------------------------

_config_cache: dict[int, dict[str, Any]] = {}
_CONFIG_TTL = 60  # seconds


def _cache_get(instance_id: int) -> dict[str, Any] | None:
    entry = _config_cache.get(instance_id)
    if entry is None:
        return None
    if time.time() - entry["_ts"] > _CONFIG_TTL:
        _config_cache.pop(instance_id, None)
        return None
    return entry


def _cache_set(instance_id: int, data: dict[str, Any]) -> None:
    _config_cache[instance_id] = {**data, "_ts": time.time()}


def clear_config_cache(instance_id: int | None = None) -> None:
    """Clear cached LLM config.  If *instance_id* is None, clear all."""
    if instance_id is None:
        _config_cache.clear()
    else:
        _config_cache.pop(instance_id, None)


# ---------------------------------------------------------------------------
# get_llm_config / get_deployment_mode
# ---------------------------------------------------------------------------

def get_llm_config(instance_id: int) -> dict[str, Any]:
    """Return the LLM configuration for an instance.

    For SaaS instances the platform Anthropic key is used.  For BYOK
    instances the user's encrypted key is decrypted on every call (the
    decrypted key is never cached).

    Returns::

        {
            "deployment_mode": "saas" | "byok",
            "provider": "anthropic" | "openai" | "google",
            "model": "<model-id>",
            "api_key": "<plaintext key>",
        }
    """
    cached = _cache_get(instance_id)

    if cached and cached["deployment_mode"] == "saas":
        # SaaS config is fully cacheable (key comes from env)
        return {
            "deployment_mode": "saas",
            "provider": "anthropic",
            "model": CLAUDE_MODEL,
            "api_key": ANTHROPIC_API_KEY,
        }

    if cached and cached["deployment_mode"] == "byok":
        # Re-use cached provider/model but always decrypt the key fresh
        row = execute_query(
            "SELECT llm_api_key_encrypted, llm_api_key_iv FROM instances WHERE id = ?",
            [instance_id],
            instance_id=None,
        )
        if not row.get("rows"):
            raise ValueError(f"Instance {instance_id} not found")
        r = row["rows"][0]
        api_key = decrypt_api_key(
            bytes(r["llm_api_key_encrypted"]),
            bytes(r["llm_api_key_iv"]),
        )
        return {
            "deployment_mode": "byok",
            "provider": cached["provider"],
            "model": cached["model"],
            "api_key": api_key,
        }

    # No cache — query the database
    result = execute_query(
        "SELECT deployment_mode, llm_provider, llm_model, "
        "llm_api_key_encrypted, llm_api_key_iv "
        "FROM instances WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    if not result.get("rows"):
        raise ValueError(f"Instance {instance_id} not found")

    row = result["rows"][0]
    mode = row["deployment_mode"] or "saas"
    provider = row["llm_provider"] or "anthropic"
    model = row["llm_model"] or CLAUDE_MODEL

    # Cache deployment_mode / provider / model (NOT the decrypted key)
    _cache_set(instance_id, {
        "deployment_mode": mode,
        "provider": provider,
        "model": model,
    })

    if mode == "saas":
        return {
            "deployment_mode": "saas",
            "provider": "anthropic",
            "model": CLAUDE_MODEL,
            "api_key": ANTHROPIC_API_KEY,
        }

    # BYOK — decrypt the key
    encrypted = row["llm_api_key_encrypted"]
    iv = row["llm_api_key_iv"]
    if not encrypted or not iv:
        raise ValueError(
            f"Instance {instance_id} is configured as BYOK but has no API key stored"
        )
    api_key = decrypt_api_key(bytes(encrypted), bytes(iv))
    return {
        "deployment_mode": "byok",
        "provider": provider,
        "model": model,
        "api_key": api_key,
    }


def get_deployment_mode(instance_id: int) -> str:
    """Return ``'saas'`` or ``'byok'`` for *instance_id* (cached)."""
    cached = _cache_get(instance_id)
    if cached:
        return cached["deployment_mode"]
    config = get_llm_config(instance_id)
    return config["deployment_mode"]


# ---------------------------------------------------------------------------
# Tool format conversion helpers
# ---------------------------------------------------------------------------

def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
    """Convert tools from OpenAI format to Anthropic format.

    OpenAI format::

        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}

    Anthropic format::

        {"name": "...", "description": "...", "input_schema": {...}}

    Tools already in Anthropic format (with ``input_schema``) are returned
    as-is.
    """
    converted = []
    for tool in tools:
        if "input_schema" in tool:
            # Already in Anthropic format
            converted.append(tool)
        elif tool.get("type") == "function" and "function" in tool:
            fn = tool["function"]
            converted.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        else:
            # Unknown format — pass through and let the API reject it
            converted.append(tool)
    return converted


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert tools from Anthropic format to OpenAI format.

    Anthropic format::

        {"name": "...", "description": "...", "input_schema": {...}}

    OpenAI format::

        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}

    Tools already in OpenAI format (with ``type: "function"``) are returned
    as-is.
    """
    converted = []
    for tool in tools:
        if tool.get("type") == "function":
            # Already in OpenAI format
            converted.append(tool)
        elif "input_schema" in tool:
            converted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["input_schema"],
                },
            })
        else:
            converted.append(tool)
    return converted


# ---------------------------------------------------------------------------
# System prompt preparation
# ---------------------------------------------------------------------------

def _prepare_system(provider: str, system_blocks: list[dict]) -> Any:
    """Prepare the system prompt for the target provider.

    - **Anthropic**: returns *system_blocks* as-is (preserves cache_control).
    - **OpenAI / Google**: concatenates all block texts into a single string
      (these providers don't support cache_control blocks).
    """
    if provider == "anthropic":
        return system_blocks
    # Flatten to a single string for non-Anthropic providers
    parts = []
    for block in system_blocks:
        text = block.get("text", "")
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LiteLLM model ID mapping
# ---------------------------------------------------------------------------

def _convert_messages_for_openai(messages: list[dict]) -> list[dict]:
    """Convert Anthropic-format messages to OpenAI format for LiteLLM.

    Anthropic uses content blocks for tool_use/tool_result within user/assistant
    messages.  OpenAI uses ``tool_calls`` on assistant messages and separate
    ``role: "tool"`` messages for results.
    """
    converted: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")

        # Plain text message — pass through
        if isinstance(content, str):
            converted.append(msg)
            continue

        if not isinstance(content, list):
            converted.append(msg)
            continue

        # Check what block types are present
        has_tool_use = any(b.get("type") == "tool_use" for b in content if isinstance(b, dict))
        has_tool_result = any(b.get("type") == "tool_result" for b in content if isinstance(b, dict))

        if has_tool_use and role == "assistant":
            # Convert assistant tool_use blocks to OpenAI tool_calls format
            text_parts = []
            tool_calls = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    })
            openai_msg = {
                "role": "assistant",
                "content": "\n".join(text_parts) if text_parts else None,
            }
            if tool_calls:
                openai_msg["tool_calls"] = tool_calls
            converted.append(openai_msg)

        elif has_tool_result:
            # Convert tool_result blocks to separate role:"tool" messages
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    converted.append({
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id", ""),
                        "content": block.get("content", ""),
                    })

        else:
            # Regular message with text blocks — flatten to string
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            converted.append({"role": role, "content": "\n".join(text_parts)})

    return converted


def _litellm_model_id(provider: str, model: str) -> str:
    """Return the LiteLLM model identifier.

    Examples:
        ``("anthropic", "claude-sonnet-4-6")`` -> ``"anthropic/claude-sonnet-4-6"``
        ``("openai", "gpt-5.4")``              -> ``"openai/gpt-5.4"``
        ``("google", "gemini-3.1-pro")``        -> ``"gemini/gemini-3.1-pro"``
    """
    prefix_map = {
        "anthropic": "anthropic",
        "openai": "openai",
        "google": "gemini",
        "deepseek": "deepseek",
    }
    prefix = prefix_map.get(provider, provider)
    return f"{prefix}/{model}"


# ---------------------------------------------------------------------------
# Response normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_anthropic_response(response: Any) -> NormalizedResponse:
    """Convert a native Anthropic API response to NormalizedResponse."""
    content: list[dict] = []
    for block in response.content:
        if block.type == "text":
            content.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            content.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            response.usage, "cache_creation_input_tokens", 0
        ) or 0,
        "cache_read_input_tokens": getattr(
            response.usage, "cache_read_input_tokens", 0
        ) or 0,
    }

    return NormalizedResponse(
        stop_reason=response.stop_reason,
        content=content,
        usage=usage,
    )


def _normalize_litellm_response(response: Any) -> NormalizedResponse:
    """Convert a LiteLLM (OpenAI-format) response to NormalizedResponse."""
    choice = response.choices[0]
    message = choice.message
    content: list[dict] = []

    # Text content
    if message.content:
        content.append({"type": "text", "text": message.content})

    # Tool calls
    has_tool_use = False
    if message.tool_calls:
        has_tool_use = True
        for tc in message.tool_calls:
            args = tc.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {"raw": args}
            content.append({
                "type": "tool_use",
                "id": tc.id or f"toolu_{uuid.uuid4().hex[:24]}",
                "name": tc.function.name,
                "input": args,
            })

    # Normalise stop reason to Anthropic terms
    finish_reason = choice.finish_reason
    if has_tool_use or finish_reason == "tool_calls":
        stop_reason = "tool_use"
    else:
        stop_reason = "end_turn"

    # Usage
    u = response.usage
    usage = {
        "input_tokens": getattr(u, "prompt_tokens", 0) or 0,
        "output_tokens": getattr(u, "completion_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
    }

    return NormalizedResponse(stop_reason=stop_reason, content=content, usage=usage)


# ---------------------------------------------------------------------------
# make_completion
# ---------------------------------------------------------------------------

def make_completion(
    instance_id: int,
    messages: list[dict],
    system: list[dict],
    tools: list[dict],
    max_tokens: int = 4096,
) -> NormalizedResponse:
    """Make a non-streaming LLM completion.

    Automatically routes to the Anthropic SDK (SaaS fast path) or LiteLLM
    (BYOK) based on the instance's deployment mode.
    """
    config = get_llm_config(instance_id)

    if config["deployment_mode"] == "saas":
        return _saas_completion(config, messages, system, tools, max_tokens)
    else:
        return _byok_completion(config, messages, system, tools, max_tokens)


def _saas_completion(
    config: dict,
    messages: list[dict],
    system: list[dict],
    tools: list[dict],
    max_tokens: int,
) -> NormalizedResponse:
    """SaaS fast path: direct Anthropic SDK call with spare-key failover."""
    anthropic_tools = _to_anthropic_tools(tools)
    system_blocks = _prepare_system("anthropic", system)

    kwargs: dict[str, Any] = {
        "model": config["model"],
        "max_tokens": max_tokens,
        "system": system_blocks,
        "messages": messages,
    }
    if anthropic_tools:
        kwargs["tools"] = anthropic_tools

    try:
        response = _get_saas_client().messages.create(**kwargs)
    except (anthropic.RateLimitError, anthropic.AuthenticationError):
        if _swap_to_spare():
            response = _get_saas_client().messages.create(**kwargs)
        else:
            raise

    return _normalize_anthropic_response(response)


def _byok_completion(
    config: dict,
    messages: list[dict],
    system: list[dict],
    tools: list[dict],
    max_tokens: int,
) -> NormalizedResponse:
    """BYOK path: LiteLLM multi-provider call."""
    provider = config["provider"]
    model_id = _litellm_model_id(provider, config["model"])
    system_content = _prepare_system(provider, system)
    openai_tools = _to_openai_tools(tools)

    # Convert Anthropic-format messages to OpenAI format for LiteLLM
    converted_messages = _convert_messages_for_openai(messages)

    # Build messages list with system prompt prepended
    llm_messages: list[dict] = []
    if system_content:
        if isinstance(system_content, str):
            llm_messages.append({"role": "system", "content": system_content})
        else:
            # Anthropic cache_control blocks — flatten for LiteLLM
            text = "\n\n".join(b.get("text", "") for b in system_content if b.get("text"))
            llm_messages.append({"role": "system", "content": text})
    llm_messages.extend(converted_messages)

    kwargs: dict[str, Any] = {
        "model": model_id,
        "messages": llm_messages,
        "api_key": config["api_key"],
        "max_tokens": max_tokens,
    }
    if openai_tools:
        kwargs["tools"] = openai_tools

    try:
        response = litellm.completion(**kwargs)
    except Exception as exc:
        raise LLMError(_friendly_byok_error(exc, provider)) from exc

    return _normalize_litellm_response(response)


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

class StreamContext:
    """Wraps streaming for both SaaS and BYOK deployments.

    Usage::

        ctx = make_stream(instance_id, messages, system, tools)
        for chunk in ctx.text_stream():
            send_to_client(chunk)
        final = ctx.get_final_response()
    """

    def __init__(
        self,
        instance_id: int,
        messages: list[dict],
        system: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
    ):
        self._config = get_llm_config(instance_id)
        self._messages = messages
        self._system = system
        self._tools = tools
        self._max_tokens = max_tokens
        self._final_response: NormalizedResponse | None = None

    def text_stream(self) -> Generator[str, None, None]:
        """Yield text chunks from the LLM response."""
        if self._config["deployment_mode"] == "saas":
            yield from self._stream_saas()
        else:
            yield from self._stream_byok()

    def get_final_response(self) -> NormalizedResponse:
        """Return the final normalised response after streaming completes.

        Must be called after ``text_stream()`` has been fully consumed.
        """
        if self._final_response is None:
            raise RuntimeError(
                "get_final_response() called before text_stream() was consumed"
            )
        return self._final_response

    # -- SaaS streaming (Anthropic SDK) ------------------------------------

    def _stream_saas(self) -> Generator[str, None, None]:
        anthropic_tools = _to_anthropic_tools(self._tools)
        system_blocks = _prepare_system("anthropic", self._system)

        kwargs: dict[str, Any] = {
            "model": self._config["model"],
            "max_tokens": self._max_tokens,
            "system": system_blocks,
            "messages": self._messages,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        try:
            with _get_saas_client().messages.stream(**kwargs) as stream:
                for text_chunk in stream.text_stream:
                    yield text_chunk
                response = stream.get_final_message()
        except (anthropic.RateLimitError, anthropic.AuthenticationError):
            if _swap_to_spare():
                with _get_saas_client().messages.stream(**kwargs) as stream:
                    for text_chunk in stream.text_stream:
                        yield text_chunk
                    response = stream.get_final_message()
            else:
                raise

        self._final_response = _normalize_anthropic_response(response)

    # -- BYOK streaming (LiteLLM) ------------------------------------------

    def _stream_byok(self) -> Generator[str, None, None]:
        provider = self._config["provider"]
        model_id = _litellm_model_id(provider, self._config["model"])
        system_content = _prepare_system(provider, self._system)
        openai_tools = _to_openai_tools(self._tools)

        converted_messages = _convert_messages_for_openai(self._messages)

        llm_messages: list[dict] = []
        if system_content:
            if isinstance(system_content, str):
                llm_messages.append({"role": "system", "content": system_content})
            else:
                text = "\n\n".join(b.get("text", "") for b in system_content if b.get("text"))
                llm_messages.append({"role": "system", "content": text})
        llm_messages.extend(converted_messages)

        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": llm_messages,
            "api_key": self._config["api_key"],
            "max_tokens": self._max_tokens,
            "stream": True,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        try:
            stream_response = litellm.completion(**kwargs)
        except Exception as exc:
            raise LLMError(_friendly_byok_error(exc, provider)) from exc

        # Accumulate text and tool calls from streamed deltas
        collected_text = []
        collected_tool_calls: dict[int, dict] = {}  # index -> {id, name, arguments}
        usage_data = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        finish_reason = None

        try:
            for chunk in stream_response:
                if not chunk.choices:
                    # Usage-only chunk (some providers send this at the end)
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage_data["input_tokens"] = getattr(chunk.usage, "prompt_tokens", 0) or 0
                        usage_data["output_tokens"] = getattr(chunk.usage, "completion_tokens", 0) or 0
                    continue

                delta = chunk.choices[0].delta
                chunk_finish = chunk.choices[0].finish_reason

                if chunk_finish:
                    finish_reason = chunk_finish

                # Text content
                if delta and delta.content:
                    collected_text.append(delta.content)
                    yield delta.content

                # Tool calls (streamed incrementally)
                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index if tc_delta.index is not None else 0
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": tc_delta.id or f"toolu_{uuid.uuid4().hex[:24]}",
                                "name": "",
                                "arguments": "",
                            }
                        entry = collected_tool_calls[idx]
                        if tc_delta.id:
                            entry["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                entry["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                entry["arguments"] += tc_delta.function.arguments

                # Usage from chunk (if provided)
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_data["input_tokens"] = getattr(chunk.usage, "prompt_tokens", 0) or 0
                    usage_data["output_tokens"] = getattr(chunk.usage, "completion_tokens", 0) or 0
        except Exception as exc:
            raise LLMError(_friendly_byok_error(exc, provider)) from exc

        # Build the final NormalizedResponse
        content: list[dict] = []
        full_text = "".join(collected_text)
        if full_text:
            content.append({"type": "text", "text": full_text})

        has_tool_use = False
        for idx in sorted(collected_tool_calls):
            tc = collected_tool_calls[idx]
            has_tool_use = True
            args = tc["arguments"]
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {"raw": args}
            content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": args,
            })

        if has_tool_use or finish_reason == "tool_calls":
            stop_reason = "tool_use"
        else:
            stop_reason = "end_turn"

        self._final_response = NormalizedResponse(
            stop_reason=stop_reason,
            content=content,
            usage=usage_data,
        )


def make_stream(
    instance_id: int,
    messages: list[dict],
    system: list[dict],
    tools: list[dict],
    max_tokens: int = 4096,
) -> StreamContext:
    """Create a StreamContext for streaming LLM responses.

    Returns a :class:`StreamContext` whose ``text_stream()`` yields text
    chunks and ``get_final_response()`` returns the full normalised
    response after streaming completes.
    """
    return StreamContext(instance_id, messages, system, tools, max_tokens)


# ---------------------------------------------------------------------------
# Key validation
# ---------------------------------------------------------------------------

def validate_key(
    provider: str,
    api_key: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Test an API key with a minimal 1-token completion.

    Returns ``{"valid": True}`` on success or
    ``{"valid": False, "error": "message"}`` on failure.
    """
    if not api_key or not api_key.strip():
        return {"valid": False, "error": "API key is empty"}

    # Pick a default model for the provider if none specified
    if not model:
        defaults = {
            "anthropic": "claude-haiku-4-5-20251001",
            "openai": "gpt-5.4-nano",
            "google": "gemini-2.5-flash",
            "deepseek": "deepseek-chat",
        }
        model = defaults.get(provider)
        if not model:
            return {"valid": False, "error": f"Unknown provider: {provider}"}

    if provider == "anthropic":
        return _validate_anthropic_key(api_key, model)
    else:
        return _validate_litellm_key(provider, api_key, model)


def _validate_anthropic_key(api_key: str, model: str) -> dict[str, Any]:
    """Validate an Anthropic API key directly."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return {"valid": True}
    except anthropic.AuthenticationError:
        return {"valid": False, "error": "Invalid API key"}
    except anthropic.PermissionDeniedError:
        return {"valid": False, "error": "API key does not have permission for this model"}
    except anthropic.RateLimitError:
        # Key is valid, just rate-limited
        return {"valid": True}
    except Exception as exc:
        return {"valid": False, "error": f"Validation failed: {str(exc)}"}


def _validate_litellm_key(
    provider: str, api_key: str, model: str
) -> dict[str, Any]:
    """Validate a BYOK key via LiteLLM."""
    model_id = _litellm_model_id(provider, model)
    try:
        litellm.completion(
            model=model_id,
            messages=[{"role": "user", "content": "hi"}],
            api_key=api_key,
            max_tokens=1,
        )
        return {"valid": True}
    except Exception as exc:
        error_msg = str(exc).lower()
        if "auth" in error_msg or "api key" in error_msg or "unauthorized" in error_msg:
            return {"valid": False, "error": "Invalid API key"}
        if "permission" in error_msg or "access" in error_msg:
            return {"valid": False, "error": "API key does not have permission for this model"}
        if "rate" in error_msg and "limit" in error_msg:
            # Key is valid, just rate-limited
            return {"valid": True}
        if "not found" in error_msg or "does not exist" in error_msg:
            return {"valid": False, "error": f"Model '{model}' not found for provider '{provider}'"}
        return {"valid": False, "error": f"Validation failed: {str(exc)}"}


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """User-friendly LLM error for BYOK calls."""
    pass


def _friendly_byok_error(exc: Exception, provider: str) -> str:
    """Convert a raw provider exception into a user-friendly message."""
    msg = str(exc).lower()
    if "auth" in msg or "api key" in msg or "unauthorized" in msg or "401" in msg:
        return (
            f"Your {provider.title()} API key appears to be invalid or expired. "
            "Please update it in Settings > LLM Configuration."
        )
    if "rate" in msg and "limit" in msg:
        return (
            f"Rate limit reached on your {provider.title()} API key. "
            "Please wait a moment and try again."
        )
    if "quota" in msg or "billing" in msg or "insufficient" in msg:
        return (
            f"Your {provider.title()} account has insufficient quota or billing issues. "
            "Please check your account at the provider's dashboard."
        )
    if "not found" in msg or "does not exist" in msg or "404" in msg:
        return (
            f"The configured model was not found on {provider.title()}. "
            "Please check your model selection in Settings > LLM Configuration."
        )
    if "context" in msg and ("length" in msg or "window" in msg or "too long" in msg):
        return (
            "The conversation is too long for this model's context window. "
            "Try starting a new conversation or using a model with a larger context."
        )
    # Generic fallback
    return f"LLM call to {provider.title()} failed: {str(exc)}"
