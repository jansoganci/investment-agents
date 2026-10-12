"""A saved page → what the Eye keeps: title, date, the post's own tags, the plain body text, and whether the page is cut.

Standard library only. The page is turned into a small tree; the site's selectors (sites.py) find the body, the gate and the
blocks that are not post text. Tags come from the page's meta (`article:tag`) — the 44 / 24 `/tag/` links in the page are the
site menu, not the post's tags (probe, 2026-10-11)."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser

from agents.eye.sites import Selector, Site, describe

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "section", "article",
         "figure", "figcaption", "tr", "table", "pre", "hr", "aside", "header", "footer", "main"}
NOT_TEXT = {"script", "style", "noscript", "template", "svg", "head"}


class Node:
    def __init__(self, tag: str, attrs: dict, parent: "Node | None" = None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list = []

    @property
    def classes(self) -> set:
        return set((self.attrs.get("class") or "").split())

    def matches(self, selector: Selector) -> bool:
        tag, classes = selector
        return self.tag == tag and classes <= self.classes

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.current)
        self.current.children.append(node)

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def parse(html: str) -> Node:
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return builder.root


def find_all(root: Node, selector: Selector) -> list:
    return [node for node in root.walk() if node.matches(selector)]


def _collect(node: Node, strip: tuple, out: list) -> None:
    for child in node.children:
        if isinstance(child, str):
            out.append(child)
            continue
        if child.tag in NOT_TEXT or any(child.matches(s) for s in strip):
            continue
        block = child.tag in BLOCK
        if block:
            out.append("\n")
        _collect(child, strip, out)
        if block:
            out.append("\n")


def text_of(node: Node, strip: tuple = ()) -> str:
    """Plain text: block elements become line breaks, runs of spaces collapse, empty lines go."""
    parts: list = []
    _collect(node, strip, parts)
    lines = []
    for line in "".join(parts).replace("\xa0", " ").split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def norm_tag(name: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", name)).strip()


_TR = str.maketrans({"ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ş": "s", "Ş": "s", "ı": "i", "İ": "i", "ö": "o", "Ö": "o",
                     "ç": "c", "Ç": "c"})


def slugify(name: str) -> str:
    """How Ghost spells a tag in its address: Turkish letters to plain ones, lower case, other signs to a hyphen."""
    plain = unicodedata.normalize("NFKD", name.translate(_TR)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


@dataclass
class Post:
    title: str | None = None
    published_at: str | None = None       # as the page writes it (ISO, with its offset)
    tags: list = field(default_factory=list)
    text: str = ""
    gated: bool = False                   # the page carries a "log in / subscribe" block
    body_selector: str | None = None      # which candidate selector found the body
    body_matches: int = 0                 # how many elements matched it (more than 1 → look at it)

    @property
    def text_missing(self) -> bool:
        """The text is not the whole post: the page is cut, or the body was not found."""
        return self.gated or self.body_selector is None


def _meta(root: Node, key: str) -> list:
    return [norm_tag(n.attrs["content"]) for n in root.walk()
            if n.tag == "meta" and n.attrs.get("property") == key and n.attrs.get("content")]


def _jsonld_keywords(root: Node) -> list:
    found: list = []
    for node in root.walk():
        if node.tag != "script" or "ld+json" not in node.attrs.get("type", ""):
            continue
        try:
            data = json.loads("".join(c for c in node.children if isinstance(c, str)))
        except ValueError:
            continue
        for item in (data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []):
            words = item.get("keywords") if isinstance(item, dict) else None
            if isinstance(words, str):
                words = words.split(",")
            if isinstance(words, list):
                found += [norm_tag(str(w)) for w in words if str(w).strip()]
    return found


def parse_post(html: str, site: Site) -> Post:
    root = parse(html)
    post = Post()
    titles = _meta(root, "og:title")
    if titles:
        post.title = titles[0]
    else:
        for node in root.walk():
            if node.tag == "title":
                post.title = text_of(node) or None
                break
    dates = _meta(root, "article:published_time")
    post.published_at = dates[0] if dates else None
    tags = _meta(root, "article:tag") or _jsonld_keywords(root)
    post.tags = list(dict.fromkeys(tags))
    post.gated = any(find_all(root, g) for g in site.gate)
    for candidate in site.body:
        matches = find_all(root, candidate)
        if matches:
            post.body_selector = describe(candidate)
            post.body_matches = len(matches)
            post.text = text_of(matches[0], site.strip)
            break
    return post


def is_glossary(post: Post, site: Site) -> bool:
    return any(slugify(tag) in site.glossary_slugs for tag in post.tags)
