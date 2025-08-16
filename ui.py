# PySide6 UI to interact with the app
from datetime import date
import inspect
from types import GenericAlias
from typing import Callable, Any
import typing
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QDateEdit,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
)
from PySide6.QtGui import (
    QIcon,
    QFont,
    QGuiApplication,
    QAction,
    QIntValidator,
    QDoubleValidator,
)
from PySide6.QtCore import Qt, QSize, QPoint, QDate
import pydantic

# notifications are handled via UIState methods (app_state or prints)
import auth
import database
from fakes import generate_person, generate_property
import query
from schema import Booking, Payment, Person, Property, DbModel, Service


class TableView(QWidget):
    def __init__(
        self,
        model_class: type[DbModel],
        get_paginated_data: Callable[[int, int, dict[str, str]], list[DbModel]],
        get_count: Callable[[], int],
        hidden_fields: list[str] = [],
        context_menu_actions: dict[str, Callable[[str, DbModel], None]] = {},
    ):
        super().__init__()
        self.get_paginated_data = get_paginated_data
        self.get_count = get_count
        self.hidden_fields = hidden_fields
        self.context_menu_actions = context_menu_actions

        self.current_page = 0

        self.fields = model_class.model_fields

        self.box = QVBoxLayout(self)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search...")
        self.box.addWidget(self.search)

        self.search.textChanged.connect(self.on_search_text_changed)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.fields))
        self.table.setHorizontalHeaderLabels(
            [field for field in self.fields if field not in self.hidden_fields]
        )
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # allow the table columns to stretch to fill available width
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # allow this whole TableView widget to expand inside parent layouts
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # give the table vertical stretch so it fills the TableView
        self.box.addWidget(self.table, 1)

        if self.context_menu_actions:
            self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.bar = QHBoxLayout()

        self.left_button = QPushButton("<", self)
        self.left_button.clicked.connect(self.go_to_previous_page)
        self.bar.addWidget(self.left_button)

        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.refresh)
        self.bar.addWidget(self.refresh_button)

        self.page_label = QLabel("Page 1", self)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bar.addWidget(self.page_label)

        self.right_button = QPushButton(">", self)
        self.right_button.clicked.connect(self.go_to_next_page)
        self.bar.addWidget(self.right_button)

        self.box.addLayout(self.bar)

        self.update()

    def refresh(self):
        self.current_page = 0
        self.update()

    def on_search_text_changed(self, text: str):
        self.current_page = 0
        self.update()

    def update(self):
        data = self.get_paginated_data(self.current_page * 10, 10, self.search.text())
        self.update_table(data)

    def update_table(self, data: list[DbModel]):
        self.cached_count = self.get_count()
        self.table.setRowCount(len(data))

        for row_index, item in enumerate(data):
            for col_index, field in enumerate(self.fields):
                if field in self.hidden_fields:
                    continue
                value = getattr(item, field, "")
                if isinstance(value, date):
                    value = value.strftime("%Y-%m-%d")
                wig = QTableWidgetItem(str(value))
                wig.setData(Qt.ItemDataRole.UserRole, item)
                self.table.setItem(row_index, col_index, wig)
        self.page_label.setText(
            f"Page {self.current_page + 1}/{self.cached_count // 10 + 1}"
        )

    def go_to_previous_page(self):
        self.cached_count = self.get_count()
        if self.current_page > 0:
            self.current_page -= 1
            self.update()

    def go_to_next_page(self):
        self.cached_count = self.get_count()
        if self.current_page < (self.cached_count // 10):
            self.current_page += 1
            self.update()

    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item and self.context_menu_actions:
            menu = QMenu(self)
            item_column = item.column()
            field_keys = list(self.fields.keys())
            item_data = item.data(Qt.ItemDataRole.UserRole)
            for action_name, actionfn in self.context_menu_actions.items():
                action = QAction(action_name, menu)
                action.setData(actionfn)
                # bind actionfn, field name and item data into defaults so each
                # lambda captures the current values (avoid late-binding bug)
                field_name = field_keys[item_column]
                action.triggered.connect(
                    lambda _, fn=actionfn, fname=field_name, data=item_data: fn(
                        fname, data
                    )
                )
                menu.addAction(action)
            menu.exec(self.table.viewport().mapToGlobal(pos))


searchers = {
    Person: lambda offset, limit, q: query.search_persons(q, offset, limit).value,
    Property: lambda offset, limit, q: query.search_properties(q, offset, limit).value,
    Booking: lambda offset, limit, q: query.search_bookings(q, offset, limit).value,
    Service: lambda offset, limit, q: query.search_services(q, offset, limit).value,
}


class SearchWithList(QDialog):
    def __init__(
        self,
        model: type[DbModel],
        on_done: Callable[[QDialog, bool, DbModel], None],
        search: Callable[[int, int, str], list[DbModel]] = None,
    ):
        super().__init__()

        self.setWindowTitle("Search")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search...")
        layout.addWidget(self.search_input)

        self.results_list = QListWidget(self)
        self.results_list.itemClicked.connect(self.handle_item_clicked)
        layout.addWidget(self.results_list)

        self.setLayout(layout)

        self.model = model
        self.on_done = on_done
        self.search = search

        self.search_input.textChanged.connect(
            lambda text: self.update_results(self.search_input.text())
        )

        self.update_results("")

    def update_results(self, search_text: str):
        if self.search:
            results = self.search(0, 10, search_text)
            self.results_list.clear()
            for result in results:
                item = QListWidgetItem(str(result), self.results_list)
                item.setData(Qt.ItemDataRole.UserRole, result)
                self.results_list.addItem(item)

    def handle_item_clicked(self, item: QListWidgetItem):
        self.on_done(self, True, item.data(Qt.ItemDataRole.UserRole))

    def closeEvent(self, _):
        self.on_done(self, False, None)


# a button but when you click it it opens a window to choose using a search
class LineEditWithSearch(QPushButton):
    def __init__(
        self,
        model: type[DbModel],
        search: Callable[[str], list[DbModel]],
        setter: Callable[[DbModel], None] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.model = model
        self.setText("Search...")
        self.search = search
        self.pressed.connect(self.open_search)
        self.setter = setter
        self.valid = False

    def open_search(self):
        self.search_list = SearchWithList(
            model=self.model, on_done=self.handle_search_result, search=self.search
        )
        self.search_list.show()

    def handle_search_result(self, dialog: QDialog, accepted: bool, data: DbModel):
        if accepted:
            self.setText(str(data))
            self.valid = True
            if self.setter:
                self.setter(data)
        dialog.close()


validators = {
    int: QIntValidator,
    float: QDoubleValidator,
    str: None,
}


def convert_safe(callable, value) -> tuple[bool, Any]:
    try:
        return True, callable(value)
    except ValueError as e:
        return False, None
    except Exception as e:
        print(f"Error occurred in {callable.__name__}: {e}")
        return False, None


def default_init(T):
    if T == int:
        return 0
    elif T == float:
        return 0.0
    elif T == str:
        return ""
    elif T == list:
        return []
    elif T == dict:
        return {}
    elif T == bool:
        return False
    return None


def create_datatype_widget(
    T: type,
    initial_value: Any,
    setter,
    parent=None,
    is_top: False = False,
    search_fields: dict[str, type[DbModel]] = None,
) -> QWidget:
    widget = None
    if issubclass(T, DbModel) and not is_top:
        widget = LineEditWithSearch(
            model=T,
            search=searchers[T],
            setter=lambda data, setter=setter: setter(data.id),
        )
        if parent:
            widget.setParent(parent)
    elif T == int:
        widget = QSpinBox(parent=parent)
        widget.setValue(initial_value)
        widget.valueChanged.connect(lambda value, setter=setter: setter(value))
    elif T == float:
        widget = QDoubleSpinBox(parent=parent)
        widget.setValue(initial_value)
        widget.valueChanged.connect(lambda value, setter=setter: setter(value))
    elif T == str or T == pydantic.EmailStr:
        widget = QLineEdit(initial_value, parent=parent)
        widget.textChanged.connect(lambda text, setter=setter: setter(text))
    elif T == list:
        widget = QFormLayout(parent=parent)
        for item in initial_value:

            def inner_setter(item, new_value, setter):
                initial_value.__setitem__(item, new_value)
                setter(initial_value)

            wid = create_datatype_widget(
                str,
                item,
                lambda new_value, item=item, setter=setter: inner_setter(
                    item, new_value, setter
                ),
            )
            widget.addRow(wid)
    elif T == date:
        widget = QDateEdit(parent=parent)
        widget.setDate(QDate.fromString(str(initial_value), "yyyy-MM-dd"))
        widget.dateChanged.connect(lambda date, setter=setter: setter(date.toPython()))
    elif T == bool:
        widget = QCheckBox(parent=parent)
        widget.setChecked(initial_value)
        widget.stateChanged.connect(
            lambda state, setter=setter: setter(state == Qt.CheckState.Checked)
        )
    elif T == dict or typing.get_origin(T) == dict:
        widget = QFormLayout(parent=parent)
        for key, value in initial_value.items():

            def inner_setter(initial_value, key, new_value, setter):
                initial_value.__setitem__(key, new_value)
                setter(initial_value)

            widget.addRow(
                QLabel(key),
                create_datatype_widget(
                    value.__class__,
                    value,
                    lambda new_value, key=key, initial_value=initial_value, setter=setter: inner_setter(
                        initial_value, key, new_value, setter
                    ),
                ),
            )

    elif issubclass(T, pydantic.BaseModel):
        widget = QFormLayout(parent=parent)
        for field, info in T.model_fields.items():
            if field not in initial_value:
                continue

            def inner_setter(initial_value, new_value, setter, field):
                initial_value[field] = new_value
                setter(initial_value)

            wig = create_datatype_widget(
                (
                    search_fields[field]
                    if search_fields and field in search_fields
                    else info.annotation
                ),
                initial_value[field],
                setter=lambda new_value, initial_value=initial_value, setter=setter, field=field: inner_setter(
                    initial_value, new_value, setter, field
                ),
            )
            widget.addRow(QLabel(field), wig)
    else:
        print(f"Unsupported type for widget creation: {T}")
    return widget


def create_modal_floating(
    name: str,
    model: DbModel,
    on_done: Callable[[QDialog, bool, DbModel], None],
    ignore_fields: list[str] = None,
    rename_fields: dict[str, str] = None,
    search_fields: dict[str, type[DbModel]] = None,
):
    # creates a window and puts all the fields in
    dialog = QDialog(modal=False)
    dialog.setWindowTitle(name)
    dialog.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    dialog.setWindowFlag(Qt.WindowType.Tool, True)

    fields = model.model_dump()
    new_fields = {
        field: value for field, value in fields.items() if field not in ignore_fields
    }

    reverse = dict()
    # rename fields
    if rename_fields:
        new_fields = {
            rename_fields.get(field, field): value
            for field, value in new_fields.items()
        }
        reverse = {value: key for key, value in rename_fields.items()}

    def setter(data: dict):
        for key, value in data.items():
            key = reverse.get(key, key)
            model.__setattr__(key, value)

    layout: QFormLayout = create_datatype_widget(
        model.__class__,
        new_fields,
        setter=setter,
        parent=dialog,
        is_top=True,
        search_fields=search_fields,
    )

    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
    button_box.accepted.connect(lambda: on_done(dialog, True, model))
    button_box.rejected.connect(lambda: on_done(dialog, False, None))
    layout.addRow(button_box)

    dialog.show()

    return dialog


class PersonManagement(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.add_new_person_button = QPushButton("Add New Person", self)
        self.add_new_person_button.clicked.connect(self.add_new_person)
        layout.addWidget(self.add_new_person_button)

        self.add_fake_person_button = QPushButton("Add Fake Person", self)
        self.add_fake_person_button.clicked.connect(self.add_fake_person)
        layout.addWidget(self.add_fake_person_button)

        self.people_table = TableView(
            model_class=Person,
            get_paginated_data=searchers[Person],
            get_count=lambda: query.get_person_count().one(),
            context_menu_actions={
                "delete": lambda field, person: self.delete_person(person),
                "copy": lambda field, person: self.copy_person(field, person),
                "change rank": lambda field, person: self.rank_person(person),
            },
        )
        layout.addWidget(self.people_table, 1)

        database.database_updated.connect(self.people_table.update)

        self.setLayout(layout)

    def delete_person(self, person: Person):
        if person.id == 1:
            print("Error: Cannot delete admin user.")
            return
        result = query.delete_person(person.id)
        if result.error:
            print(f"Error deleting person: {result.error}")
        else:
            self.people_table.refresh()

    def copy_person(self, field: str, person: Person):
        value = getattr(person, field, None)
        if value is not None:
            print(f"Copied {field} from {person} with value: {value}")
            QGuiApplication.clipboard().setText(str(value))

    def add_fake_person(self):
        person = generate_person()
        result = query.create_person(**person.model_dump(exclude=["id", "is_employee"]))
        if result.error:
            print(f"Error adding fake person: {result.error}")
        else:
            self.people_table.update()

    def rank_person(self, person: Person):
        if person.id == 1:
            print("Error: Cannot change rank of admin user.")
            return
        if person.is_employee:
            result = query.set_person_customer(person.id)
        else:
            result = query.set_person_employee(person.id)
        if result.error:
            print(f"Error changing rank of person: {result.error}")
        else:
            self.people_table.update()

    def add_new_person(self):
        new_person = Person(
            id=-1,
            email="email@example.com",
            first_name="First",
            last_name="Last",
            phone_number="123-456-7890",
            is_employee=False,
            hashed_password="password123",
            username="username",
        )
        modal = create_modal_floating(
            "Add New Person",
            new_person,
            self.handle_add_new_person,
            ignore_fields=["id", "is_employee"],
            rename_fields={"hashed_password": "password"},
        )

    def handle_add_new_person(self, dialog: QDialog, success: bool, person: Person):
        if success:
            try:
                person.hashed_password = auth.hash_plaintext(person.hashed_password)
                person = Person(**person.model_dump())
                query.create_person(**person.model_dump(exclude=["id", "is_employee"]))
            except Exception as e:
                print(f"Error adding new person: {e}")
        dialog.close()


class PropertyManagement(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.add_new_property_button = QPushButton("Add New Property", self)
        self.add_new_property_button.clicked.connect(self.add_new_property)
        layout.addWidget(self.add_new_property_button)

        self.add_fake_property_button = QPushButton("Add Fake Property", self)
        self.add_fake_property_button.clicked.connect(self.add_fake_property)
        layout.addWidget(self.add_fake_property_button)

        self.property_table = TableView(
            model_class=Property,
            get_paginated_data=searchers[Property],
            get_count=lambda: query.get_property_count().one(),
            context_menu_actions={
                "delete": lambda field, property: self.delete_property(property),
                "copy": lambda field, property: self.copy_property(field, property),
            },
        )
        layout.addWidget(self.property_table, 1)

        database.database_updated.connect(self.property_table.update)

        self.setLayout(layout)

    def delete_property(self, property: Property):
        result = query.delete_property(property.id)
        if result.error:
            print(f"Error deleting property: {result.error}")
        else:
            self.property_table.refresh()

    def copy_property(self, field: str, property: Property):
        value = getattr(property, field, None)
        if value is not None:
            print(f"Copied {field} from {property} with value: {value}")
            QGuiApplication.clipboard().setText(str(value))

    def add_fake_property(self):
        property = generate_property()
        result = query.create_property(**property.model_dump(exclude=["id"]))
        if result.error:
            print(f"Error adding fake property: {result.error}")
        else:
            self.property_table.update()

    def add_new_property(self):
        new_property = Property(
            id=-1,
            city="Perth",
            post_code="6000",
            state="WA",
            street_address="123 Fake St",
        )
        modal = create_modal_floating(
            "Add New Property",
            new_property,
            self.handle_add_new_property,
            ignore_fields=["id"],
        )

    def handle_add_new_property(
        self, dialog: QDialog, success: bool, property: Property
    ):
        if success:
            try:
                property = Property(**property.model_dump())
                query.create_property(**property.model_dump(exclude=["id"]))
            except Exception as e:
                print(f"Error adding new property: {e}")
        dialog.close()


class BookingManagement(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.add_new_booking_button = QPushButton("Add New Booking", self)
        self.add_new_booking_button.clicked.connect(self.add_new_booking)
        layout.addWidget(self.add_new_booking_button)

        self.booking_table = TableView(
            model_class=Booking,
            get_paginated_data=searchers[Booking],
            get_count=lambda: query.get_booking_count().one(),
            context_menu_actions={
                "delete": lambda field, booking: self.delete_booking(booking),
                "copy": lambda field, booking: self.copy_booking(field, booking),
            },
        )
        layout.addWidget(self.booking_table, 1)

        database.database_updated.connect(self.booking_table.update)

        self.setLayout(layout)

    def delete_booking(self, booking: Booking):
        result = query.delete_booking(booking.id)
        if result.error:
            print(f"Error deleting booking: {result.error}")
        else:
            self.booking_table.refresh()

    def copy_booking(self, field: str, booking: Booking):
        value = getattr(booking, field, None)
        if value is not None:
            print(f"Copied {field} from {booking} with value: {value}")
            QGuiApplication.clipboard().setText(str(value))

    def add_new_booking(self):
        new_booking = Booking(
            id=-1,
            person_id=-1,  # Placeholder, will be set in modal
            property_id=-1,  # Placeholder, will be set in modal
            booking_date=date.today(),
            services={},
        )
        modal = create_modal_floating(
            "Add New Booking",
            new_booking,
            self.handle_add_new_booking,
            ignore_fields=["id", "completed", "services"],
            search_fields={
                "property_id": Property,
                "person_id": Person,
            },
        )

    def handle_add_new_booking(self, dialog: QDialog, success: bool, booking: Booking):
        if success:
            try:
                if booking.booking_date < date.today():
                    raise ValueError("Booking date must be today or in the future")
                if booking.person_id < 0:
                    raise ValueError("Person ID must be valid")
                if booking.property_id < 0:
                    raise ValueError("Property ID must be valid")
                booking = Booking(**booking.model_dump(exclude=["services"]))
                query.create_booking(**booking.model_dump(exclude=["id"]))
            except Exception as e:
                print(f"Error adding new booking: {e}")
        dialog.close()


# left hand side with bookings, then a panel on right hand with info and then the list of services
class BookingServiceManagement(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)

        # Use a QListWidget populated from the searcher so the
        # left panel is visible inside the layout.
        self.booking_list = SearchWithList(
            Booking, on_done=self.on_booking_selected, search=searchers[Booking]
        )
        layout.addWidget(self.booking_list)

        self.details_panel = QWidget(self)
        layout.addWidget(self.details_panel)

        # make 1/3 2/3 split
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)

        self.setLayout(layout)

        # populate the list initially
        try:
            self.update_booking_list()
        except Exception:
            # safe no-op if searcher/query not ready
            pass

        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_panel.setLayout(self.details_layout)

        self.info_area = QWidget(self.details_panel)
        self.details_layout.addWidget(self.info_area)

        self.services_area = QWidget(self.details_panel)
        self.details_layout.addWidget(self.services_area)

    def on_booking_selected(self, dialog: QDialog, success: bool, booking: Booking):
        # Update the right panel with booking details and services
        print(f"Selected booking: {booking}")
        pass

    def _handle_booking_list_click(self, item: QListWidgetItem):
        # forward QListWidget selection to the same handler signature
        booking = item.data(Qt.ItemDataRole.UserRole)
        self.on_booking_selected(None, True, booking)

    def update_booking_list(self, search: str = ""):
        results = searchers[Booking](0, 20, search)
        self.booking_list.clear()
        for r in results:
            it = QListWidgetItem(str(r), self.booking_list)
            it.setData(Qt.ItemDataRole.UserRole, r)
            self.booking_list.addItem(it)


class LoginFrame(QWidget):
    def __init__(
        self, on_login: Callable[[str, str], Any], close_event: Callable[[], Any]
    ):
        super().__init__()
        self.on_login = on_login
        self.close_event = close_event

        layout = QVBoxLayout(self)

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        layout.addWidget(self.password_input)

        login_button = QPushButton("Login", self)
        login_button.clicked.connect(self.handle_login)
        layout.addWidget(login_button)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if username and password:
            self.on_login(username, password)

    def closeEvent(self, event):
        self.close_event()


TAB_MANAGE_PERSONS = 0
TAB_MANAGE_PROPERTIES = 1
TAB_MANAGE_BOOKINGS = 2
TAB_MANAGE_BOOKING_SERVICES = 3


class Ui(QMainWindow):
    def __init__(self):
        super().__init__()

        self.logged_in_as_user: Person | None = None

        self.setWindowTitle("Lawn Database")
        self.resize(1000, 800)

        central = QWidget(self)
        self.setCentralWidget(central)
        central_layout = QVBoxLayout(central)
        # keep children aligned to the top; avoid centering so expanding widgets
        # (like the top bar) can fill the full width
        central_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.bigfont = QFont("Arial", 24)
        self.italicfont = QFont("Arial", 18, italic=True)
        self.normalfont = QFont("Arial", 12)

        # make a top bar with the logged in user name on the left and logout on the right
        top_bar = QWidget(central)
        # make top bar 50px high and expand x
        top_bar.setFixedHeight(50)
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_bar_layout = QHBoxLayout(top_bar)

        self.logged_in_user_label = QLabel("Logged in as: ", top_bar)
        self.logged_in_user_label.setFont(self.italicfont)
        self.logged_in_user_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.logged_in_user_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        top_bar_layout.addWidget(self.logged_in_user_label)

        logout_button = QPushButton("Logout", top_bar)
        logout_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        logout_button.setFont(self.normalfont)
        logout_button.clicked.connect(self.handle_logout)
        top_bar_layout.addWidget(logout_button)

        # add the top bar to the main layout so it can expand to the window width
        central_layout.addWidget(top_bar)

        self.login_frame = LoginFrame(self.handle_login, self.closeAll)
        self.login_frame.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        central_layout.addWidget(self.tab_widget)

        # employee only
        self.manage_persons_widget = PersonManagement()
        self.tab_widget.addTab(self.manage_persons_widget, "Manage Persons")
        self.manage_properties_widget = PropertyManagement()
        self.tab_widget.addTab(self.manage_properties_widget, "Manage Properties")
        self.manage_bookings_widget = BookingManagement()
        self.tab_widget.addTab(self.manage_bookings_widget, "Manage Bookings")
        self.manage_booking_services_widget = BookingServiceManagement()
        self.tab_widget.addTab(
            self.manage_booking_services_widget, "Manage Booking Services"
        )

        self.handle_state()

    def handle_state(self):
        logged_in = self.logged_in_as_user is not None
        self.login_frame.setVisible(not logged_in)

        if not logged_in:
            self.centralWidget().setVisible(False)
            return

        self.centralWidget().setVisible(True)
        self.logged_in_user_label.setText(f"Logged in as: {self.logged_in_as_user}")

        is_employee = (
            self.logged_in_as_user.is_employee if self.logged_in_as_user else False
        )
        self.tab_widget.setTabVisible(TAB_MANAGE_PERSONS, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_PROPERTIES, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_BOOKINGS, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_BOOKING_SERVICES, is_employee)

    def handle_login(self, username: str, password: str):
        result = query.login_person(username, auth.hash_plaintext(password))

        if result.error:
            print(f"Login failed: {result.error}")
        else:
            self.logged_in_as_user = result.one()
            print(f"Login successful: {self.logged_in_as_user}")

        self.handle_state()

    def handle_logout(self):
        self.logged_in_as_user = None
        self.handle_state()

    def closeAll(self):
        self.close()
        self.login_frame.close()
