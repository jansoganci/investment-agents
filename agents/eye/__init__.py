"""Agent 1 — Eye (roadmap section 3, "Agent 1 rules"): reads the new posts of Emtia Defteri and Dragonomi, three passes a day.

    sites.py          the two sites: where the body, the paywall block and the audio player are in the page (from the
                      2026-10-11 probe; the cookie check on the Mac confirms them for a logged-in page)
    http.py           one polite request; stops on a block; never sends the cookie to another host
    extract.py        a saved page → title, date, tags, plain body text, "is it gated?"
    session_check.py  `python -m agents.eye.session_check emtia|dragonomi` — does my stored login give the full text?
"""
