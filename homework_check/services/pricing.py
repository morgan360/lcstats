"""What a vision call costs, from the tokens it used.

Published list prices in US dollars per million tokens, as (input, cached
input, output), each with the date it takes effect so a price change applies
only to calls made after it. Output includes any thinking the model does.

Sources, checked 2026-09-15:
https://ai.google.dev/gemini-api/docs/pricing
https://developers.openai.com/api/docs/pricing
"""
import datetime as dt
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

PRICES = {
    # Introductory price until the end of 2026, then doubled.
    "gemini-3.8-flash": [
        (dt.date(2000, 1, 1), (0.75, 0.075, 3.75)),
        (dt.date(2027, 1, 1), (1.50, 0.15, 7.50)),
    ],
    "gpt-5.5": [(dt.date(2000, 1, 1), (5.00, 0.50, 30.00))],
}


def prices_for(model, on):
    """(input, cached, output) in force for ``model`` on date ``on``, or None."""
    current = None
    for start, prices in PRICES.get(model, []):
        if on >= start:
            current = prices
    return current


def cost_usd(model, prompt_tokens, cached_tokens, completion_tokens, on=None):
    """The call's cost in dollars; 0 for a model with no price, logged."""
    prices = prices_for(model, on or dt.date.today())
    if prices is None:
        logger.warning("No price for vision model %s; its spend is not counted", model)
        return Decimal("0")
    p_in, p_cached, p_out = prices
    cached = min(cached_tokens, prompt_tokens)
    dollars = ((prompt_tokens - cached) * p_in + cached * p_cached
               + completion_tokens * p_out) / 1_000_000
    return Decimal(str(round(dollars, 6)))
