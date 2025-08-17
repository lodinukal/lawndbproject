import sys
from ui import Ui
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication([])

    # if provided with args, then user is 1st then password
    if len(sys.argv) > 2:
        user = sys.argv[1]
        password = sys.argv[2]

    ui = Ui(
        user=user if "user" in locals() else None,
        password=password if "password" in locals() else None,
    )
    ui.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
