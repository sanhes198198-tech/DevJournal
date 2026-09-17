"""
Split sidebar block from app/window.py into app/window_sidebar.py.

Extracts the sidebar-building code from setup_ui
and replaces it with a call to build_sidebar(self).
"""

import os
import sys


WINDOW_PATH = os.path.join("app", "window.py")
SIDEBAR_PATH = os.path.join("app", "window_sidebar.py")


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


def find_sidebar_block(text):

    # find "# SIDEBAR" marker
    marker = "# SIDEBAR"

    marker_idx = text.find(marker)

    if marker_idx < 0:
        raise RuntimeError(
            "Cannot find '# SIDEBAR' marker in window.py"
        )

    # find "# ===..." line start before marker
    line_start = text.rfind(
        "# =================================================",
        0,
        marker_idx,
    )

    if line_start < 0:
        raise RuntimeError(
            "Cannot find opening separator line before SIDEBAR"
        )

    # find beginning of that line
    start = text.rfind("\n", 0, line_start) + 1

    # find closing marker: sidebar_layout.addStretch()
    end_marker = "sidebar_layout.addStretch()"

    end_pos = text.find(end_marker, marker_idx)

    if end_pos < 0:
        raise RuntimeError(
            "Cannot find sidebar_layout.addStretch()"
        )

    end = end_pos + len(end_marker)

    return start, end


def main():

    if not os.path.exists(WINDOW_PATH):
        print("ERROR: window.py not found at", WINDOW_PATH)
        sys.exit(1)

    text = read_text_with_bom(WINDOW_PATH)

    start, end = find_sidebar_block(text)

    block = text[start:end]

    print("Found SIDEBAR block, size:", len(block), "bytes")

    # split into lines, preserving line endings is not needed here
    # because we will rebuild the file anyway.

    block_lines = block.splitlines()

    body_lines = []

    for line in block_lines:

        # remove 8 leading spaces (two indents -> one indent)
        if line.startswith("        "):
            body_lines.append(line[8:])
        else:
            body_lines.append(line)

    body = "\r\n".join(body_lines)

    sidebar_content = (
        '"""Sidebar builder for DevJournal."""\r\n'
        "\r\n"
        "from PySide6.QtWidgets import (\r\n"
        "    QFrame,\r\n"
        "    QVBoxLayout,\r\n"
        "    QLabel,\r\n"
        "    QPushButton,\r\n"
        ")\r\n"
        "\r\n"
        "\r\n"
        "def build_sidebar(window):\r\n"
        "\r\n"
        + "\r\n".join(
            ("    " + l) if l else ""
            for l in body_lines
        )
        + "\r\n"
        "\r\n"
        "    return window.sidebar\r\n"
    )

    write_text_with_bom(SIDEBAR_PATH, sidebar_content)

    print("Written:", SIDEBAR_PATH)
    print("Size:", len(sidebar_content), "bytes")

    replacement = (
        "        self.sidebar = build_sidebar(self)"
    )

    new_text = text[:start] + replacement + text[end:]

    import_line = "from .window_sidebar import build_sidebar"

    anchor = "from .window_styles import QSS"

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