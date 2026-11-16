"""Resolve extensionless Mintlify page links against the MkDocs source tree."""

from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class DocsPageLinks(Treeprocessor):
    def run(self, root):
        for link in root.iter("a"):
            href = link.get("href", "")
            if not href.startswith("/") or href.startswith("//"):
                continue

            url = urlsplit(href)
            if url.path != "/" and not PurePosixPath(url.path).suffix:
                link.set("href", urlunsplit(url._replace(path=url.path.rstrip("/") + ".md")))


class DocsPageLinksExtension(Extension):
    def extendMarkdown(self, md):
        # MkDocs converts source paths into generated URLs at priority 0.
        md.treeprocessors.register(DocsPageLinks(md), "docs_page_links", 2)


def on_config(config):
    config.markdown_extensions.append(DocsPageLinksExtension())
