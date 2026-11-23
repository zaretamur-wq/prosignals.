"""Research-only USD pip-value conversion for USD-denominated accounts.

Not a broker contract specification or permission to trade. A caller must supply
verified contract units, pip size, and contemporaneous quote-to-USD conversion.
"""
import math


def usd_pip_value_per_lot(contract_units, pip_size, quote_to_usd):
    """USD per pip per lot; quote_to_usd = USD for one quote-currency unit.

    EURUSD/GBPUSD/AUDUSD quote currency is USD (conversion 1).
    USDJPY quote currency is JPY (conversion approximately 1/USDJPY).
    XAUUSD contract units must be verified with the broker, not assumed.
    """
    vals = (contract_units, pip_size, quote_to_usd)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool)
           or not math.isfinite(v) or v <= 0 for v in vals):
        raise ValueError("Positive finite contract units, pip size and conversion required")
    return float(contract_units) * float(pip_size) * float(quote_to_usd)


def quote_to_usd_for_usdjpy(usd_jpy_rate):
    if not isinstance(usd_jpy_rate, (int, float)) or isinstance(usd_jpy_rate, bool) or not math.isfinite(usd_jpy_rate) or usd_jpy_rate <= 0:
        raise ValueError("Positive finite USDJPY conversion rate required")
    return 1.0 / usd_jpy_rate
