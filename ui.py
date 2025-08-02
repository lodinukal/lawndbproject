# simple tkinter ui to interact with the app
from datetime import datetime
import customtkinter as ctk

from typing import Callable, Any

from app import State
from database import BookingModel, CustomerModel, PropertyModel

from ui_base import ModelEditor, TableUser, TableView, ErrorDialog
from util import Signal

ctk.set_appearance_mode("dark")


class DataTabInfo:
    columns: list[str]
    create_fake_function: None | Callable[[], None]
    create_function: None | Callable[[], None]
    dependent_signals: list[Signal]

    gather_data: Callable[[int, int], list]
    get_max_pages: Callable[[int], int]
    delete_items: Callable[[list[int]], None]
    create_editor: Callable[[Any | None], None]


class DataTab(ctk.CTkScrollableFrame, TableUser):
    def __init__(self, app_state: State, info: DataTabInfo, master=None):
        super().__init__(master)
        self.app_state = app_state
        self.info = info

        self.table = TableView(
            user=self,
            master=self,
            columns=self.info.columns,
        )
        self.table.pack(expand=True, fill="both")

        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(expand=False, fill="x")

        if self.info.create_fake_function is not None:
            self.fake_button = ctk.CTkButton(
                master=self.buttons_frame,
                text="Generate Fake",
                command=self.add_fake_item,
            )
            self.fake_button.pack(pady=5)

        self.create_button = ctk.CTkButton(
            master=self.buttons_frame,
            text="Create",
            command=self.create_item,
        )
        self.create_button.pack(pady=5)

        for signal in self.info.dependent_signals:
            signal.connect(self.on_data_updated)

    def add_fake_item(self):
        if self.info.create_fake_function is not None:
            self.info.create_fake_function()
        else:
            ErrorDialog("Failed to add item", master=self)

    def create_item(self):
        if self.info.create_function is not None:
            self.info.create_function()
        else:
            ErrorDialog("Failed to create item", master=self)

    def on_data_updated(self):
        self.table.load_data()

    # table things
    def gather_data(self, page_index: int, page_size: int = 10):
        return self.info.gather_data(page_index, page_size)

    def get_max_pages(self, page_size: int):
        return self.info.get_max_pages(page_size)

    def delete_items(self, selected: list[int]):
        self.info.delete_items(selected)

    def edit_item(self, item):
        customer = self.app_state.database.get_customer_by_id(item)
        if customer:
            self.info.create_editor(customer)
        else:
            ErrorDialog(f"Customer with id {item} not found.", master=self)


class CustomerTab(DataTab):
    def __init__(self, app_state: State, master=None):
        info = DataTabInfo()
        info.columns = ["ID", "First Name", "Last Name", "Email", "Phone"]
        info.create_fake_function = app_state.add_fake_customer
        info.create_function = lambda: self.create_customer_editor(None)
        info.dependent_signals = [app_state.database.customers_changed]
        info.gather_data = app_state.database.get_all_customers
        info.get_max_pages = app_state.database.get_num_customer_pages
        info.delete_items = app_state.database.remove_customer_by_id
        info.create_editor = self.create_customer_editor
        super().__init__(app_state, info, master)

    def create_customer_editor(self, model: CustomerModel | None):
        new_model = (
            model
            if model
            else CustomerModel(-1, "First name", "Last name", "Email", "Phone number")
        )
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.app_state.database.add_or_update_customer(m),
            master=self,
        )
        editor.grab_set()


class PropertyTab(DataTab):
    def __init__(self, app_state: State, master=None):
        info = DataTabInfo()
        info.columns = [
            "ID",
            "Street Number",
            "Unit",
            "Street Name",
            "City",
            "Post Code",
        ]
        info.create_fake_function = app_state.add_fake_property
        info.create_function = lambda: self.create_property_editor(None)
        info.dependent_signals = [app_state.database.properties_changed]
        info.gather_data = app_state.database.get_all_properties
        info.get_max_pages = app_state.database.get_num_property_pages
        info.delete_items = app_state.database.remove_property_by_id
        info.create_editor = self.create_property_editor
        super().__init__(app_state, info, master)

    def create_property_editor(self, model: PropertyModel | None):
        new_model = (
            model
            if model
            else PropertyModel(-1, 0, "Street Name", "City", "Post Code", None)
        )
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.app_state.database.add_or_update_property(m),
            master=self,
        )
        editor.grab_set()


class BookingTab(DataTab):
    def __init__(self, app_state: State, master=None):
        info = DataTabInfo()
        info.columns = ["ID", "Customer ID", "Property ID", "When"]
        info.create_fake_function = None
        info.create_function = lambda: self.create_booking_editor(None)
        info.dependent_signals = [app_state.database.bookings_changed]
        info.gather_data = app_state.database.get_all_bookings
        info.get_max_pages = app_state.database.get_num_booking_pages
        info.delete_items = app_state.database.remove_booking_by_id
        info.create_editor = self.create_booking_editor
        super().__init__(app_state, info, master)

    def create_booking_editor(self, model: BookingModel | None):
        new_model = model if model else BookingModel(-1, -1, -1, datetime.now())
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.verify_update_booking(m),
            master=self,
        )
        editor.grab_set()

    def verify_update_booking(self, model: BookingModel):
        model.assure()
        if self.app_state.database.add_or_update_booking(model):
            return True
        ErrorDialog(
            f"Failed to set booking: {self.app_state.database.last_error}",
            master=self,
        )
        return False


class SettingsTab(ctk.CTkFrame):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state

        reset_database_button = ctk.CTkButton(
            master=self,
            text="Reset Database",
            command=lambda: self.app_state.database.reset(),
        )
        reset_database_button.pack(pady=5)


class TabView(ctk.CTkTabview):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state
        self.add("Home")
        self.add("Customers")
        self.add("Properties")
        self.add("Bookings")
        self.add("Settings")
        self.set("Home")  # Set the default tab

        self.customers_tab = CustomerTab(
            app_state=self.app_state, master=self.tab("Customers")
        )
        self.customers_tab.pack(expand=True, fill="both")

        self.properties_tab = PropertyTab(
            app_state=self.app_state, master=self.tab("Properties")
        )
        self.properties_tab.pack(expand=True, fill="both")

        self.bookings_tab = BookingTab(
            app_state=self.app_state, master=self.tab("Bookings")
        )
        self.bookings_tab.pack(expand=True, fill="both")

        self.settings_tab = SettingsTab(
            app_state=self.app_state, master=self.tab("Settings")
        )
        self.settings_tab.pack(expand=True, fill="both")


class Ui(ctk.CTk):
    def __init__(self, app_state: State):
        super().__init__()
        self.app_state = app_state
        self.title("Lawn Database")
        self.geometry("800x600")
        self.iconbitmap("static/icon.ico")

        # Create UI elements here
        label = ctk.CTkLabel(master=self, text="Lawn Database")
        label.pack(pady=20)

        self.tab_view = TabView(app_state=self.app_state, master=self)
        self.tab_view.pack(expand=True, fill="both")

    def test_cb(self):
        self.app_state.test()
