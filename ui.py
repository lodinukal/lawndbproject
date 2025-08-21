# PySide6 UI to interact with the app
from datetime import date, timedelta
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
    QFrame,
    QCalendarWidget,
    QSplitter,
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

import fpdf

from edifice import *

import pydantic

# notifications are handled via UIState methods (app_state or prints)
import auth
import database
from fakes import generate_person, generate_property
import query
from schema import (
    Booking,
    BookingService,
    Payment,
    Person,
    Property,
    DbModel,
    Roster,
    Service,
)


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
                field_name = field_keys[item_column]

                def triggered(
                    _, actionfn=actionfn, field_name=field_name, item_data=item_data
                ):
                    actionfn(field_name, item_data)

                action.triggered.connect(triggered)
                menu.addAction(action)
            menu.exec(self.table.viewport().mapToGlobal(pos))


searchers = {
    Person: lambda offset, limit, q: query.search_persons(q, offset, limit).value,
    Property: lambda offset, limit, q: query.search_properties(q, offset, limit).value,
    Booking: lambda offset, limit, q: query.search_bookings(q, offset, limit).value,
    Service: lambda offset, limit, q: query.search_services(q, offset, limit).value,
    BookingService: lambda booking, offset, limit, q: query.search_services_by_booking(
        booking, q, offset, limit
    ).value,
}


class SearchWithList(QDialog):
    def __init__(
        self,
        model: type[DbModel],
        on_done: Callable[[QDialog, bool, DbModel], None],
        search: Callable[[int, int, str], list[DbModel]] = None,
        stringer: Callable[[DbModel], str] = None,
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
        self.stringer = stringer

        self.search_input.textChanged.connect(lambda text: self.update_results())

        self.update_results()

    def update_results(self):
        stringer = self.stringer if self.stringer else str
        if self.search:
            results = self.search(0, 10, self.search_input.text())
            self.results_list.clear()
            for result in results:
                item = QListWidgetItem(stringer(result), self.results_list)
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
    rename_fields: dict[str, str] = None,
    field_limits: dict[str, tuple[float, float]] = None,
    this_limits: tuple[float, float] = None,
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
        this_limits = this_limits if this_limits else (None, None)
        widget = QSpinBox(parent=parent)
        if this_limits[0]:
            widget.setMinimum(this_limits[0])
        if this_limits[1]:
            widget.setMaximum(this_limits[1])
        widget.setValue(initial_value)
        widget.valueChanged.connect(lambda value, setter=setter: setter(value))
    elif T == float:
        this_limits = this_limits if this_limits else (None, None)
        widget = QDoubleSpinBox(parent=parent)
        if this_limits[0]:
            widget.setMinimum(this_limits[0])
        if this_limits[1]:
            widget.setMaximum(this_limits[1])
        widget.setValue(initial_value)
        widget.valueChanged.connect(lambda value, setter=setter: setter(value))
    elif T == str or T == pydantic.EmailStr:
        widget = QLineEdit(initial_value, parent=parent)
        widget.textChanged.connect(lambda text, setter=setter: setter(text))
    elif T == list:
        widget = QFormLayout(parent=parent)
        for item in initial_value:

            def inner_setter(new_value, item=item, setter=setter):
                initial_value.__setitem__(item, new_value)
                setter(initial_value)

            wid = create_datatype_widget(
                str,
                item,
                inner_setter,
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

            def inner_setter(
                new_value, initial_value=initial_value, key=key, setter=setter
            ):
                initial_value.__setitem__(key, new_value)
                setter(initial_value)

            if rename_fields and key in rename_fields:
                key = rename_fields[key]

            limits = (0, 1000)
            if field_limits:
                limits = field_limits.get(key, this_limits)

            widget.addRow(
                QLabel(key),
                create_datatype_widget(
                    value.__class__,
                    value,
                    inner_setter,
                    field_limits=field_limits,
                    this_limits=limits,
                ),
            )

    elif issubclass(T, pydantic.BaseModel):
        widget = QFormLayout(parent=parent)
        for field, info in T.model_fields.items():
            if field not in initial_value:
                continue

            def inner_setter(
                new_value, initial_value=initial_value, setter=setter, field=field
            ):
                initial_value[field] = new_value
                setter(initial_value)

            limits = (0, 1000)
            if field_limits:
                limits = field_limits.get(field, this_limits)

            wig = create_datatype_widget(
                (
                    search_fields[field]
                    if search_fields and field in search_fields
                    else info.annotation
                ),
                initial_value[field],
                setter=inner_setter,
                field_limits=field_limits,
                this_limits=limits,
            )

            if rename_fields and field in rename_fields:
                field = rename_fields[field]
            widget.addRow(QLabel(field), wig)
    else:
        print(f"Unsupported type for widget creation: {T}")
    return widget


def create_modal_floating(
    name: str,
    model: DbModel,
    on_done: Callable[[QDialog, bool, DbModel], None],
    ignore_fields: list[str] = [],
    rename_fields: dict[str, str] = None,
    search_fields: dict[str, type[DbModel]] = None,
    field_limits: dict[str, tuple[float, float]] = None,
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

    def setter(data: dict, model=model):
        for key, value in data.items():
            model.__setattr__(key, value)

    layout: QFormLayout = create_datatype_widget(
        model.__class__,
        new_fields,
        setter=setter,
        parent=dialog,
        is_top=True,
        search_fields=search_fields,
        rename_fields=rename_fields,
        field_limits=field_limits,
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
            state="Western Australia",
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


class ServiceManagement(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.add_new_service_button = QPushButton("Add New Service", self)
        self.add_new_service_button.clicked.connect(self.add_new_service)
        layout.addWidget(self.add_new_service_button)

        self.service_table = TableView(
            model_class=Service,
            get_paginated_data=searchers[Service],
            get_count=lambda: query.get_service_count().one(),
            context_menu_actions={
                "delete": lambda field, service: self.delete_service(service),
                "copy": lambda field, service: self.copy_service(field, service),
            },
        )
        layout.addWidget(self.service_table, 1)

        database.database_updated.connect(self.service_table.update)

        self.setLayout(layout)

    def delete_service(self, service: Service):
        result = query.delete_service(service.id)
        if result.error:
            print(f"Error deleting service: {result.error}")
        else:
            self.service_table.refresh()

    def copy_service(self, field: str, service: Service):
        value = getattr(service, field, None)
        if value is not None:
            print(f"Copied {field} from {service} with value: {value}")
            QGuiApplication.clipboard().setText(str(value))

    def add_new_service(self):
        new_service = Service(
            id="Name (must be unique)", description="Description", price=100.0
        )
        modal = create_modal_floating(
            "Add New Service",
            new_service,
            self.handle_add_new_service,
            rename_fields={"id": "name"},
            field_limits={
                "price": (0.01, 10000.0)  # Price must be positive and reasonable
            },
        )

    def handle_add_new_service(self, dialog: QDialog, success: bool, service: Service):
        if success:
            try:
                if query.get_service_by_id(service.id).one():
                    raise ValueError("Service ID must be unique")
                if service.price <= 0:
                    raise ValueError("Service price must be positive")
                query.create_service(**service.model_dump())
            except Exception as e:
                print(f"Error adding new service: {e}")
        dialog.close()


# left hand side with bookings, then a panel on right hand with info and then the list of services
class BookingServiceManagement(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)

        self.booking_id = None

        self.left_panel = QWidget(self)
        self.left_layout = QVBoxLayout(self.left_panel)

        # Use a QListWidget populated from the searcher so the
        # left panel is visible inside the layout.
        self.booking_list = SearchWithList(
            Booking,
            on_done=self.on_booking_selected,
            search=searchers[Booking],
            stringer=lambda model: str(query.get_booking_string(model.id).one()),
        )
        self.left_layout.addWidget(self.booking_list)

        self.add_booking_button = QPushButton("Add Booking", self.left_panel)
        self.add_booking_button.clicked.connect(self.add_booking)
        self.left_layout.addWidget(self.add_booking_button)

        layout.addWidget(self.left_panel, 1)

        self.details_panel = QWidget(self)
        layout.addWidget(self.details_panel, 2)

        # populate the list initially
        try:
            self.update_booking_list()
        except Exception:
            # safe no-op if searcher/query not ready
            pass

        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_panel.setLayout(self.details_layout)

        self.details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.info_area = QWidget(self.details_panel)
        self.info_layout = QVBoxLayout(self.info_area)
        self.details_layout.addWidget(self.info_area, 1)

        # add a separator line
        self.details_layout.addWidget(QFrame(self.details_panel))

        self.detail_name = QLabel(self.info_area)
        self.info_layout.addWidget(self.detail_name)

        self.detail_property = QLabel(self.info_area)
        self.info_layout.addWidget(self.detail_property)

        self.detail_date = QLabel(self.info_area)
        self.info_layout.addWidget(self.detail_date)

        self.status_label = QLabel(self.info_area)
        self.info_layout.addWidget(self.status_label)

        self.payment_label = QLabel(self.info_area)
        self.info_layout.addWidget(self.payment_label)

        self.delete_button = QPushButton("Delete Booking", self.info_area)
        self.delete_button.clicked.connect(self.delete_booking)
        self.delete_button.setVisible(False)
        self.info_layout.addWidget(self.delete_button)

        self.info_layout.insertStretch(-1, 1)

        self.services_area = QFormLayout(self.details_panel)
        self.details_layout.addLayout(self.services_area, 3)

        self.add_service_button = QPushButton("Add Service", self.details_panel)
        self.add_service_button.clicked.connect(self.handle_add_new_service)
        self.details_layout.addWidget(self.add_service_button)

        self.setLayout(layout)

        database.database_updated.connect(lambda: self.booking_list.update_results())
        database.database_updated.connect(self.update_services)
        database.database_updated.connect(self.update_booking_list)

    def add_booking(self):
        model = Booking(
            id=-1,
            booking_date=date.today(),
            person_id=-1,  # Placeholder, will be set in modal
            property_id=-1,  # Placeholder, will be set in modal
        )
        modal = create_modal_floating(
            "Add New Booking",
            model,
            on_done=self.handle_add_new_booking_done,
            ignore_fields=["id"],
            rename_fields={
                "person_id": "customer",
                "property_id": "property",
            },
            search_fields={
                "person_id": Person,
                "property_id": Property,
            },
        )
        modal.exec()

    def handle_add_new_booking_done(
        self, dialog: QDialog, success: bool, booking: Booking
    ):
        if success:
            try:
                if booking.booking_date < date.today():
                    raise ValueError("Booking date must be today or in the future")
                if booking.person_id < 0:
                    raise ValueError("Person ID must be valid")
                if booking.property_id < 0:
                    raise ValueError("Property ID must be valid")
                res = query.create_booking(
                    booking.property_id, booking.person_id, booking.booking_date
                )
                if res.lastrowid:
                    self.booking_id = res.lastrowid
                    self.update_booking_list()
            except Exception as e:
                print(f"Error adding booking: {e}")
        dialog.close()

    def update_booking_list(self):
        # check if the object exists still
        if not self.booking_id:
            return
        result = query.get_booking_by_id(self.booking_id)
        if result.one() is None:
            self.booking_id = None
        else:
            self.on_booking_selected(None, True, result.one())

    def on_booking_selected(self, dialog: QDialog, success: bool, booking: Booking):
        self.booking_id = booking.id
        self.right_panel_update()

    def right_panel_update(self):
        if self.booking_id is None:
            self.detail_name.setText("")
            self.detail_property.setText("")
            self.detail_date.setText("")
            self.status_label.setText("")
            self.payment_label.setText("")
            self.delete_button.setVisible(False)
            while self.services_area.rowCount() > 0:
                self.services_area.removeRow(0)
            return
        booking = query.get_booking_by_id(self.booking_id).one()
        booking_strings = query.get_booking_string(booking.id).one()
        self.detail_name.setText(f"Customer Name: {booking_strings.person_name}")
        self.detail_property.setText(f"Property: {booking_strings.property_name}")
        self.detail_date.setText(f"Date: {booking_strings.booking_date}")
        self.delete_button.setVisible(True)

        completion = query.get_completed_service_count_by_booking(self.booking_id).one()
        if completion:
            is_done = completion.completed == completion.total
            status_text = "Done" if is_done else "In Progress"
            self.status_label.setText(
                f"{status_text}: {completion.completed}/{completion.total} services completed"
            )
        else:
            self.status_label.setText("Status: No services found")

        paid = query.get_payment_totals_by_booking(self.booking_id).one()
        total = query.get_booking_cost(self.booking_id).one()

        if paid and total:
            self.payment_label.setText(
                f"Payment: ${paid.total_amount}/{total.total}, Remaining: ${total.total - paid.total_amount}"
            )

        self.update_services()

    def delete_booking(self):
        if not self.booking_id:
            return
        query.delete_bookings_services(self.booking_id)
        query.delete_booking(self.booking_id)
        self.booking_id = None
        self.update_booking_list()
        self.right_panel_update()

    def _handle_booking_list_click(self, item: QListWidgetItem):
        booking = item.data(Qt.ItemDataRole.UserRole)
        self.on_booking_selected(None, True, booking)

    def update_services(self, search: str = ""):
        results: list[BookingService] = searchers[BookingService](
            self.booking_id, 0, 20, search
        )
        while self.services_area.rowCount() > 0:
            self.services_area.removeRow(0)
        for r in results:
            # make it so that it can add and remove services in a map from service to duration
            # service name
            service_name = QLabel(f"{r.service_id} ({r.duration} min)")
            # delete button

            double_button_spread = QWidget(self.details_panel)
            double_layout = QHBoxLayout()
            double_button_spread.setLayout(double_layout)

            completion_text = "Done" if r.completed else "Not done"
            completion_button = QPushButton(
                text=completion_text, parent=double_button_spread
            )
            double_layout.addWidget(completion_button)

            completion_button.clicked.connect(
                lambda checked, r=r: self.handle_complete_service(r)
            )

            delete_button = QPushButton(text="Delete", parent=double_button_spread)
            delete_button.clicked.connect(
                lambda checked, r=r: self.handle_delete_service(r)
            )
            double_layout.addWidget(delete_button)

            self.services_area.addRow(service_name, double_button_spread)

    def handle_add_new_service(self, e):
        model = BookingService(
            booking_id=self.booking_id,
            service_id="",
            duration=30,
            id=-1,
            completed=False,
        )
        modal = create_modal_floating(
            "Add New Service",
            model,
            on_done=self.handle_add_new_service_done,
            ignore_fields=["id", "booking_id", "completed"],
            rename_fields={
                "duration": "duration (min)",
                "service_id": "service",
            },
            search_fields={
                "service_id": Service,
                "booking_id": Booking,
            },
        )

    def handle_delete_service(self, booking_service: BookingService):
        try:
            query.delete_booking_service(
                booking_service.booking_id,
                booking_service.service_id,
            )
            self.update_services()
        except Exception as e:
            print(f"Error: {e}")

    def handle_add_new_service_done(
        self, dialog: QDialog, success: bool, service: BookingService
    ):
        if success:
            try:
                # find a service with same stuff
                existing_service = query.get_service_by_booking_and_service(
                    service.booking_id, service.service_id
                )
                if existing_service and existing_service.one() is not None:
                    print("Service already exists.")
                    return
                if service.booking_id < 0:
                    print("Error: Booking ID is not set.")
                    return
                if not service.service_id:
                    print("Error: Service ID is not set.")
                    return
                if service.duration <= 0:
                    print("Error: Duration must be positive.")
                    return

                query.create_booking_service(
                    service_id=service.service_id,
                    booking_id=service.booking_id,
                    duration=service.duration,
                )

                self.update_services()
            except Exception as e:
                print(f"Error: {e}")
        dialog.close()

    def handle_complete_service(self, booking_service: BookingService):
        try:
            query.toggle_completion_booking_service(
                booking_service.booking_id,
                booking_service.service_id,
            )
            self.update_services()
        except Exception as e:
            print(f"Error: {e}")


class RosterCreateInfo(pydantic.BaseModel):
    start_date: date
    end_date: date
    person_id: int


class RosterView(QWidget):
    def __init__(self):
        super().__init__()
        self.left_panel = QWidget(self)
        self.left_layout = QVBoxLayout(self.left_panel)

        self.calendar = QCalendarWidget(self.left_panel)
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.handle_date_selected)
        self.calendar.setMinimumDate(QDate.currentDate())
        self.calendar.setMaximumDate(QDate.currentDate().addMonths(3))
        self.left_layout.addWidget(self.calendar, 9)

        self.extra_toolbar = QWidget(self.left_panel)
        self.extra_toolbar_layout = QHBoxLayout(self.extra_toolbar)

        self.generate_roster_button = QPushButton("Generate Roster", self.extra_toolbar)
        self.extra_toolbar_layout.addWidget(self.generate_roster_button)
        self.generate_roster_button.clicked.connect(self.handle_generate_roster)

        self.left_layout.addWidget(self.extra_toolbar, 1)

        self.details_widget = QScrollArea(self)
        self.details_widget.setWidgetResizable(True)
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details_container.setLayout(self.details_layout)
        self.details_widget.setWidget(self.details_container)

        self.splitter = QWidget(self)
        self.split_layout = QHBoxLayout(self.splitter)
        self.split_layout.addWidget(self.left_panel, 1)
        self.split_layout.addWidget(self.details_widget, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.splitter)

        self.setLayout(layout)

        self.selected_date: QDate | None = None

        database.database_updated.connect(self.update_calendar)

    def handle_generate_roster(self):
        model = RosterCreateInfo(
            start_date=self.calendar.selectedDate().toPython(),
            end_date=self.calendar.selectedDate().toPython(),
            person_id=1,  # Replace with actual person ID
        )
        modal = create_modal_floating(
            "Generate Roster",
            model,
            on_done=self.handle_generate_roster_done,
            search_fields={
                "person_id": Person,
            },
            rename_fields={"person_id": "person"},
        )

    def handle_generate_roster_done(
        self, dialog: QDialog, success: bool, roster: RosterCreateInfo
    ):
        if success:
            # ensure the start is before the end
            if roster.start_date >= roster.end_date:
                print("Error: Start date must be before end date.")
                return
            person = query.get_person_by_id(roster.person_id).one()
            if not person:
                print("Error: Person not found.")
                return
            if not person.is_employee:
                print("Error: Person is not an employee.")
                return

            # create a pdf and prompt to download
            pdf = fpdf.fpdf.FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Roster", ln=True, align="C")
            pdf.cell(
                200, 10, txt=f"Start Date: {roster.start_date}", ln=True, align="C"
            )
            pdf.cell(200, 10, txt=f"End Date: {roster.end_date}", ln=True, align="C")
            pdf.cell(200, 10, txt=f"Person ID: {roster.person_id}", ln=True, align="C")

            pdf.cell(
                200,
                10,
                txt=f"Name: {person.first_name} {person.last_name}",
                ln=True,
                align="C",
            )
            pdf.cell(200, 10, txt=f"Email: {person.email}", ln=True, align="C")

            all_services = query.get_services_by_person(person.id).value

            def sort_key(s: BookingService):
                booking = query.get_booking_by_id(s.booking_id).one()
                return booking.booking_date, s.duration

            all_services.sort(key=sort_key)

            # in batches of 3 print out the services
            for i in range(0, len(all_services), 3):
                pdf.add_page()
                batch = all_services[i : i + 3]
                for booking_service in batch:
                    service = query.get_service_by_id(booking_service.service_id).one()
                    location: query.BookingServiceStrings = (
                        query.get_booking_service_string(
                            booking_service.booking_id, booking_service.service_id
                        ).one()
                    )
                    pdf.set_font("Arial", style="B", size=14)
                    pdf.cell(
                        200,
                        10,
                        txt=f"Service Name: {location.service_name}",
                        ln=True,
                    )
                    pdf.set_font("Arial", size=12)
                    pdf.cell(
                        200,
                        10,
                        txt=f"Location: {location.property_name}",
                        ln=True,
                    )
                    pdf.cell(
                        200,
                        10,
                        txt=f"Booking Date: {location.booking_date}",
                        ln=True,
                    )
                    pdf.cell(
                        200,
                        10,
                        txt=f"Service Duration (mins): {booking_service.duration}",
                        ln=True,
                    )
                    pdf.cell(
                        200,
                        10,
                        txt=f"Service Price: ${service.price}",
                        ln=True,
                    )
                    pdf.cell(
                        200,
                        10,
                        txt=f"Service Completed: {booking_service.completed}",
                        ln=True,
                    )

            pdf_file = (
                f"roster_{person.first_name}_{person.last_name}_{roster.start_date}.pdf"
            )
            pdf.output(pdf_file)

        dialog.close()

    def update_calendar(self):
        if self.selected_date is not None:
            self.handle_date_selected(self.selected_date)
        else:
            self.clear_details()

    def clear_details(self):
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            else:
                # if it's a nested layout, try to clear it recursively
                try:
                    sublayout = item.layout()
                    while sublayout and sublayout.count():
                        sub = sublayout.takeAt(0)
                        if sub and sub.widget():
                            sub.widget().setParent(None)
                            sub.widget().deleteLater()
                except Exception:
                    pass

    def handle_date_selected(self, date: QDate):
        self.selected_date = date
        self.clear_details()

        booking_services: list[BookingService] = query.get_services_by_date(
            date.toPython(), date.toPython()
        ).value

        bookings: dict[int, list[BookingService]] = dict()
        for service in booking_services:
            if service.booking_id not in bookings:
                bookings[service.booking_id] = []
            bookings[service.booking_id].append(service)

        for booking_id, booking_services in bookings.items():
            inner_widget = QWidget(self.details_container)
            inner_layout = QVBoxLayout(inner_widget)
            booking_strings = query.get_booking_string(booking_id).one()
            inner_layout.addWidget(QLabel(f"Customer: {booking_strings.person_name}"))
            inner_layout.addWidget(QLabel(f"Property: {booking_strings.property_name}"))

            inner_layout.addWidget(QFrame(inner_widget, frameShape=QFrame.Shape.HLine))

            for service in booking_services:
                strings: query.BookingServiceStrings = query.get_booking_service_string(
                    booking_id, service.service_id
                ).one()

                people = query.get_people_page_by_service(service.id, 0, 100).value

                inner_layout.addWidget(QLabel(f"Service: {strings.service_name}"))
                inner_layout.addWidget(QLabel(f"Price ($): {strings.price}"))
                inner_layout.addWidget(QLabel(f"Duration (mins): {strings.duration}"))
                inner_layout.addWidget(
                    QLabel(f"Completed : {True if strings.completed else False}")
                )

                form_layout = QFormLayout(inner_widget)
                for person in people:
                    button = QPushButton("Remove")
                    button.clicked.connect(
                        lambda _, p=person, s=service: self.remove_person(p, s)
                    )
                    form_layout.addRow(
                        QLabel(f"{person.first_name} {person.last_name}"), button
                    )

                completed = service.completed

                service_id = service.id
                add_new_person_button = QPushButton("Add New Person", inner_widget)
                add_new_person_button.clicked.connect(
                    lambda _, s=service_id: self.add_person_to_service(s)
                )
                if completed:
                    add_new_person_button.setEnabled(False)
                    add_new_person_button.setText("Completed")
                form_layout.addRow(add_new_person_button)
                inner_layout.addLayout(form_layout)

                inner_layout.addStretch(1)
                # add widget to the details container layout so scroll area updates
                self.details_layout.addWidget(inner_widget)
                inner_layout.addWidget(
                    QFrame(inner_widget, frameShape=QFrame.Shape.HLine)
                )
        # keep items at top; add final stretch so content hugs top when few items
        self.details_layout.addStretch(1)

    def remove_person(self, person: Person, service: BookingService):
        query.delete_roster(person.id, service.id)
        self.update_calendar()

    def add_person_to_service(self, booking_service_id: int):
        model = Roster(
            id=-1,
            person_id=-1,
            booking_service_id=booking_service_id,
        )
        modal = create_modal_floating(
            "Add Person to Service",
            model,
            on_done=self.handle_add_person_done,
            ignore_fields=["id", "booking_service_id"],
            rename_fields={"person_id": "person"},
            search_fields={"person_id": Person},
        )

    def handle_add_person_done(self, dialog: QDialog, success: bool, roster: Roster):
        if success:
            try:
                if roster.person_id < 0:
                    raise ValueError("Invalid person ID")
                person = query.get_person_by_id(roster.person_id).one()
                if not person:
                    raise ValueError("Person not found")
                if not person.is_employee:
                    raise ValueError("Person is not an employee")
                query.create_roster(roster.person_id, roster.booking_service_id)
            except Exception as e:
                print(f"Error adding roster: {e}")
        dialog.close()


# Gives a calendar view of all the bookings for this client on the left
# and a right panel split into details and actions
class ClientBookingView(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_date = None
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.handle_date_selected)
        self.calendar.setMinimumDate(QDate.currentDate())
        self.calendar.setMaximumDate(QDate.currentDate().addMonths(3))

        # details area is a scroll area with an internal container widget
        self.details_widget = QScrollArea(self)
        self.details_widget.setWidgetResizable(True)
        self.details_container = QWidget()
        # vertical layout inside the scroll area's internal widget
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details_container.setLayout(self.details_layout)
        self.details_widget.setWidget(self.details_container)

        self.splitter = QWidget(self)
        self.split_layout = QHBoxLayout(self.splitter)
        self.split_layout.addWidget(self.calendar, 1)
        self.split_layout.addWidget(self.details_widget, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.splitter)

        self.setLayout(layout)

        database.database_updated.connect(self.update_calendar)

    def set_client(self, client: Person):
        self.client = client
        self.setWindowTitle(f"Bookings for {client.first_name} {client.last_name}")

    def update_calendar(self):
        if self.selected_date is not None:
            self.handle_date_selected(self.selected_date)
        else:
            self.clear_details()

    def clear_details(self):
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            else:
                # if it's a nested layout, try to clear it recursively
                try:
                    sublayout = item.layout()
                    while sublayout and sublayout.count():
                        sub = sublayout.takeAt(0)
                        if sub and sub.widget():
                            sub.widget().setParent(None)
                            sub.widget().deleteLater()
                except Exception:
                    pass

    def handle_date_selected(self, date: QDate):
        self.selected_date = date
        self.clear_details()

        booking_services: list[BookingService] = query.get_services_person_and_date(
            self.client.id, date.toPython(), date.toPython()
        ).value

        bookings: dict[int, list[BookingService]] = dict()
        for service in booking_services:
            if service.booking_id not in bookings:
                bookings[service.booking_id] = []
            bookings[service.booking_id].append(service)

        for booking_id, booking_services in bookings.items():
            inner_widget = QWidget(self.details_container)
            inner_layout = QVBoxLayout(inner_widget)
            booking_strings = query.get_booking_string(booking_id).one()
            inner_layout.addWidget(QLabel(f"Property: {booking_strings.property_name}"))

            total = query.get_booking_cost(booking_id).one()
            payment = query.get_payment_totals_by_booking(booking_id).one()
            inner_layout.addWidget(
                QLabel(f"Payment Total ($): {payment.total_amount}/{total.total}")
            )

            remaining_payment = total.total - payment.total_amount
            inner_layout.addWidget(
                QLabel(f"Remaining Payment ($): {remaining_payment}")
            )

            add_payment_button = QPushButton("Add Payment", inner_widget)
            add_payment_button.clicked.connect(
                lambda _, bid=booking_id, rp=remaining_payment: self.add_payment(
                    bid, rp
                )
            )
            if remaining_payment <= 0:
                add_payment_button.setEnabled(False)
                add_payment_button.setText("Payment Complete")
            inner_layout.addWidget(add_payment_button)

            generate_invoice_button = QPushButton("Generate Invoice", inner_widget)
            generate_invoice_button.clicked.connect(
                lambda _, bid=booking_id: self.generate_invoice(bid)
            )
            inner_layout.addWidget(generate_invoice_button)

            inner_layout.addWidget(QFrame(inner_widget, frameShape=QFrame.Shape.HLine))

            for service in booking_services:
                strings: query.BookingServiceStrings = query.get_booking_service_string(
                    booking_id, service.service_id
                ).one()
                inner_layout.addWidget(QLabel(f"Service: {strings.service_name}"))
                inner_layout.addWidget(QLabel(f"Price ($): {strings.price}"))
                inner_layout.addWidget(QLabel(f"Duration (mins): {strings.duration}"))
                inner_layout.addWidget(
                    QLabel(f"Completed : {True if strings.completed else False}")
                )
                inner_layout.addStretch(1)
                # add widget to the details container layout so scroll area updates
                self.details_layout.addWidget(inner_widget)
                inner_layout.addWidget(
                    QFrame(inner_widget, frameShape=QFrame.Shape.HLine)
                )
        # keep items at top; add final stretch so content hugs top when few items
        self.details_layout.addStretch(1)

    def add_payment(self, booking_id: int, remaining_payment: float):
        model = Payment(
            id=-1,
            booking_id=booking_id,
            amount=0.0,
            payment_date=date.today(),
        )
        modal = create_modal_floating(
            "Payment",
            model=model,
            on_done=self.handle_payment_done,
            field_limits={"amount": (0, remaining_payment)},
            ignore_fields=["id", "booking_id", "payment_date"],
        )

    def handle_payment_done(self, dialog: QDialog, success: bool, payment: Payment):
        if success:
            query.create_payment(
                payment.booking_id, payment.amount, payment.payment_date
            )
        dialog.close()

    def generate_invoice(self, booking_id: int):
        invoice_data = query.get_booking_string(booking_id).one()
        if not invoice_data:
            print("No invoice data found.")
            return

        total_cost = query.get_booking_cost(booking_id).one()
        if not total_cost:
            print("No total cost found.")
            return

        file = fpdf.fpdf.FPDF()
        file.add_page()
        file.set_font("Arial", size=12)

        # Add invoice details
        file.cell(200, 10, txt=f"Invoice for Booking ID: {booking_id}", ln=True)
        file.cell(200, 10, txt=f"Date: {invoice_data.booking_date}", ln=True)
        file.cell(200, 10, txt=f"Property: {invoice_data.property_name}", ln=True)

        # Add a line break
        file.cell(200, 10, txt="", ln=True)

        services = query.get_services_by_booking(booking_id).value

        # print out all of the services
        for service in services:
            booking_service_strings = query.get_booking_service_string(
                booking_id, service.service_id
            ).one()
            file.cell(
                200,
                10,
                txt=f" - {booking_service_strings.service_name}: ${booking_service_strings.price}",
                ln=True,
            )
            file.cell(
                200,
                10,
                txt=f"   Duration: {booking_service_strings.duration} mins",
                ln=True,
            )
            file.cell(
                200,
                10,
                txt=f"   Completed: {booking_service_strings.completed}",
                ln=True,
            )

        # footer
        file.cell(200, 10, txt=f"Total Amount: ${total_cost.total}", ln=True)
        file.cell(200, 10, txt="Thank you for your business!", ln=True)

        # Save the invoice
        file.output(
            f"invoice_{invoice_data.booking_date}_{invoice_data.property_name}.pdf"
        )


class StatsView(QWidget):
    def __init__(self):
        super().__init__()

        split_left_right_layout = QHBoxLayout(self)

        # left is a list of queries
        self.queries_list = QFormLayout(self)
        split_left_right_layout.addLayout(self.queries_list)

        # right is a List
        self.results_list = QListWidget(self)
        split_left_right_layout.addWidget(self.results_list)

        # some queries
        queries = {
            "Unpaid bookings": query.get_unpaid_bookings,
            "Income by month": query.get_income_by_month,
            "Outstanding clients": query.get_outstanding_clients,
            "Popular services": query.get_popular_services,
        }
        for query_name, query_func in queries.items():
            button = QPushButton(query_name, self)
            button.clicked.connect(lambda _, f=query_func: self.run_query(f))
            self.queries_list.addWidget(button)

    def clear(self):
        self.results_list.clear()

    def run_query(self, query_func):
        self.clear()
        results = query_func()
        if results.value:
            for result in results.value:
                self.results_list.addItem(str(result))
        else:
            self.results_list.addItem("No results found.")


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


TAB_STATS = 0
TAB_MANAGE_PERSONS = 1
TAB_MANAGE_PROPERTIES = 2
TAB_MANAGE_SERVICES = 3
TAB_MANAGE_BOOKING_SERVICES = 4
TAB_MANAGE_ROSTER = 5

TAB_CLIENT_BOOKINGS = 6


class Ui(QMainWindow):
    def __init__(self, user=None, password=None):
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
        self.stats_widget = StatsView()
        self.tab_widget.addTab(self.stats_widget, "Statistics")
        self.manage_persons_widget = PersonManagement()
        self.tab_widget.addTab(self.manage_persons_widget, "Manage Persons")
        self.manage_properties_widget = PropertyManagement()
        self.tab_widget.addTab(self.manage_properties_widget, "Manage Properties")
        self.manage_services_widget = ServiceManagement()
        self.tab_widget.addTab(self.manage_services_widget, "Manage Services")
        self.manage_booking_services_widget = BookingServiceManagement()
        self.tab_widget.addTab(
            self.manage_booking_services_widget, "Manage Booking Services"
        )
        self.manage_roster_widget = RosterView()
        self.tab_widget.addTab(self.manage_roster_widget, "Manage Roster")

        # client only
        self.client_bookings_widget = ClientBookingView()
        self.tab_widget.addTab(self.client_bookings_widget, "Client Bookings")

        if user is not None and password is not None:
            self.handle_login(user, password)

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

        self.tab_widget.setTabVisible(TAB_STATS, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_PERSONS, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_PROPERTIES, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_SERVICES, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_BOOKING_SERVICES, is_employee)
        self.tab_widget.setTabVisible(TAB_MANAGE_ROSTER, is_employee)

        self.tab_widget.setTabVisible(TAB_CLIENT_BOOKINGS, not is_employee)

    def handle_login(self, username: str, password: str):
        result = query.login_person(username, auth.hash_plaintext(password))

        if result.error:
            print(f"Login failed: {result.error}")
        else:
            self.logged_in_as_user = result.one()
            if self.logged_in_as_user:
                print(f"Login successful: {self.logged_in_as_user}")
                self.client_bookings_widget.set_client(self.logged_in_as_user)

        self.handle_state()

    def handle_logout(self):
        self.logged_in_as_user = None
        self.handle_state()

    def closeAll(self):
        self.close()
        self.login_frame.close()
