# simple tkinter ui to interact with the app
from datetime import datetime
import customtkinter as ctk

from typing import Callable, Any

from app import State
from custom_notifications.notification_type import NotifyType
from database import (
    Access,
    BookingModel,
    BookingServiceModel,
    CustomerModel,
    PaymentModel,
    PropertyModel,
    ServiceModel,
)

from ui_base import (
    DatetimeValidatedEntry,
    ModelEditor,
    SearchbarWithCompletion,
    TableUser,
    TableView,
)
from custom_notifications import NotificationManager
from util import Signal

ctk.set_appearance_mode("dark")


class UIState:
    app_state: State
    notification_manager: NotificationManager

    def err(self, message: str):
        self.notification_manager.show_notification(
            message=message, notify_type=NotifyType.ERROR
        )

    def info(self, message: str):
        self.notification_manager.show_notification(
            message=message, notify_type=NotifyType.INFO
        )


class DataTabInfo:
    columns: list[str]
    create_fake_function: None | Callable[[], None]
    create_function: None | Callable[[], None]
    dependent_signals: list[Signal]

    gather_data: Callable[[int, int], list]
    get_max_pages: Callable[[int], int]
    delete_items: Callable[[list[int]], None]
    create_editor: Callable[[Any | None], None]

    access: Access

    def __init__(self, access: Access = Access.WRITE):
        self.access = access


class DataTab(ctk.CTkScrollableFrame, TableUser):
    def __init__(self, ui_state: UIState, info: DataTabInfo, master=None):
        super().__init__(master)
        self.ui_state = ui_state
        self.info = info

        self.table = TableView(
            user=self,
            master=self,
            columns=self.info.columns,
            access=self.info.access,
        )
        self.table.pack(expand=True, fill="both")

        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(expand=False, fill="x")

        if (
            self.info.create_fake_function is not None
            and self.info.access == Access.WRITE
        ):
            self.fake_button = ctk.CTkButton(
                master=self.buttons_frame,
                text="Generate Fake",
                command=self.add_fake_item,
            )
            self.fake_button.pack(pady=5)

        if self.info.create_function is not None and self.info.access == Access.WRITE:
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
            self.ui_state.err("Failed to add item")

    def create_item(self):
        if self.info.create_function is not None:
            self.info.create_function()
        else:
            self.ui_state.err("Failed to create item")

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
        if self.info.create_editor(item) == False:
            self.ui_state.err(f"Failed to edit item with id {item.id}.")


class CustomerTab(DataTab):
    def __init__(self, ui_state: UIState, master=None):
        info = DataTabInfo()
        info.columns = ["ID", "First Name", "Last Name", "Email", "Phone"]
        info.create_fake_function = ui_state.app_state.add_fake_customer
        info.create_function = lambda: self.create_customer_editor(None)
        info.dependent_signals = [ui_state.app_state.database.customers_changed]
        info.gather_data = ui_state.app_state.database.get_all_customers
        info.get_max_pages = ui_state.app_state.database.get_num_customer_pages
        info.delete_items = ui_state.app_state.database.remove_customer_by_id
        info.create_editor = self.create_customer_editor
        super().__init__(ui_state, info, master)

    def create_customer_editor(self, id: int | None):
        model = self.ui_state.app_state.database.get_customer_by_id(id) if id else None
        new_model = (
            model
            if model
            else CustomerModel(-1, "First name", "Last name", "Email", "Phone number")
        )
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.ui_state.app_state.database.add_or_update_customer(
                m
            ),
            master=self,
        )


class PropertyTab(DataTab):
    def __init__(self, ui_state: UIState, master=None):
        info = DataTabInfo()
        info.columns = [
            "ID",
            "Street Number",
            "Unit",
            "Street Name",
            "City",
            "Post Code",
        ]
        info.create_fake_function = ui_state.app_state.add_fake_property
        info.create_function = lambda: self.create_property_editor(None)
        info.dependent_signals = [ui_state.app_state.database.properties_changed]
        info.gather_data = ui_state.app_state.database.get_all_properties
        info.get_max_pages = ui_state.app_state.database.get_num_property_pages
        info.delete_items = ui_state.app_state.database.remove_property_by_id
        info.create_editor = self.create_property_editor
        super().__init__(ui_state, info, master)

    def create_property_editor(self, id: int | None):
        model = self.ui_state.app_state.database.get_property_by_id(id) if id else None
        new_model = (
            model
            if model
            else PropertyModel(-1, 0, "Street Name", "City", "Post Code", None)
        )
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.ui_state.app_state.database.add_or_update_property(
                m
            ),
            master=self,
        )


class BookingTab(DataTab):
    def __init__(self, ui_state: UIState, master=None):
        info = DataTabInfo()
        info.columns = ["ID", "Customer ID", "Property ID", "When"]
        info.create_fake_function = None
        info.create_function = lambda: self.create_booking_editor(None)
        info.dependent_signals = [ui_state.app_state.database.bookings_changed]
        info.gather_data = ui_state.app_state.database.get_all_bookings
        info.get_max_pages = ui_state.app_state.database.get_num_booking_pages
        info.delete_items = ui_state.app_state.database.remove_booking_by_id
        info.create_editor = self.create_booking_editor
        super().__init__(ui_state, info, master)

    def create_booking_editor(self, model_id: int | None):
        model = (
            self.ui_state.app_state.database.get_booking_by_id(model_id)
            if model_id
            else None
        )
        new_model = model if model else BookingModel(-1, -1, -1, datetime.now())
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.verify_update_booking(m),
            master=self,
        )

    def verify_update_booking(self, model: BookingModel):
        model.assure()
        if self.ui_state.app_state.database.add_or_update_booking(model):
            return True
        self.ui_state.err(
            f"Failed to set booking: {self.ui_state.app_state.database.last_error}"
        )
        return False


class ServiceTab(DataTab):
    def __init__(self, ui_state: UIState, access: Access = Access.WRITE, master=None):
        info = DataTabInfo(access=access)
        info.columns = ["ID", "Name", "Base Price"]
        info.create_fake_function = None
        info.create_function = lambda: self.create_service_editor(None)
        info.dependent_signals = [ui_state.app_state.database.services_changed]
        info.gather_data = ui_state.app_state.database.get_all_services
        info.get_max_pages = ui_state.app_state.database.get_num_service_pages
        info.delete_items = ui_state.app_state.database.remove_service_by_id
        info.create_editor = self.create_service_editor
        super().__init__(ui_state, info, master)

    def create_service_editor(self, model_id: int | None):
        model = (
            self.ui_state.app_state.database.get_service_by_id(model_id)
            if model_id
            else None
        )
        new_model = model if model else ServiceModel(-1, "Service Name", 0.0)
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.ui_state.app_state.database.add_or_update_service(
                m
            ),
            master=self,
        )


class PaymentTab(DataTab):
    def __init__(self, ui_state: UIState, master=None):
        info = DataTabInfo()
        info.columns = ["ID", "Booking ID", "Amount", "Payment Date"]
        info.create_fake_function = None
        info.create_function = lambda: self.create_payment_editor(None)
        info.dependent_signals = [ui_state.app_state.database.payments_changed]
        info.gather_data = ui_state.app_state.database.get_all_payments
        info.get_max_pages = ui_state.app_state.database.get_num_payment_pages
        info.delete_items = ui_state.app_state.database.remove_payment_by_id
        info.create_editor = self.create_payment_editor
        super().__init__(ui_state, info, master)

    def create_payment_editor(self, model_id: int | None):
        model = (
            self.ui_state.app_state.database.get_payment_by_id(model_id)
            if model_id
            else None
        )
        new_model = model if model else PaymentModel(-1, -1, 0.0, datetime.now())
        editor = ModelEditor(
            model=new_model,
            on_complete=lambda m: self.ui_state.app_state.database.add_or_update_payment(
                m
            ),
            master=self,
        )


class SettingsTab(ctk.CTkFrame):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        reset_database_button = ctk.CTkButton(
            master=self,
            text="Reset Database",
            command=lambda: self.ui_state.app_state.database.reset(),
        )
        reset_database_button.pack(pady=5)


class DirectAccessTabView(ctk.CTkTabview):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state
        self.add("Customers")
        self.add("Properties")
        self.add("Bookings")
        self.add("Services")
        self.add("Payments")
        self.add("Settings")
        self.set("Customers")  # Set the default tab

        self.customers_tab = CustomerTab(
            ui_state=self.ui_state, master=self.tab("Customers")
        )
        self.customers_tab.pack(expand=True, fill="both")

        self.properties_tab = PropertyTab(
            ui_state=self.ui_state, master=self.tab("Properties")
        )
        self.properties_tab.pack(expand=True, fill="both")

        self.bookings_tab = BookingTab(
            ui_state=self.ui_state, master=self.tab("Bookings")
        )
        self.bookings_tab.pack(expand=True, fill="both")

        self.services_tab = ServiceTab(
            ui_state=self.ui_state, master=self.tab("Services")
        )
        self.services_tab.pack(expand=True, fill="both")

        self.payments_tab = PaymentTab(
            ui_state=self.ui_state, master=self.tab("Payments")
        )
        self.payments_tab.pack(expand=True, fill="both")

        self.settings_tab = SettingsTab(
            ui_state=self.ui_state, master=self.tab("Settings")
        )
        self.settings_tab.pack(expand=True, fill="both")


class CreateCustomerForm(ctk.CTkFrame):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

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
            self.ui_state.err("All fields are required.")
            return

        customer_model = CustomerModel(-1, first_name, last_name, email, phone)
        if self.ui_state.app_state.database.add_customer(customer_model):
            self.ui_state.info("Customer created successfully.")
            self.clear_fields()
        else:
            self.ui_state.err(
                f"Failed to create customer: {self.ui_state.app_state.database.last_error}"
            )

    def clear_fields(self):
        self.first_name_entry.delete(0, "end")
        self.last_name_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")


class CreatePropertyForm(ctk.CTkFrame):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

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
            self.ui_state.err(
                "Street Number, Street Name, City, and Post Code are required."
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
        if self.ui_state.app_state.database.add_property(property_model):
            self.ui_state.info("Property created successfully.")
            self.clear_fields()
        else:
            self.ui_state.err(
                f"Failed to create property: {self.ui_state.app_state.database.last_error}"
            )

    def clear_fields(self):
        self.street_number_entry.delete(0, "end")
        self.unit_entry.delete(0, "end")
        self.street_name_entry.delete(0, "end")
        self.city_entry.delete(0, "end")
        self.post_code_entry.delete(0, "end")


class CreateBookingForm(ctk.CTkScrollableFrame):
    chosen_services: set[ServiceModel]

    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.splitter = ctk.CTkFrame(master=self)

        self.customer_search = SearchbarWithCompletion(
            title="Customer",
            search_fn=self.ui_state.app_state.database.search_customers,
            on_choose=self.on_customer_choose,
            master=self.splitter,
        )
        self.customer_search.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.property_search = SearchbarWithCompletion(
            title="Property",
            search_fn=self.ui_state.app_state.database.search_properties,
            on_choose=self.on_property_choose,
            master=self.splitter,
        )
        self.property_search.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        self.services_frame = ctk.CTkFrame(master=self.splitter)
        self.services_frame.grid(row=0, column=2, sticky="ew", padx=10, pady=10)

        self.chosen_services = set([])
        self.services_search = SearchbarWithCompletion(
            title="Service",
            search_fn=self.ui_state.app_state.database.search_services,
            on_choose=self.on_service_choose,
            master=self.services_frame,
        )
        self.services_search.pack(expand=True, fill="x", padx=10, pady=10)

        self.splitter.pack(expand=True, fill="x", padx=10, pady=10)
        self.splitter.columnconfigure(0, weight=1)
        self.splitter.columnconfigure(1, weight=1)
        self.splitter.columnconfigure(2, weight=1)

        self.info_label = ctk.CTkLabel(
            master=self,
            text="Select a customer and property, then choose a date and time (YYYY-MM-DD HH:MM). Must be in the future.",
        )

        self.when_entry = DatetimeValidatedEntry(
            master=self, placeholder_text="Datetime"
        )
        self.when_entry.pack(expand=True)

        self.service_info_label = ctk.CTkLabel(
            master=self,
            text="Selected services:",
        )
        self.service_info_label.pack(pady=5)
        self.services_list = ctk.CTkScrollableFrame(master=self)
        self.services_list.pack(expand=True, fill="x")

        self.submit_button = ctk.CTkButton(
            master=self, text="Submit", command=self.submit
        )
        self.submit_button.pack(pady=5)

    def on_customer_choose(self, customer_name):
        pass

    def on_property_choose(self, property_name):
        pass

    def on_service_choose(self, service_model: ServiceModel):
        if service_model in self.chosen_services:
            self.chosen_services.remove(service_model)
        else:
            self.chosen_services.add(service_model)
        self.services_search.clear_selection()

        self.update_selected_services()

    def update_selected_services(self):
        for widget in self.services_list.winfo_children():
            widget.destroy()

        for service in self.chosen_services:
            service_label = ctk.CTkLabel(
                master=self.services_list,
                text=service.name,
            )
            service_label.pack(fill="x", padx=5, pady=2)

    def submit(self):
        customer_model: CustomerModel = self.customer_search.selected
        property_model: PropertyModel = self.property_search.selected
        when = self.when_entry.valid_time

        if customer_model is None or property_model is None or when is None:
            self.ui_state.err("All fields are required.")
            return

        # check if it's in the future
        if when <= datetime.now():
            self.ui_state.err("The date and time must be in the future.")
            return

        # check if it has at least one service
        if len(self.chosen_services) == 0:
            self.ui_state.err("At least one service must be selected.")
            return

        booking_model = BookingModel(-1, customer_model.id, property_model.id, when)
        if self.ui_state.app_state.database.add_booking(booking_model):
            self.ui_state.info("Booking created successfully.")
            self.clear_fields()

            # Add the services to the booking
            for service in self.chosen_services:
                booking_service_model = BookingServiceModel(
                    booking_id=booking_model.id,
                    service_id=service.id,
                    completed=False,
                )
                if (
                    self.ui_state.app_state.database.add_booking_service(
                        booking_service_model
                    )
                    == False
                ):
                    self.ui_state.err(
                        f"Failed to add service {service.name} to booking: {self.ui_state.app_state.database.last_error}"
                    )
        else:
            self.ui_state.err(
                f"Failed to create booking: {self.ui_state.app_state.database.last_error}"
            )

    def clear_fields(self):
        self.customer_search.clear_selection()
        self.property_search.clear_selection()
        self.when_entry.clear()


class BookingManager(ctk.CTkFrame):
    # left hand scrolling search, right hand side with info about booking with list of services
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.search_bar = SearchbarWithCompletion(
            title="Search Bookings",
            search_fn=self.search_bookings,
            on_choose=self.on_booking_choose,
            colour_fn=self.colour_fn,
            master=self,
        )
        self.search_bar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.booking_info_frame = ctk.CTkFrame(master=self)
        self.booking_info_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.topbar_booking_info = ctk.CTkFrame(master=self.booking_info_frame)
        self.topbar_booking_info.pack(fill="x", padx=10, pady=10)

        self.booking_name = ctk.CTkLabel(
            master=self.topbar_booking_info, text="Unselected"
        )
        self.booking_name.pack(side="left", padx=10)

        self.booking_delete_button = ctk.CTkButton(
            master=self.topbar_booking_info,
            text="Delete Booking",
            command=lambda: self.remove_selected(),
        )
        self.booking_delete_button.pack(side="right", padx=10)

        self.booking_services_completion_text = ctk.CTkLabel(
            master=self.topbar_booking_info,
            text="",
        )
        self.booking_services_completion_text.pack(side="right", padx=10)

        self.booking_price_text = ctk.CTkLabel(
            master=self.topbar_booking_info,
            text="",
        )
        self.booking_price_text.pack(side="right", padx=10)

        self.booking_description = ctk.CTkLabel(
            master=self.booking_info_frame, text="Select a booking to see details."
        )
        self.booking_description.pack(pady=10)

        self.booking_services_list = ctk.CTkScrollableFrame(
            master=self.booking_info_frame
        )
        self.booking_services_list.pack(expand=True, fill="both", padx=10, pady=10)

        self.current_booking = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=5)

        self.ui_state.app_state.database.bookings_changed.connect(
            self.update_current_booking
        )
        self.ui_state.app_state.database.booking_services_changed.connect(
            self.update_current_booking
        )

    def search_bookings(self, query: str):
        """
        Searches for bookings based on the query and returns a list of booking models.
        """
        bookings = self.ui_state.app_state.database.search_bookings(query)
        for booking in bookings:
            booking.assure()
        return bookings

    def on_booking_choose(self, booking_model: BookingModel):
        self.current_booking = booking_model

        self.update_current_booking()

    def colour_fn(self, booking_model: BookingModel):
        """
        Returns a colour based on the booking's completion status.
        """
        is_completed = self.ui_state.app_state.database.is_booking_completed(
            booking_model.id
        )
        needs_payment = self.ui_state.app_state.database.booking_has_pending_payments(
            booking_model.id
        )
        if is_completed:
            if needs_payment:
                return "orange"
            return "green"
        return "red"

    def update_current_booking(self):
        self.search_bar.on_search()
        if self.current_booking is None:
            self.booking_name.configure(text="Unselected")
            self.booking_description.configure(text="Select a booking to see details.")
            for widget in self.booking_services_list.winfo_children():
                widget.destroy()

            self.booking_delete_button.configure(state="disabled")
            self.booking_services_completion_text.configure(text="")
            self.booking_price_text.configure(text="")

            return

        self.booking_name.configure(text=f"Booking ID: {self.current_booking.id}")
        self.booking_delete_button.configure(state="normal")

        customer_model = self.ui_state.app_state.database.get_customer_by_id(
            self.current_booking.customer_id
        )
        property_model = self.ui_state.app_state.database.get_property_by_id(
            self.current_booking.property_id
        )
        datetime_str = self.current_booking.when.strftime("%Y-%m-%d %H:%M")

        self.booking_description.configure(
            text=f"Customer: {customer_model}\n"
            f"Property: {property_model}\n"
            f"When: {datetime_str}"
        )

        # Clear previous services
        for widget in self.booking_services_list.winfo_children():
            widget.destroy()

        # Load services for the current booking
        booking_services = (
            self.ui_state.app_state.database.get_booking_services_by_booking_id(
                self.current_booking.id
            )
        )

        if not booking_services:
            self.booking_services_list.pack_forget()
            self.booking_description.configure(
                text=f"No services found for booking ID: {self.current_booking.id}"
            )
            return

        total_services = len(booking_services)
        completed_services = sum(1 for service in booking_services if service.completed)
        for service_model in booking_services:
            service = self.ui_state.app_state.database.get_service_by_id(
                service_model.service_id
            )
            if service:
                service_label_button = ctk.CTkButton(
                    master=self.booking_services_list,
                    text=f"{service.name} - {'Completed' if service_model.completed else 'Pending'}",
                    command=lambda sm=service_model: self.ui_state.app_state.database.toggle_booking_service_completion(
                        sm.booking_id,
                        sm.service_id,
                    ),
                )
                service_label_button.pack(fill="x", padx=5, pady=2)

        self.booking_services_list.pack(expand=True, fill="both", padx=10, pady=10)
        self.booking_services_completion_text.configure(
            text=f"Services: {completed_services}/{total_services}"
        )

        total_paid = self.ui_state.app_state.database.get_total_payments_for_booking(
            self.current_booking.id
        )
        total_price = self.ui_state.app_state.database.get_booking_total_cost(
            self.current_booking.id
        )
        self.booking_price_text.configure(
            text=f"Total Price: ${total_price:.2f}, Total Paid: ${total_paid:.2f}"
        )

    def remove_selected(self):
        if self.current_booking is None:
            self.ui_state.err("No booking selected.")
            return

        # clear services first
        if not self.ui_state.app_state.database.remove_booking_service_in_booking(
            self.current_booking.id,
        ):
            self.ui_state.err(
                f"Failed to delete booking services: {self.ui_state.app_state.database.last_error}"
            )
            return

        if self.ui_state.app_state.database.remove_booking_by_id(
            [self.current_booking.id]
        ):
            self.ui_state.info("Booking deleted successfully.")
            self.current_booking = None
            self.update_current_booking()
        else:
            self.ui_state.err(
                f"Failed to delete booking: {self.ui_state.app_state.database.last_error}"
            )

        self.search_bar.on_search()


class BookingTabView(ctk.CTkTabview):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.add("Overview")
        self.add("Create Booking")
        self.set("Overview")

        self.uncompleted_bookings_label = ctk.CTkLabel(
            master=self.tab("Overview"),
        )
        self.uncompleted_bookings_label.pack(pady=10)

        self.booking_manager = BookingManager(
            ui_state=self.ui_state, master=self.tab("Overview")
        )
        self.booking_manager.pack(expand=True, fill="both")

        self.create_booking_form = CreateBookingForm(
            ui_state=self.ui_state, master=self.tab("Create Booking")
        )
        self.create_booking_form.pack(expand=True, fill="both")

        self.on_data_updated()

        self.ui_state.app_state.database.bookings_changed.connect(self.on_data_updated)
        self.ui_state.app_state.database.booking_services_changed.connect(
            self.on_data_updated
        )

    def on_data_updated(self):
        # Update the uncompleted bookings label
        self.uncompleted_bookings_label.configure(
            text=f"Uncompleted Bookings: {self.ui_state.app_state.database.get_number_uncompleted_bookings()}"
        )


class CreateServiceForm(ctk.CTkFrame):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.name_entry = ctk.CTkEntry(master=self, placeholder_text="Service Name")
        self.name_entry.pack(pady=5)

        self.base_price_entry = ctk.CTkEntry(master=self, placeholder_text="Base Price")
        self.base_price_entry.pack(pady=5)

        self.submit_button = ctk.CTkButton(
            master=self, text="Submit", command=self.submit
        )
        self.submit_button.pack(pady=5)

    def submit(self):
        name = self.name_entry.get()
        base_price = self.base_price_entry.get()

        if not (name and base_price):
            self.ui_state.err("All fields are required.")
            return

        try:
            base_price = float(base_price)
        except ValueError:
            self.ui_state.err("Base Price must be a valid number.")
            return

        model = ServiceModel(-1, name, base_price)
        self.ui_state.app_state.database.add_service(model)

        self.ui_state.info("Service created successfully.")
        self.clear_fields()

    def clear_fields(self):
        self.name_entry.delete(0, "end")
        self.base_price_entry.delete(0, "end")


class ServiceTabView(ctk.CTkTabview):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.add("Services")
        self.add("Create Service")
        self.set("Services")

        self.services_tab = ServiceTab(
            ui_state=self.ui_state, master=self.tab("Services"), access=Access.READ
        )
        self.services_tab.pack(expand=True, fill="both")

        self.create_service_form = CreateServiceForm(
            ui_state=self.ui_state, master=self.tab("Create Service")
        )
        self.create_service_form.pack(expand=True, fill="both")


class CreatePaymentForm(ctk.CTkFrame):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.booking_search = SearchbarWithCompletion(
            title="Booking",
            search_fn=self.search_bookings,
            on_choose=self.on_booking_choose,
            master=self,
        )
        self.booking_search.pack(pady=5)

        self.amount_entry = ctk.CTkEntry(master=self, placeholder_text="Amount")
        self.amount_entry.pack(pady=5)

        self.submit_button = ctk.CTkButton(
            master=self, text="Submit", command=self.submit
        )
        self.submit_button.pack(pady=5)

    def search_bookings(self, query: str):
        """
        Searches for bookings based on the query and returns a list of booking models.
        """
        bookings = self.ui_state.app_state.database.search_bookings(query)
        for booking in bookings:
            booking.assure()
        return bookings

    def on_booking_choose(self, booking_name):
        pass

    def submit(self):
        booking_model: BookingModel = self.booking_search.selected
        amount = self.amount_entry.get()

        if booking_model is None or not amount:
            self.ui_state.err("Booking and amount are required.")
            return

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
        except ValueError:
            self.ui_state.err("Amount must be a valid number.")
            return

        model = PaymentModel(
            id=-1,
            booking_id=booking_model.id,
            amount=amount,
            payment_date=datetime.now(),
        )
        if self.ui_state.app_state.database.create_payment(model):
            self.ui_state.info("Payment created successfully.")
            self.clear_fields()
        else:
            self.ui_state.err(
                f"Failed to create payment: {self.ui_state.app_state.database.last_error}"
            )

    def clear_fields(self):
        self.booking_search.clear_selection()
        self.amount_entry.delete(0, "end")


class PaymentTabView(ctk.CTkTabview):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.add("Add")
        self.set("Add")

        # Placeholder for payment management functionality
        self.create_payment_form = CreatePaymentForm(
            ui_state=self.ui_state, master=self.tab("Add")
        )
        self.create_payment_form.pack(expand=True, fill="both")


class TabView(ctk.CTkTabview):
    def __init__(self, ui_state: UIState, master=None):
        super().__init__(master)
        self.ui_state = ui_state

        self.add("Payments")
        self.add("Customers")
        self.add("Properties")
        self.add("Bookings")
        self.add("Services")
        self.add("Direct Access")
        self.set("Payments")

        self.payments_tab = PaymentTabView(
            ui_state=self.ui_state, master=self.tab("Payments")
        )
        self.payments_tab.pack(expand=True, fill="both")

        # self.home_tab = ctk.CTkFrame(self.tab("Home"))
        # self.home_tab.pack(expand=True, fill="both")

        self.create_customer_form = CreateCustomerForm(
            ui_state=self.ui_state, master=self.tab("Customers")
        )
        self.create_customer_form.pack(expand=True, fill="both")

        self.create_property_form = CreatePropertyForm(
            ui_state=self.ui_state, master=self.tab("Properties")
        )
        self.create_property_form.pack(expand=True, fill="both")

        self.bookings = BookingTabView(
            ui_state=self.ui_state, master=self.tab("Bookings")
        )
        self.bookings.pack(expand=True, fill="both")

        self.services_tab = ServiceTabView(
            ui_state=self.ui_state, master=self.tab("Services")
        )
        self.services_tab.pack(expand=True, fill="both")

        self.direct_access_tab = DirectAccessTabView(
            ui_state=self.ui_state, master=self.tab("Direct Access")
        )
        self.direct_access_tab.pack(expand=True, fill="both")


class Ui(ctk.CTk):
    def __init__(self, app_state: State):
        super().__init__()
        self.ui_state = UIState()
        self.ui_state.app_state = app_state
        self.ui_state.notification_manager = NotificationManager(self)
        self.title("Lawn Database")
        self.geometry("800x600")
        self.iconbitmap("static/icon.ico")

        # Create UI elements here
        label = ctk.CTkLabel(master=self, text="Lawn Database")
        label.pack(pady=20)

        # self.tab_view = TabView(ui_state=self.ui_state, master=self)
        # self.tab_view.pack(expand=True, fill="both")

        self.tab_view = TabView(ui_state=self.ui_state, master=self)
        self.tab_view.pack(expand=True, fill="both")
