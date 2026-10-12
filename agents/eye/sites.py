"""The two sites. Both are Ghost. Selectors come from the probe of 2026-10-11 (Hermes on the Air, no login), so they describe
the page of a visitor who is not logged in; the cookie check (session_check.py) shows what a logged-in page looks like."""

from __future__ import annotations

from dataclasses import dataclass

# (tag, class tokens that must all be present)
Selector = tuple[str, frozenset]


def sel(tag: str, *classes: str) -> Selector:
    return (tag, frozenset(classes))


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    base: str                       # no trailing slash
    cookie_env: str                 # the .env variable that holds my login cookie header
    body: tuple                     # candidate selectors for the post body, tried in order, the first that matches wins
    gate: tuple                     # a block that exists only when the page is cut for a visitor
    strip: tuple                    # blocks inside the body that are not the post text
    glossary_slugs: tuple           # a post with one of these tags is a glossary post: not taken

    @property
    def posts_sitemap(self) -> str:
        return f"{self.base}/sitemap-posts.xml"


SITES = {
    "emtia": Site(
        key="emtia",
        name="Emtia Defteri",
        base="https://www.emtiadefteri.com",
        cookie_env="EMTIA_COOKIE",
        body=(sel("article", "ghost-content"),),
        gate=(sel("aside", "gh-post-upgrade-cta"), sel("div", "paywall-content-wrap")),
        strip=(sel("aside", "gh-post-upgrade-cta"), sel("div", "paywall-content-wrap")),
        glossary_slugs=("emtia-sozlugu",),
    ),
    "dragonomi": Site(
        key="dragonomi",
        name="Dragonomi",
        base="https://www.dragonomi.com",
        cookie_env="DRAGONOMI_COOKIE",
        body=(sel("div", "content", "post-sneak-peek"), sel("div", "content")),
        gate=(sel("div", "content-cta", "paid"),),
        strip=(sel("div", "kg-audio-player"), sel("div", "content-cta")),
        glossary_slugs=("yatirim-sozlugu",),
    ),
}


def describe(selector: Selector) -> str:
    tag, classes = selector
    return tag + "".join("." + c for c in sorted(classes))
