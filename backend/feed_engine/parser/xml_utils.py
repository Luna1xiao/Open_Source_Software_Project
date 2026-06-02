from __future__ import annotations

from collections.abc import Iterable
from xml.etree.ElementTree import Element


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def child(element: Element, *names: str) -> Element | None:
    wanted = set(names)
    for item in element:
        if local_name(item.tag) in wanted:
            return item
    return None


def children(element: Element, *names: str) -> list[Element]:
    wanted = set(names)
    return [item for item in element if local_name(item.tag) in wanted]


def descendants(element: Element, *names: str) -> Iterable[Element]:
    wanted = set(names)
    for item in element.iter():
        if item is not element and local_name(item.tag) in wanted:
            yield item


def text_of(element: Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def first_text(element: Element, *names: str) -> str:
    return text_of(child(element, *names))


def html_text(element: Element | None) -> str:
    if element is None:
        return ""
    if element.text:
        return element.text.strip()
    return "".join(element.itertext()).strip()

