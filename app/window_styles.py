"""Qt Style Sheet for DevJournal."""

QSS = """

        QMainWindow {
            background: #F7F7F5;
        }

        QWidget {
            font-family: "Roboto";
            color: #202124;
        }

        QFrame#sidebar {
            background: #FFFFFF;
            border-right: 1px solid #E7E7E3;
        }

        QLabel#appTitle {
            font-size: 18px;
            font-weight: 700;
            color: #171717;
        }

        QLabel#projectLabel {
            font-size: 11px;
            font-weight: 600;
            color: #999999;
        }

        QLabel#sectionLabel {
            font-size: 10px;
            font-weight: 700;
            color: #A0A09B;
        }

        QLabel#statusLabel {
            color: #8A8A85;
            font-size: 11px;
        }

        QPushButton {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 9px 12px;
            text-align: left;
            color: #343434;
            font-size: 13px;
        }

        QPushButton:hover {
            background: #F1F1EE;
        }

        QPushButton:pressed {
            background: #EAEAE6;
        }

        QPushButton#activeSection {
            background: #F0F3FF;
            color: #315EDB;
            font-weight: 600;
        }

        QFrame#toolbar {
            background: #FFFFFF;
            border-bottom: 1px solid #E7E7E3;
        }

        QToolButton {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 7px;
            padding: 6px 9px;
            color: #4A4A47;
            font-size: 12px;
        }

        QToolButton:hover {
            background: #F1F1EE;
            border-color: #E3E3DE;
        }

        QToolButton:pressed {
            background: #EAEAE6;
        }

        QToolButton#menuButton {
            font-weight: 600;
            padding-left: 10px;
            padding-right: 10px;
        }

        QLabel#zoomLabel {
            min-width: 52px;
            color: #666660;
            font-size: 12px;
        }

        QDialog {
            background: #FFFFFF;
        }

        QLabel#settingsTitle {
            font-size: 18px;
            font-weight: 700;
        }

        QComboBox,
        QSpinBox {
            background: #FAFAF8;
            border: 1px solid #DCDCD7;
            border-radius: 8px;
            padding: 8px;
        }

        QMenu {
            background: #FFFFFF;
            border: 1px solid #DCDCD7;
            padding: 5px;
        }

        QMenu::item {
            padding: 8px 24px 8px 12px;
            border-radius: 5px;
        }

        QMenu::item:selected {
            background: #F1F1EE;
        }

        """
