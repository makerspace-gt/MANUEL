"""Turns the HTML of the case study into the small subset of HTML that Etherpad keeps, see
docs/adr/0071-etherpad-voruebergehend-fuer-anmerkungen-des-teams.adoc.

Headings become bold lines, tables one line per row with | between the cells, images their alt text.
Render the HTML with the image of the CI first, then convert:
    podman run --rm --security-opt label=disable -v "$PWD:/documents:ro" -v "$OUT:/out" \
        docker.io/asciidoctor/docker-asciidoctor:1.108 asciidoctor -r asciidoctor-bibtex -o /out/manuel.html case-study/manuel.adoc
    python3 -I case-study/etherpad_html.py $OUT/manuel.html $OUT/pad.html
"""
import html
import re
import sys
from html.parser import HTMLParser

BLOCK = {"p", "div", "dt", "dd", "pre", "tr", "caption", "blockquote", "figcaption"}
HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}
SKIP = {"script", "style", "svg", "head", "title", "nav"}


class Pad(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.line, self.skip, self.lists, self.cells = [], [], 0, [], None
        self.in_content = False

    def flush(self, bold=False):
        text = re.sub(r"\s+", " ", "".join(self.line)).strip()
        self.line = []
        if not text:
            return
        if self.lists:
            depth = len(self.lists)
            self.out.append(("li", depth, self.lists[-1], text))
        else:
            self.out.append(("b" if bold else "p", 0, None, text))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "img":
            alt = a.get("alt") or ""
            self.line.append(f" [Bild: {alt}] ")
        elif tag in HEAD:
            self.flush()
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists.append(tag)
        elif tag == "li":
            self.flush()
        elif tag == "tr":
            self.flush()
            self.cells = []
        elif tag in ("td", "th") and self.cells is not None:
            self.cells.append([])
        elif tag == "br":
            self.flush()
        elif tag in BLOCK:
            if self.cells is None:
                self.flush()

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in HEAD:
            self.flush(bold=True)
        elif tag in ("ul", "ol"):
            self.flush()
            if self.lists:
                self.lists.pop()
        elif tag == "li":
            self.flush()
        elif tag == "tr" and self.cells is not None:
            row = " | ".join(re.sub(r"\s+", " ", "".join(c)).strip() for c in self.cells)
            self.cells = None
            self.line = [row]
            self.flush()
        elif tag in BLOCK and self.cells is None:
            self.flush()

    def handle_data(self, data):
        if self.skip:
            return
        if self.cells is not None and self.cells:
            self.cells[-1].append(data)
        else:
            self.line.append(data)


def render(items):
    parts, open_lists = [], []
    for kind, depth, ltype, text in items:
        text = html.escape(text, quote=False)
        if kind == "li":
            while len(open_lists) > depth:
                parts.append(f"</{open_lists.pop()}>")
            while len(open_lists) < depth:
                open_lists.append(ltype)
                parts.append(f"<{ltype}>")
            parts.append(f"<li>{text}</li>")
            continue
        while open_lists:
            parts.append(f"</{open_lists.pop()}>")
        if kind == "b":
            parts.append(f"<p><br></p><p><b>{text}</b></p>")
        else:
            parts.append(f"<p>{text}</p>")
    while open_lists:
        parts.append(f"</{open_lists.pop()}>")
    return "<html><body>" + "".join(parts) + "</body></html>"


source = open(sys.argv[1], encoding="utf-8").read()
body = source.split("<body", 1)[-1].split(">", 1)[-1]
body = re.sub(r'<div id="toc".*?</ul>\s*</div>', "", body, count=1, flags=re.S)
parser = Pad()
parser.feed(body)
parser.flush()
note = ("Anmerkungen zur Fallstudie MANUEL. Bitte schreibt Anmerkungen direkt in den Text, am besten mit eurem Namen in "
        "der Leiste oben rechts. Bitte keine Namen, Adressen oder andere Angaben zu Gästen eintragen. Jede Anmerkung "
        "wird geprüft, bevor sie in die Fallstudie kommt.")
items = [("b", 0, None, note), ("p", 0, None, "Link zur Fallstudie https://makerspace-gt.github.io/MANUEL/")] + parser.out
open(sys.argv[2], "w", encoding="utf-8").write(render(items))
print(len(items), "Zeilen,", sum(len(t) for *_, t in items), "Zeichen")
