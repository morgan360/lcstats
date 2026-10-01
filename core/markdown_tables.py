"""Tag Markdown-rendered tables so the site's CSS can style them.

Tailwind's reset strips every table of borders and padding, so a bare <table>
from Markdown renders with its cells run together ("1015" for 10 and 15).
Hand-written tables elsewhere in the templates carry their own styles, and some
have no class either, so CSS cannot target "tables without a class" safely.
This extension gives Markdown's tables a class of their own, ``md-table``,
which ``static/src/input.css`` styles.
"""
from markdown import Extension
from markdown.treeprocessors import Treeprocessor

TABLE_CLASS = "md-table"


class _TableClassTreeprocessor(Treeprocessor):
    def run(self, root):
        for table in root.iter("table"):
            existing = table.get("class", "")
            if TABLE_CLASS not in existing.split():
                table.set("class", f"{existing} {TABLE_CLASS}".strip())


class TableClassExtension(Extension):
    def extendMarkdown(self, md):
        # Low priority, so it runs after the tables extension has built them.
        md.treeprocessors.register(_TableClassTreeprocessor(md), "md_table_class", 1)
