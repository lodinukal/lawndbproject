from ui import Ui
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication([])

    ui = Ui()
    ui.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
