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


class DirectAccessTabView(ctk.CTkTabview):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state
        self.add("Customers")
        self.add("Properties")
        self.add("Bookings")
        self.add("Settings")
        self.set("Customers")  # Set the default tab

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


class CreateCustomerForm(ctk.CTkFrame):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state

        self.first_name_entry = ctk.CTkEntry(master=self, placeholder_text="First Name")
        self.first_name_entry.pack(pady=5)

        self.last_name_entry = ctk.CTkEntry(master=self, placeholder_text="Last Name")
        self.last_name_entry.pack(pady=5)

        self.email_entry = ctk.CTkEntry(master=self, placeholder_text="Email")
        self.email_entry.pack(pady=5)

        self.phone_entry = ctk.CTkEntry(master=self, placeholder_text="Phone Number")
        self.phone_entry.pack(pady=5)

        self.submit_button = ctk.CTkButton(
            master=self, text="Submit", command=self.submit
        )
        self.submit_button.pack(pady=5)

    def submit(self):
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        email = self.email_entry.get()
        phone = self.phone_entry.get()

        if not (first_name and last_name and email and phone):
            ErrorDialog("All fields are required.", master=self)
            return

        customer_model = CustomerModel(-1, first_name, last_name, email, phone)
        if self.app_state.database.add_customer(customer_model):
            ErrorDialog("Customer created successfully.", master=self)
            self.clear_fields()
        else:
            ErrorDialog(
                f"Failed to create customer: {self.app_state.database.last_error}",
                master=self,
            )

    def clear_fields(self):
        self.first_name_entry.delete(0, "end")
        self.last_name_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")


class CreatePropertyForm(ctk.CTkFrame):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state

        self.street_number_entry = ctk.CTkEntry(
            master=self, placeholder_text="Street Number"
        )
        self.street_number_entry.pack(pady=5)

        self.unit_entry = ctk.CTkEntry(master=self, placeholder_text="Unit (optional)")
        self.unit_entry.pack(pady=5)

        self.street_name_entry = ctk.CTkEntry(
            master=self, placeholder_text="Street Name"
        )
        self.street_name_entry.pack(pady=5)

        self.city_entry = ctk.CTkEntry(master=self, placeholder_text="City")
        self.city_entry.pack(pady=5)

        self.post_code_entry = ctk.CTkEntry(master=self, placeholder_text="Post Code")
        self.post_code_entry.pack(pady=5)

        self.submit_button = ctk.CTkButton(
            master=self, text="Submit", command=self.submit
        )
        self.submit_button.pack(pady=5)

    def submit(self):
        street_number = self.street_number_entry.get()
        unit = self.unit_entry.get()
        street_name = self.street_name_entry.get()
        city = self.city_entry.get()
        post_code = self.post_code_entry.get()

        if not (street_number and street_name and city and post_code):
            ErrorDialog(
                "Street Number, Street Name, City, and Post Code are required.",
                master=self,
            )
            return

        property_model = PropertyModel(
            -1,
            int(street_number),
            unit if len(unit) > 0 else None,
            street_name,
            city,
            post_code,
        )
        if self.app_state.database.add_property(property_model):
            ErrorDialog("Property created successfully.", master=self)
            self.clear_fields()
        else:
            ErrorDialog(
                f"Failed to create property: {self.app_state.database.last_error}",
                master=self,
            )

    def clear_fields(self):
        self.street_number_entry.delete(0, "end")
        self.unit_entry.delete(0, "end")
        self.street_name_entry.delete(0, "end")
        self.city_entry.delete(0, "end")
        self.post_code_entry.delete(0, "end")


class SearchbarWithCompletion(ctk.CTkFrame):
    def __init__(self, app_state: State, title, search_fn, on_choose, master=None):
        super().__init__(master)
        self.title = title
        self.app_state = app_state
        self.search_fn = search_fn
        self.on_choose = on_choose

        self.title_label = ctk.CTkLabel(master=self, text=self.title)
        self.title_label.pack(pady=5)

        self.search_entry = ctk.CTkEntry(master=self, placeholder_text="Search")
        self.search_entry.pack(expand=True, fill="x", padx=10, pady=10)

        self.options = ctk.CTkScrollableFrame(self)
        self.options.pack(expand=True, fill="both", padx=10, pady=10)

        # as the user types, we will show the results in this frame
        self.search_entry.bind("<KeyRelease>", self.on_search)

    def on_search(self, event=None):
        search_text = self.search_entry.get().strip()
        if search_text:
            results = self.search_fn(search_text)
            self.update_options(results)
        else:
            self.update_options([])

    def update_options(self, results):
        for widget in self.options.winfo_children():
            widget.destroy()

        for item in results:
            option_button = ctk.CTkButton(
                master=self.options,
                text=str(item),
                command=lambda i=item: self.on_choose(i),
            )
            option_button.pack(fill="x", padx=5, pady=2)


class CreateBookingForm(ctk.CTkScrollableFrame):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state

        self.splitter = ctk.CTkFrame(master=self)

        self.customer_search = SearchbarWithCompletion(
            title="Search Customers",
            app_state=self.app_state,
            search_fn=self.app_state.database.search_customers,
            on_choose=self.on_customer_choose,
            master=self.splitter,
        )
        # self.customer_search.pack(expand=True, fill="x", padx=10, pady=10)
        self.customer_search.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.property_search = SearchbarWithCompletion(
            title="Search Properties",
            app_state=self.app_state,
            search_fn=self.app_state.database.search_properties,
            on_choose=self.on_property_choose,
            master=self.splitter,
        )
        self.property_search.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        self.splitter.pack(expand=True, fill="x", padx=10, pady=10)
        self.splitter.columnconfigure(0, weight=1)
        self.splitter.columnconfigure(1, weight=1)

        self.when_entry = ctk.CTkEntry(master=self, placeholder_text="When")
        self.when_entry.pack(pady=5)

        self.submit_button = ctk.CTkButton(
            master=self, text="Submit", command=self.submit
        )
        self.submit_button.pack(pady=5)

    def on_customer_choose(self, customer_name):
        print(f"Selected customer: {customer_name}")
        # Handle customer selection
        pass

    def on_property_choose(self, property_name):
        print(f"Selected property: {property_name}")
        # Handle property selection
        pass

    def submit(self):
        # Handle form submission
        pass


class TabView(ctk.CTkTabview):
    def __init__(self, app_state: State, master=None):
        super().__init__(master)
        self.app_state = app_state

        self.add("Home")
        self.add("Customers")
        self.add("Properties")
        self.add("Bookings")
        self.add("Direct Access")
        self.set("Home")

        self.home_tab = ctk.CTkFrame(self.tab("Home"))
        self.home_tab.pack(expand=True, fill="both")

        self.customers_tab = ctk.CTkFrame(self.tab("Customers"))
        self.customers_tab.pack(expand=True, fill="both")

        self.create_customer_form = CreateCustomerForm(
            app_state=self.app_state, master=self.customers_tab
        )
        self.create_customer_form.pack(expand=True, fill="both")

        self.properties_tab = ctk.CTkFrame(self.tab("Properties"))
        self.properties_tab.pack(expand=True, fill="both")

        self.create_property_form = CreatePropertyForm(
            app_state=self.app_state, master=self.properties_tab
        )
        self.create_property_form.pack(expand=True, fill="both")

        self.bookings_tab = ctk.CTkFrame(self.tab("Bookings"))
        self.bookings_tab.pack(expand=True, fill="both")

        self.create_booking_form = CreateBookingForm(
            app_state=self.app_state, master=self.bookings_tab
        )
        self.create_booking_form.pack(expand=True, fill="both")

        self.direct_access_tab = DirectAccessTabView(
            app_state=self.app_state, master=self.tab("Direct Access")
        )
        self.direct_access_tab.pack(expand=True, fill="both")


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

        # self.tab_view = TabView(app_state=self.app_state, master=self)
        # self.tab_view.pack(expand=True, fill="both")

        self.tab_view = TabView(app_state=self.app_state, master=self)
        self.tab_view.pack(expand=True, fill="both")

    def test_cb(self):
        self.app_state.test()
