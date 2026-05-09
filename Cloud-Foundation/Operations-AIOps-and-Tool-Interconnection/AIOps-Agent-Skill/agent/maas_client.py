"""MaaS GLM 5.1 client factory for the AIOps Agent.

Reuses css-log-assistant/app/maas_client.py pattern:
OpenAI-compatible client pointed at Huawei Cloud MaaS endpoint.
"""

from typing import Optional

from openai import OpenAI

from ops_agent_config import OpsAgentConfig


def create_maas_client(config: OpsAgentConfig) -> OpenAI:
    """Create an OpenAI-compatible client for Huawei Cloud MaaS.

    Reuses the css-log-assistant MaaS client pattern.
    """
    return OpenAI(
        api_key=config.maas_api_key,
        base_url=config.maas_api_base,
    )


def call_maas(client: OpenAI, system_prompt: str, user_prompt: str,
              model: Optional[str] = None, temperature: float = 0.1,
              max_tokens: int = 4096) -> str:
    """Call MaaS LLM with system and user prompts.

    Returns the assistant's text response.
    """
    response = client.chat.completions.create(
        model=model or "glm-5.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def call_maas_with_thinking(client: OpenAI, system_prompt: str, user_prompt: str,
                             model: Optional[str] = None,
                             thinking_budget: int = 8192,
                             max_tokens: int = 4096) -> dict:
    """Call MaaS LLM with thinking/reasoning support.

    Returns {"thinking": str, "text": str}.
    """
    response = client.chat.completions.create(
        model=model or "glm-5.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
        extra_body={
            "thinking": {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            },
        },
    )

    thinking = ""
    text = ""
    for block in response.choices[0].message.content:
        if block.type == "thinking":
            thinking = block.thinking
        elif block.type == "text":
            text = block.text

    return {"thinking": thinking, "text": text}
