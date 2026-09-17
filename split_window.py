"""
Split app/window.py.

Extracts the Qt Style Sheet block into app/window_styles.py,
and replaces it in app/window.py with an import and a call.
"""

import os
import sys


WINDOW_PATH = os.path.join(
    "app",
    "window.py",
)

STYLES_PATH = os.path.join(
    "app",
    "window_styles.py",
)


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


def find_qss_block(text):

    start_marker = 'self.setStyleSheet("""'

    idx = text.find(start_marker)

    if idx < 0:
        raise RuntimeError(
            "Cannot find setStyleSheet block in window.py"
        )

    end_marker = '""")'

    end_idx = text.find(end_marker, idx + len(start_marker))

    if end_idx < 0:
        raise RuntimeError(
            "Cannot find closing triple-quote in window.py"
        )

    return idx, end_idx + len(end_marker)


def main():

    if not os.path.exists(WINDOW_PATH):
        print("ERROR: window.py not found at", WINDOW_PATH)
        sys.exit(1)

    text = read_text_with_bom(WINDOW_PATH)

    start, end = find_qss_block(text)

    qss_full = text[start:end]

    qss_value = qss_full[len('self.setStyleSheet('):-1]

    styles_content = (
        '"""Qt Style Sheet for DevJournal."""\n'
        "\n"
        "QSS = " + qss_value + "\n"
    )

    write_text_with_bom(STYLES_PATH, styles_content)

    print("Written:", STYLES_PATH)
    print("Size:", len(styles_content), "bytes")

    replacement = "self.setStyleSheet(QSS)"

    new_text = text[:start] + replacement + text[end:]

    import_line = "from .window_styles import QSS"

    anchor = "from .config import APP_NAME, BOARDS_DIR"

    if anchor not in new_text:
        print("DEBUG: first 500 chars of new_text:")
        print(repr(new_text[:500]))
        raise RuntimeError(
            "Cannot find import anchor in window.py"
        )

    if import_line not in new_text:
        new_text = new_text.replace(
            anchor,
            anchor + "\n" + import_line,
            1,
        )

    write_text_with_bom(WINDOW_PATH, new_text)

    print("Updated:", WINDOW_PATH)
    print("Done.")


if __name__ == "__main__":
    main()