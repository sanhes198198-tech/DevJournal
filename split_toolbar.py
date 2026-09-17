"""
Split toolbar block from app/window.py into app/window_toolbar.py.

Extracts the toolbar-building code from setup_ui
and replaces it with a call to build_toolbar(self).
"""

import os
import sys


WINDOW_PATH = os.path.join("app", "window.py")
TOOLBAR_PATH = os.path.join("app", "window_toolbar.py")


def read_text_with_bom(path):

    with open(path, "rb") as f:
        data = f.read()

    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]

    return data.decode("utf-8")


def write_text_with_bom(path, text):

    with open(path, "wb") as f:
        f.write(b"\xef\xbb\xbf")
        f.write(text.encode("utf-8"))


def find_toolbar_block(text):

    # Find "# TOOLBAR" marker
    marker = "# TOOLBAR"

    marker_idx = text.find(marker)

    if marker_idx < 0:
        raise RuntimeError("Cannot find '# TOOLBAR' marker")

    # Find opening separator line before marker
    line_start = text.rfind(
        "# =================================================",
        0,
        marker_idx,
    )

    if line_start < 0:
        raise RuntimeError("Cannot find opening separator")

    start = text.rfind("\n", 0, line_start) + 1

    # Find closing line: right_layout.addWidget(
    #                      toolbar
    #                  )
    end_marker = "right_layout.addWidget("

    end_search = text.find(end_marker, marker_idx)

    if end_search < 0:
        raise RuntimeError("Cannot find right_layout.addWidget(")

    # find end of this call (closing parenthesis + newline)
    closing = text.find(")", end_search)

    if closing < 0:
        raise RuntimeError("Cannot find closing parenthesis")

    end = closing + 1

    return start, end


def main():

    if not os.path.exists(WINDOW_PATH):
        print("ERROR: window.py not found at", WINDOW_PATH)
        sys.exit(1)

    text = read_text_with_bom(WINDOW_PATH)

    start, end = find_toolbar_block(text)

    block = text[start:end]

    print("Found TOOLBAR block, size:", len(block), "bytes")

    block_lines = block.splitlines()

    body_lines = []

    for line in block_lines:

        if line.startswith("        "):
            line = line[8:]

        body_lines.append(line)

    # replace self. -> window. in every line
    fixed_lines = []

    for line in body_lines:

        line = line.replace("self.", "window.")

        fixed_lines.append(line)

    body = "\r\n".join(fixed_lines)

    toolbar_content = (
        '"""Toolbar builder for DevJournal."""\r\n'
        "\r\n"
        "from PySide6.QtCore import Qt\r\n"
        "from PySide6.QtWidgets import (\r\n"
        "    QFrame,\r\n"
        "    QHBoxLayout,\r\n"
        "    QToolButton,\r\n"
        "    QMenu,\r\n"
        "    QLabel,\r\n"
        ")\r\n"
        "\r\n"
        "\r\n"
        "def build_toolbar(window):\r\n"
        "\r\n"
        + "\r\n".join("    " + l if l else "" for l in fixed_lines)
        + "\r\n"
        "\r\n"
        "    return toolbar\r\n"
    )

    write_text_with_bom(TOOLBAR_PATH, toolbar_content)

    print("Written:", TOOLBAR_PATH)
    print("Size:", len(toolbar_content), "bytes")

    replacement = (
        "        right_layout.addWidget(\r\n"
        "            build_toolbar(self)\r\n"
        "        )"
    )

    new_text = text[:start] + replacement + text[end:]

    import_line = "from .window_toolbar import build_toolbar"

    anchor = "from .window_sidebar import build_sidebar"

    if anchor not in new_text:
        print("DEBUG: first 500 chars:")
        print(repr(new_text[:500]))
        raise RuntimeError("Cannot find import anchor")

    if import_line not in new_text:
        new_text = new_text.replace(
            anchor,
            anchor + "\r\n" + import_line,
            1,
        )

    write_text_with_bom(WINDOW_PATH, new_text)

    print("Updated:", WINDOW_PATH)
    print("Done.")


if __name__ == "__main__":
    main()