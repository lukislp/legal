#!/usr/bin/env python3
"""Checks every HTML page of the site before it can be published.

Fails when a page
- has no lang attribute (de or en), no title or no skip link,
- has no language switch pointing at its counterpart page in the other language,
- misses the footer links (imprint in the page language, change history),
- links to an internal page or file that does not exist,
- loads anything from another host (script, stylesheet, image, frame, media, font),
- still contains an open-point marker (data-todo, TODO, OFFEN:, OPEN:).

Standard library only. Usage: python3 scripts/check.py [site root]
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

IMPRINT = {
    "de": "https://lktec.org/impressum",
    "en": "https://lktec.org/en/imprint",
}
HISTORY = "https://github.com/lukislp/legal/commits/main"
SKIP_DIRS = {".git", ".github", "scripts", "node_modules"}
# Attributes that make the browser fetch something on its own.
RESOURCE_ATTRS = {
    "script": ("src",),
    "img": ("src", "srcset"),
    "iframe": ("src",),
    "frame": ("src",),
    "embed": ("src",),
    "object": ("data",),
    "audio": ("src",),
    "video": ("src", "poster"),
    "source": ("src", "srcset"),
    "track": ("src",),
    "input": ("src",),
}
TODO_PATTERN = re.compile(r"data-todo|\bTODO\b|\bOFFEN:|\bOPEN:")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.IGNORECASE)


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: str | None = None
        self.title = ""
        self._in_title = False
        self.hrefs: list[str] = []
        self.resources: list[str] = []
        self.ids: set[str] = set()
        self.has_skip = False
        self.switch_links: list[str] = []
        self._in_switch = 0
        self._in_footer = 0
        self.footer_links: list[str] = []
        self.css_urls: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "title":
            self._in_title = True
        if tag == "style":
            self._in_style = True
        if a.get("style"):
            self.css_urls += re.findall(r"url\(([^)]*)\)", a["style"])
        if tag == "ul" and "lang-switch" in a.get("class", "").split():
            self._in_switch += 1
        elif tag == "ul" and self._in_switch:
            self._in_switch += 1
        if tag == "footer":
            self._in_footer += 1
        if tag == "a":
            href = a.get("href", "")
            self.hrefs.append(href)
            if "skip" in a.get("class", "").split() and href.startswith("#"):
                self.has_skip = True
            if self._in_switch:
                self.switch_links.append(href)
            if self._in_footer:
                self.footer_links.append(href)
        if tag == "link":
            rel = a.get("rel", "").lower().split()
            href = a.get("href", "")
            if "alternate" in rel or "canonical" in rel:
                self.hrefs.append(href)
            else:
                self.resources.append(href)
        for attr in RESOURCE_ATTRS.get(tag, ()):
            if a.get(attr):
                self.resources.append(a[attr])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "style":
            self._in_style = False
        if tag == "ul" and self._in_switch:
            self._in_switch -= 1
        if tag == "footer" and self._in_footer:
            self._in_footer -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_style:
            self.css_urls += re.findall(r"url\(([^)]*)\)", data)


def url_path(page: Path, root: Path) -> str:
    rel = page.relative_to(root).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def resolve(href: str, page: Path, root: Path) -> Path | None:
    target = href.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return page
    base = root if target.startswith("/") else page.parent
    path = (base / target.lstrip("/")).resolve()
    if target.endswith("/") or path.is_dir():
        path = path / "index.html"
    return path


def counterpart(path: str, lang: str) -> str:
    if lang == "de":
        return "/en" + path if path != "/" else "/en/"
    return path[len("/en"):] or "/"


def check(root: Path) -> list[str]:
    errors: list[str] = []
    pages = sorted(
        p for p in root.rglob("*.html") if not SKIP_DIRS.intersection(p.relative_to(root).parts)
    )
    if not pages:
        return ["no HTML pages found"]
    known = {url_path(p, root) for p in pages}
    for page in pages:
        rel = page.relative_to(root).as_posix()
        text = page.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if TODO_PATTERN.search(line):
                errors.append(f"{rel}:{n}: open point marker left in the page")
        p = Page()
        p.feed(text)
        lang = p.lang or ""
        if lang not in IMPRINT:
            errors.append(f"{rel}: <html lang> must be 'de' or 'en', found {lang!r}")
            continue
        expected_lang = "en" if rel.startswith("en/") else "de"
        if lang != expected_lang:
            errors.append(f"{rel}: lang {lang!r} does not match its folder ({expected_lang})")
        if not p.title.strip():
            errors.append(f"{rel}: empty or missing <title>")
        if not p.has_skip:
            errors.append(f"{rel}: no skip link (<a class=\"skip\" href=\"#...\">)")
        path = url_path(page, root)
        other = counterpart(path, lang)
        if other not in known:
            errors.append(f"{rel}: counterpart page {other} does not exist")
        if other not in p.switch_links:
            errors.append(f"{rel}: language switch does not link to {other}")
        if IMPRINT[lang] not in p.footer_links:
            errors.append(f"{rel}: footer misses the imprint link {IMPRINT[lang]}")
        if HISTORY not in p.footer_links:
            errors.append(f"{rel}: footer misses the change history link {HISTORY}")
        for res in p.resources + p.css_urls:
            res = res.strip("'\" ")
            if res.startswith("data:"):
                continue
            if EXTERNAL.match(res) or re.match(r"^[a-z][a-z0-9+.-]*:", res, re.IGNORECASE):
                errors.append(f"{rel}: external resource {res!r}")
            else:
                target = resolve(res, page, root)
                if target is None or not target.exists():
                    errors.append(f"{rel}: resource {res!r} not found")
        for href in p.hrefs:
            if not href:
                errors.append(f"{rel}: empty href")
                continue
            if EXTERNAL.match(href) or href.startswith(("mailto:", "tel:")):
                continue
            if href.startswith("#"):
                if href[1:] not in p.ids:
                    errors.append(f"{rel}: anchor {href} has no target")
                continue
            target = resolve(href, page, root)
            if target is None or not target.exists():
                errors.append(f"{rel}: broken internal link {href!r}")
                continue
            frag = href.split("#", 1)[1] if "#" in href else ""
            if frag and target.suffix == ".html":
                other_page = Page()
                other_page.feed(target.read_text(encoding="utf-8"))
                if frag not in other_page.ids:
                    errors.append(f"{rel}: anchor {href} has no target")
    css = root / "assets" / "style.css"
    if css.exists():
        for res in re.findall(r"url\(([^)]*)\)|@import\s+([^;]+)", css.read_text(encoding="utf-8")):
            value = next(v for v in res if v).strip("'\" ")
            if EXTERNAL.match(value):
                errors.append(f"assets/style.css: external resource {value!r}")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = check(root)
    for e in errors:
        print(f"error: {e}")
    if errors:
        print(f"{len(errors)} problem(s) found")
        return 1
    print("site check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
