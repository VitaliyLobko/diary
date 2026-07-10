"""Structural checks on every rendered page.

The audit found `students_with_grades.html` shipping an unclosed `</main>` and
two unclosed `</div>`s, and `top_10_students.html` emitting one `id="modal-edit"`
per card. Neither breaks a status code, so only a check on the rendered markup
itself catches them — and catches them again if a future edit reintroduces one.
"""

from html.parser import HTMLParser

import pytest

from src.services import seed as seed_service

# Elements with no closing tag; a balance check must not push them.
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
# Containers whose imbalance silently corrupts the page layout.
TRACKED = {
    "div", "main", "section", "form", "table", "tbody", "thead", "tr", "ul", "li",
}


class Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.ids = []
        self.inline_handlers = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "id":
                self.ids.append(value)
            elif name.startswith("on"):
                self.inline_handlers.append(f"{tag}[{name}]")
        if tag in VOID:
            return
        if tag in TRACKED:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in TRACKED:
            return
        if not self.stack:
            self.errors.append(f"</{tag}> with nothing open")
        elif self.stack[-1] != tag:
            self.errors.append(f"</{tag}> closes <{self.stack[-1]}>")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()


@pytest.fixture(scope="module")
def seeded(session):
    seed_service.seed_database(session, teachers=3, students=5, faker_seed=7)
    return session


PAGES = [
    "/",
    "/students/",
    "/students/avg_grade",
    "/students/top_10_students",
    "/students/1",
    "/teachers/",
    "/teachers/1",
    "/groups/",
    "/groups/1",
    "/disciplines/",
    "/disciplines/1",
    "/grades/",
    "/grades/1",
]


@pytest.fixture(scope="module")
def rendered(client, seeded):
    pages = {}
    for path in PAGES:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
        pages[path] = resp.text
    return pages


@pytest.mark.parametrize("path", PAGES)
def test_container_tags_are_balanced(rendered, path):
    parser = Structure()
    parser.feed(rendered[path])
    assert not parser.errors, f"{path}: {parser.errors}"
    assert not parser.stack, f"{path}: never closed {parser.stack}"


@pytest.mark.parametrize("path", PAGES)
def test_element_ids_are_unique(rendered, path):
    parser = Structure()
    parser.feed(rendered[path])
    dupes = {i for i in parser.ids if parser.ids.count(i) > 1}
    assert not dupes, f"{path}: duplicate id(s) {sorted(dupes)}"


@pytest.mark.parametrize("path", PAGES)
def test_no_inline_event_handlers(rendered, path):
    # Inline onclick/onchange cannot run under a script-src CSP; navigation is
    # driven by data-href / data-backdrop-href / data-autosubmit instead.
    parser = Structure()
    parser.feed(rendered[path])
    assert not parser.inline_handlers, f"{path}: {parser.inline_handlers}"


LIST_PAGES = ["/students/", "/teachers/", "/groups/", "/disciplines/", "/grades/"]
DETAIL_PAGES = [
    "/students/1", "/teachers/1", "/groups/1", "/disciplines/1", "/grades/1",
]


@pytest.mark.parametrize("path", LIST_PAGES)
def test_list_rows_stay_navigable(rendered, path):
    # Dropping the inline onclick must not drop the navigation with it: rows
    # declare their target and are reachable by keyboard.
    html = rendered[path]
    assert 'data-href="' in html, f"{path}: rows lost their link target"
    assert 'tabindex="0"' in html, f"{path}: rows are not keyboard-focusable"
    assert 'role="link"' in html, f"{path}: rows are not announced as links"


@pytest.mark.parametrize("path", DETAIL_PAGES)
def test_detail_backdrop_stays_navigable(rendered, path):
    html = rendered[path]
    assert "data-backdrop-href=" in html, f"{path}: backdrop lost its target"
    assert "data-stop-click" in html, f"{path}: card clicks would hit the backdrop"


@pytest.mark.parametrize("path", ["/students/", "/grades/"])
def test_filter_selects_still_autosubmit(rendered, path):
    assert "data-autosubmit" in rendered[path], f"{path}: filter select lost its submit"


@pytest.mark.parametrize("path", LIST_PAGES)
def test_search_input_keeps_its_value(rendered, path):
    # grades.html used to omit value=, so the term vanished from the box after
    # searching, and its "Clear" button re-submitted the very same query.
    if "search_by" not in rendered[path]:
        pytest.skip(f"{path} has no search box")
    assert 'name="search_by"' in rendered[path]
    assert 'value="' in rendered[path]


@pytest.mark.parametrize("path", PAGES)
def test_no_leftover_junk(rendered, path):
    html = rendered[path]
    assert "Lorem ipsum" not in html, f"{path}: placeholder copy still shipped"
    assert "../static/" not in html, f"{path}: relative asset path"
    assert "Закр" not in html, f"{path}: untranslated aria-label"
    assert "`" not in html, f"{path}: stray backtick literal"
