"""Agent 2 — Research (roadmap section 3, "Agent 2 rules" and "Score rules"; built in phase 5).

Every Sunday it takes the Counter's top US stocks that have no card, reads what the posts say, searches the news, scores five
criteria (code adds the points; the AI only sets labels, with a quote) and opens the card.

    health.py    quick_health: five checks from SEC's figures (code)
    tailwind.py  sector_tailwind: the sector fund and the linked commodity against their 40-week averages (code)
    score.py     the points of each criterion and the total
    reading.py   the posts: tone with a quote (strong model)
    news.py      news flow and the commodity link (strong model + web search), the serious-negative check with the auditor
    run.py       one stock end to end, the weekly run, the card, the report
"""
