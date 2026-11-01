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


def call_cost(
    usage: dict[str, float], llm_model: str, phone_seconds: float, settings: Settings
) -> dict[str, float | bool]:
    prices = settings.llm_prices.get(llm_model)
    cached = usage.get("llm_cached_input_tokens", 0)
    fresh_input = usage.get("llm_input_tokens", 0) - cached
    llm = 0.0
    if prices:
        llm = (
            fresh_input * prices["input"]
            + cached * prices.get("cached_input", prices["input"])
            + usage.get("llm_output_tokens", 0) * prices["output"]
        ) / TOKENS_PER_MILLION
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
