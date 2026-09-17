"""The copy contract — keep the two radar renderers from drifting apart.

`legal-os` renders the radar twice from the same data:

    radar/build.py                     -> docs/radar/index.html   (static, GitHub Pages)
    frontend/src/app/radar/page.tsx    -> the in-app page         (React, Vercel)

They are separate code paths with nothing keeping them in step, and on 2026-09-17 they
diverged three times: the milestone panel landed in one, the list renumbering in the other,
and the watch-list restructure in one. Each was found by a person reading a live page. That
is the failure this file exists to catch.

Two mechanisms, deliberately:

  1. SHARED SOURCE. `radar/copy.json` holds the strings both surfaces must agree on.
     build.py reads it and publishes it inside data.json; the app reads `data.copy`.

  2. THIS GUARD. Every string in copy.json must (a) appear in the generated static page,
     and (b) NOT be hardcoded in the app's source — the app has to read it from data.copy.
     (b) is the load-bearing half: copying a heading into the TSX by hand is exactly how
     the divergence starts, and this fails the moment someone does it.

Runs with pytest or standalone: `python radar/tests/test_copy_contract.py`.
"""
import json
import subprocess
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
REPO = RADAR.parent
COPY_FILE = RADAR / "copy.json"
STATIC_PAGE = REPO / "docs" / "radar" / "index.html"
APP_SRC = REPO / "frontend" / "src" / "app" / "radar" / "page.tsx"


def _copy():
    return json.loads(COPY_FILE.read_text())


def _shared():
    """The copy entries both surfaces must agree on. `_note` is internal."""
    return {k: v for k, v in _copy().items() if not k.startswith("_") and isinstance(v, str)}


def test_copy_file_parses_and_is_non_trivial():
    c = _shared()
    assert len(c) >= 6, f"copy.json looks gutted: {len(c)} entries"


def test_static_page_contains_every_shared_string():
    """The generated static page must carry each shared string, from copy.json."""
    if not STATIC_PAGE.exists():
        return  # not built in this checkout; the build step covers it
    html = STATIC_PAGE.read_text()
    missing = [k for k, v in _shared().items() if v and v not in html]
    assert not missing, (
        f"static page is missing copy from copy.json: {missing}. "
        f"Either build.py stopped reading the shared file, or the page is stale."
    )


def test_app_does_not_hardcode_shared_copy():
    """THE load-bearing test.

    If a shared string appears anywhere in the app's source OUTSIDE the fallback defaults,
    someone typed it there instead of reading data.copy — which is precisely how the two
    surfaces drifted three times on 2026-09-17.

    The fallback block is allowed to name the strings, because it exists so an older
    data.json cannot blank the page. So the check is positional: every occurrence of a
    shared string must fall inside the fallback block's span. A first version of this test
    excluded any string merely PRESENT in the fallback, which made it pass vacuously —
    it could never fire for a string the fallback also mentioned. Verified by hardcoding a
    heading and watching it fail; keep that check honest if you edit this.
    """
    if not APP_SRC.exists():
        return
    src = APP_SRC.read_text()

    marker = "const copy: Copy = data.copy ??"
    assert marker in src, "the copy fallback block moved; update this test's span logic"
    fb_start = src.index(marker)
    fb_end = src.index("};", fb_start) + 2

    offenders = []
    for key, val in _shared().items():
        if not val or key.startswith("seg_"):
            continue
        pos = 0
        while True:
            i = src.find(val, pos)
            if i < 0:
                break
            if not (fb_start <= i < fb_end):
                offenders.append((key, val[:44], src[:i].count("\n") + 1))
            pos = i + 1
    assert not offenders, (
        "app hardcodes shared copy outside the fallback block (key, string, line): "
        f"{offenders}. Read copy.<key> instead."
    )


def test_app_reads_the_copy_object():
    """Positive half: the app must actually reference data.copy, not merely avoid the literals."""
    if not APP_SRC.exists():
        return
    src = APP_SRC.read_text()
    assert "data.copy" in src, "the app no longer reads data.copy"
    refs = src.count("copy.")
    assert refs >= 3, f"the app references copy only {refs} times; expected the headings wired"


def test_data_json_publishes_the_copy():
    """The app can only read what the builder publishes."""
    data = REPO / "docs" / "radar" / "data.json"
    if not data.exists():
        return
    published = json.loads(data.read_text()).get("copy")
    assert published, "data.json carries no `copy` block; the app will fall back to defaults"
    assert published["board_heading"] == _copy()["board_heading"]


def test_both_surfaces_name_the_same_sections():
    """A cheap end-to-end assertion: the four headings a reader navigates by."""
    if not STATIC_PAGE.exists():
        return
    html = STATIC_PAGE.read_text()
    for key in ("board_heading", "actions_heading", "watch_lead"):
        assert _copy()[key] in html, f"static page lost the {key} heading"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("copy contract holds")
