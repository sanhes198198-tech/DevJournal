import os
import sys
import faulthandler
import traceback
from datetime import datetime

# ============================================================
# DEBUG PRINT FILTER
# ============================================================
# Фильтруем debug-принты: если сообщение начинается с [TAG],
# где TAG — известный debug-тег, то не выводим в консоль.
#
# Для отладки закомментируй строку:
#     _builtins_module.print = _filtered_print
#
# Тогда все print снова будут работать.

import builtins as _builtins_module

_original_print = _builtins_module.print

_DEBUG_TAGS = (
    "[SER]",
    "[COLLECT]",
    "[REST]",
    "[FIND_FRAME]",
    "[MEMBERSHIP]",
    "[FRAME]",
    "[PERSIST]",
    "[SAVE]",
    "[ADD_FRAME]",
    "[VIDEO]",
    "[FILE]",
    "[IMAGE]",
    "[COLOR]",
)


def _filtered_print(*args, **kwargs):
    if args:
        try:
            first = str(args[0])
        except Exception:
            first = ""

        for tag in _DEBUG_TAGS:
            if first.startswith(tag):
                return

    _original_print(*args, **kwargs)


_builtins_module.print = _filtered_print
# ============================================================
# ============================================================
# Qt РґРѕР»Р¶РµРЅ РІРёРґРµС‚СЊ UTF-8 РґРѕ СЃРѕР·РґР°РЅРёСЏ QApplication
# ============================================================

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ Р·Р°РґР°С‘Рј UTF-8 РґР»СЏ Qt Рё Python
os.environ["LANG"] = "ru_RU.UTF-8"
os.environ["LC_ALL"] = "ru_RU.UTF-8"
os.environ["PYTHONIOENCODING"] = "utf-8"

# ============================================================
# UTF-8 РґР»СЏ stdout/stderr
# ============================================================

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================
# Р”РёР°РіРЅРѕСЃС‚РёС‡РµСЃРєРёРµ С„Р°Р№Р»С‹
# ============================================================

DEBUG_LOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "devjournal_debug.log",
)

CRASH_LOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "devjournal_crash.log",
)


def write_debug(message):
    """
    Р—Р°РїРёСЃС‹РІР°РµС‚ РґРёР°РіРЅРѕСЃС‚РёС‡РµСЃРєРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ РІ debug-log.
    """

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]

    line = f"[{timestamp}] {message}"

    try:
        with open(
            DEBUG_LOG,
            "a",
            encoding="utf-8",
        ) as file:
            file.write(line + "\n")
            file.flush()
    except Exception:
        pass

    try:
        print(line)
    except Exception:
        pass


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ РѕР±СЂР°Р±РѕС‚С‡РёРє РЅРµРѕР±СЂР°Р±РѕС‚Р°РЅРЅС‹С… Python-РёСЃРєР»СЋС‡РµРЅРёР№.
    """

    if issubclass(exc_type, KeyboardInterrupt):

        sys.__excepthook__(
            exc_type,
            exc_value,
            exc_traceback,
        )

        return

    try:
        text = "".join(
            traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback,
            )
        )

        write_debug(
            "UNHANDLED PYTHON EXCEPTION:\n"
            + text
        )

        with open(
            CRASH_LOG,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                "\n"
                + "=" * 80
                + "\n"
                + text
            )

            file.flush()

    except Exception:
        pass

    sys.__excepthook__(
        exc_type,
        exc_value,
        exc_traceback,
    )


sys.excepthook = handle_exception


# ============================================================
# faulthandler
# ============================================================

try:

    crash_file = open(
        CRASH_LOG,
        "a",
        encoding="utf-8",
    )

    faulthandler.enable(
        crash_file
    )

    write_debug(
        "faulthandler enabled"
    )

except Exception as error:

    crash_file = None

    write_debug(
        f"РќРµ СѓРґР°Р»РѕСЃСЊ РІРєР»СЋС‡РёС‚СЊ faulthandler: {error}"
    )


# ============================================================
# РРјРїРѕСЂС‚ Qt
# ============================================================

from PySide6.QtCore import (
    qInstallMessageHandler,
    QtMsgType,
)

from PySide6.QtWidgets import QApplication


# ============================================================
# РџРµСЂРµС…РІР°С‚ СЃРѕРѕР±С‰РµРЅРёР№ Qt
# ============================================================

def qt_message_handler(
    message_type,
    context,
    message,
):
    """
    РџРµСЂРµС…РІР°С‚С‹РІР°РµС‚ СЃРѕРѕР±С‰РµРЅРёСЏ Qt:
    debug / info / warning / critical / fatal.
    """

    type_names = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "CRITICAL",
        QtMsgType.QtFatalMsg: "FATAL",
    }

    type_name = type_names.get(
        message_type,
        str(message_type),
    )

    location = ""

    try:

        if context is not None:

            file_name = getattr(
                context,
                "file",
                None,
            )

            line_number = getattr(
                context,
                "line",
                None,
            )

            function_name = getattr(
                context,
                "function",
                None,
            )

            parts = []

            if file_name:
                parts.append(
                    str(file_name)
                )

            if line_number:
                parts.append(
                    f"line {line_number}"
                )

            if function_name:
                parts.append(
                    str(function_name)
                )

            if parts:
                location = (
                    " | "
                    + ", ".join(parts)
                )

    except Exception:
        pass

    write_debug(
        f"QT {type_name}: "
        f"{message}"
        f"{location}"
    )


qInstallMessageHandler(
    qt_message_handler
)


# ============================================================
# РРјРїРѕСЂС‚ РїСЂРѕРµРєС‚Р°
# ============================================================

from app.config import APP_NAME
from app.window import DevJournal


# ============================================================
# MAIN
# ============================================================

def main():

    write_debug(
        "=" * 80
    )

    write_debug(
        "Р—Р°РїСѓСЃРє DevJournal"
    )

    write_debug(
        f"Python: {sys.version}"
    )

    write_debug(
        f"Executable: {sys.executable}"
    )

    write_debug(
        f"Working directory: {os.getcwd()}"
    )

    try:

        app = QApplication(
            sys.argv
        )

        write_debug(
            "QApplication СЃРѕР·РґР°РЅ"
        )

        app.setApplicationName(
            APP_NAME
        )

        write_debug(
            f"Application name: {APP_NAME}"
        )

        window = DevJournal()

        write_debug(
            "DevJournal СЃРѕР·РґР°РЅ"
        )

        window.show()

        write_debug(
            "Р“Р»Р°РІРЅРѕРµ РѕРєРЅРѕ РїРѕРєР°Р·Р°РЅРѕ"
        )

        write_debug(
            "Р’С…РѕРґ РІ app.exec()"
        )

        exit_code = app.exec()

        write_debug(
            f"app.exec() Р·Р°РІРµСЂС€С‘РЅ, РєРѕРґ: {exit_code}"
        )

        sys.exit(
            exit_code
        )

    except Exception:

        write_debug(
            "РСЃРєР»СЋС‡РµРЅРёРµ РІРЅСѓС‚СЂРё main():"
        )

        write_debug(
            traceback.format_exc()
        )

        raise


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()