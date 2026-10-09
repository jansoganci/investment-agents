"""Agent 4 — Portfolio (roadmap section 3, "Agent 4 rules"): the only agent that looks at my money. Code only, no AI; all
figures in USD; it never says "sell".

    ledger.py      `holdings`: buys and sales from my commands, dividends and splits by code; positions and average cost
    marketdata.py  prices from `prices` in today's share basis; SPY's total-return index; gold per gram; USD/TRY
    value.py       value, weights, gain / loss, the SPY and gold shadows, the return (`xirr` after 12 months), total wealth
    watch.py       drop alert, valuation watch, new-money ranking with the 25% rule
    block.py       the portfolio block (Sunday summary and /portfolio)
    run.py         the weekly run and the on-demand block

    uv run python -m agents.portfolio            the weekly run
    uv run python -m agents.portfolio --show     the block with the latest closes
"""
