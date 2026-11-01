"""A call's cost from what it used, at the configured prices (US dollars).

Langfuse prices LLM calls only, so speech-to-text, voice and phone minutes are priced here from
the runtime's usage counts; LLM tokens use the agent model's price, and a model with no price
is reported as unpriced rather than free.
"""

from studio_api.config import Settings

TOKENS_PER_MILLION = 1_000_000
CHARACTERS_PER_THOUSAND = 1000
SECONDS_PER_MINUTE = 60
COST_DECIMALS = 5
# Added by the post-call analysis job: its own LLM call, priced at the analysis model.
ANALYSIS_COST_PART = "analysis"


def llm_cost(
    input_tokens: float, cached_tokens: float, output_tokens: float, prices: dict | None
) -> float:
    if not prices:
        return 0.0
    return (
        (input_tokens - cached_tokens) * prices["input"]
        + cached_tokens * prices.get("cached_input", prices["input"])
        + output_tokens * prices["output"]
    ) / TOKENS_PER_MILLION


def call_cost(
    usage: dict[str, float], llm_model: str, phone_seconds: float, settings: Settings
) -> dict[str, float | bool]:
    prices = settings.llm_prices.get(llm_model)
    llm = llm_cost(
        usage.get("llm_input_tokens", 0),
        usage.get("llm_cached_input_tokens", 0),
        usage.get("llm_output_tokens", 0),
        prices,
    )
    stt = usage.get("stt_seconds", 0) / SECONDS_PER_MINUTE * settings.stt_price_per_minute
    tts = (
        usage.get("tts_characters", 0)
        / CHARACTERS_PER_THOUSAND
        * settings.tts_price_per_1k_characters
    )
    phone = phone_seconds / SECONDS_PER_MINUTE * settings.phone_price_per_minute
    parts = {"llm": llm, "stt": stt, "tts": tts, "phone": phone}
    cost: dict[str, float | bool] = {
        name: round(value, COST_DECIMALS) for name, value in parts.items()
    }
    cost["total"] = round(sum(parts.values()), COST_DECIMALS)
    cost["llm_unpriced"] = prices is None and usage.get("llm_input_tokens", 0) > 0
    return cost
