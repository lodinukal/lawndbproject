from enum import Enum
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import Tuple

from util import Signal


# -1 id means transient object


class Access(Enum):
    READ = "read"
    WRITE = "write"


@dataclass
class CustomerModel:
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str

    def is_transient(self) -> bool:
        return self.id == -1

    def to_list(self) -> list:
        return [self.id, self.first_name, self.last_name, self.email, self.phone]

    def assure(self):
        self.id = int(self.id)
        if isinstance(self.phone, str):
            self.phone = self.phone.strip()
        if isinstance(self.email, str):
            self.email = self.email.strip()
        if not self.first_name:
            self.first_name = "First name"
        if not self.last_name:
            self.last_name = "Last name"

    def __repr__(self) -> str:
        """
        Returns a nicely formatted string representation of the customer.
        """
        return f"{self.first_name} {self.last_name} ({self.email}, {self.phone})"


@dataclass
class PropertyModel:
    id: int
    street_number: int
    unit: str
    street_name: str
    city: str
    post_code: str

    def is_transient(self) -> bool:
        return self.id == -1

    def to_list(self) -> list:
        return [
            self.id,
            self.street_number,
            self.unit,
            self.street_name,
            self.city,
            self.post_code,
        ]

    def assure(self):
        self.id = int(self.id)
        self.street_number = int(self.street_number)
        if self.unit is None:
            self.unit = ""
        if isinstance(self.post_code, str):
            self.post_code = int(self.post_code)

    def __repr__(self) -> str:
        """
        Returns a nicely formatted string representation of the property.
        """
        unit_str = f"Unit {self.unit}, " if self.unit else ""
        return f"{self.street_number} {unit_str}{self.street_name}, {self.city}, {self.post_code}"


@dataclass
class BookingModel:
    id: int
    customer_id: int
    property_id: int
    when: datetime

    def is_transient(self) -> bool:
        return self.id == -1 or self.customer_id == -1 or self.property_id == -1

    def to_list(self) -> list:
        when_datetime = (
            datetime.fromisoformat(self.when)
            if isinstance(self.when, str)
            else self.when
        )

        return [
            self.id,
            self.customer_id,
            self.property_id,
            when_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        ]

    def assure(self):
        self.id = int(self.id)
        self.customer_id = int(self.customer_id)
        self.property_id = int(self.property_id)
        if isinstance(self.when, str):
            self.when = datetime.fromisoformat(self.when)

    def __repr__(self) -> str:
        """
        Returns a nicely formatted string representation of the booking.
        """
        return f"Booking {self.id} for Customer {self.customer_id} at Property {self.property_id} on {self.when.strftime('%Y-%m-%d %H:%M:%S')}"


@dataclass
class ServiceModel:
    id: int
    name: str
    base_price: float

    def is_transient(self) -> bool:
        return self.id == -1

    def to_list(self) -> list:
        return [self.id, self.name, self.base_price]

    def assure(self):
        self.id = int(self.id)
        if isinstance(self.name, str):
            self.name = self.name.strip()
        if isinstance(self.base_price, str):
            try:
                self.base_price = float(self.base_price)
            except ValueError:
                self.base_price = 0.0

    def __repr__(self) -> str:
        """
        Returns a nicely formatted string representation of the service.
        """
        self.assure()
        return f"Service {self.id}: {self.name} at base price ${self.base_price:.2f}"

    def __hash__(self):
        return hash(self.id)


@dataclass
class BookingServiceModel:
    booking_id: int
    service_id: int
    completed: bool

    def is_transient(self) -> bool:
        return self.booking_id == -1 or self.service_id == -1

    def to_list(self) -> list:
        return [
            self.booking_id,
            self.service_id,
            self.completed,
        ]

    def assure(self):
        self.booking_id = int(self.booking_id)
        self.service_id = int(self.service_id)
        if not isinstance(self.completed, bool):
            self.completed = bool(self.completed)


@dataclass
class PaymentModel:
    id: int
    booking_id: int
    amount: float
    payment_date: datetime

    def is_transient(self) -> bool:
        return self.id == -1 or self.booking_id == -1

    def to_list(self) -> list:
        payment_date_str = (
            self.payment_date.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(self.payment_date, datetime)
            else self.payment_date
        )
        return [self.id, self.booking_id, self.amount, payment_date_str]

    def assure(self):
        self.id = int(self.id)
        self.booking_id = int(self.booking_id)
        if isinstance(self.amount, str):
            try:
                self.amount = float(self.amount)
            except ValueError:
                self.amount = 0.0
        if isinstance(self.payment_date, str):
            self.payment_date = datetime.fromisoformat(self.payment_date)


class Database:
    customers_changed: Signal
    properties_changed: Signal
    bookings_changed: Signal
    services_changed: Signal
    booking_services_changed: Signal
    payments_changed: Signal

    last_error: str = ""

    def __init__(self, db_name="lawn_database.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.customers_changed = Signal()
        self.properties_changed = Signal()
        self.bookings_changed = Signal()
        self.services_changed = Signal()
        self.booking_services_changed = Signal()
        self.payments_changed = Signal()
        self.last_error = ""

        self.cursor.execute("PRAGMA foreign_keys = ON")
        # self.connection.set_trace_callback(print)

        self.create_tables()

    def reset(self):
        with open("static/drop_tables.sql", "r") as file:
            sql_script = file.read()

        self.cursor.executescript(sql_script)
        self.connection.commit()

        self.create_tables()

    def create_tables(self):
        with open("static/create_tables.sql", "r") as file:
            sql_script = file.read()

        self.cursor.executescript(sql_script)
        self.connection.commit()

        self.customers_changed.emit()
        self.properties_changed.emit()

    def close(self):
        self.connection.close()

    def get_bookings_from_to(self, from_date: datetime, to_date: datetime):
        query = """
        SELECT * FROM Booking
        WHERE date >= ? AND date <= ?
        """
        self.cursor.execute(query, (from_date, to_date))
        return self.cursor.fetchall()

    def add_customer(self, model: CustomerModel) -> bool:
        """
        Adds a customer to the database and returns True if successful, False otherwise.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will return False. If successful, the model's id will be updated.
        """
        if not model.is_transient():
            return False
        query = """
        INSERT INTO Customer (first_name, last_name, email, phone_number)
        VALUES (?, ?, ?, ?)
        """
        try:
            self.cursor.execute(
                query, (model.first_name, model.last_name, model.email, model.phone)
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()
        model.id = self.cursor.lastrowid

        success = model.id != -1
        if success:
            self.customers_changed.emit()

        return success

    def add_or_update_customer(self, model: CustomerModel) -> bool:
        """
        Adds a new customer or updates an existing one in the database.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will update the existing customer with the same id.
        Returns True if successful, False otherwise.
        """
        if model.is_transient():
            return self.add_customer(model)

        query = """
        INSERT INTO Customer (id, first_name, last_name, email, phone_number)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            email = excluded.email,
            phone_number = excluded.phone_number
        """
        try:
            self.cursor.execute(
                query,
                (model.id, model.first_name, model.last_name, model.email, model.phone),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.customers_changed.emit()

        return success

    def get_customer_by_id(self, customer_id: int) -> CustomerModel | None:
        """
        Returns a customer by id or None if not found.
        """
        query = "SELECT * FROM Customer WHERE id = ?"
        self.cursor.execute(query, (customer_id,))
        row = self.cursor.fetchone()
        if row:
            return CustomerModel(*row)
        return None

    def remove_customer_by_id(self, ids: list[int]) -> bool:
        """
        Removes a customer by id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM Customer WHERE id IN ({})".format(
            ",".join("?" for _ in ids)
        )
        self.cursor.execute(query, ids)
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.customers_changed.emit()

        return success

    def remove_customer(self, model: CustomerModel) -> bool:
        """
        Removes a customer model from the database and returns True if successful and removes the id from the model, False otherwise.
        """
        if model.is_transient():
            return False
        success = self.remove_customer_by_id(model.id)
        if success:
            model.id = -1
        return success

    def get_all_customers(self, page: int, page_size: int = 10):
        """
        Returns a list of all customers in the database, paginated.
        """
        offset = (page - 1) * page_size
        query = "SELECT * FROM Customer LIMIT ? OFFSET ?"
        self.cursor.execute(query, (page_size, offset))
        rows = self.cursor.fetchall()
        return [CustomerModel(*row) for row in rows]

    def get_num_customer_pages(self, page_size: int = 10) -> int:
        """
        Returns the number of pages of customers in the database.
        """
        query = "SELECT COUNT(*) FROM Customer"
        self.cursor.execute(query)
        total_customers = self.cursor.fetchone()[0]
        return (total_customers + page_size - 1) // page_size

    # properties
    def add_property(self, model: PropertyModel) -> bool:
        """
        Adds a property to the database and returns True if successful, False otherwise.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will return False. If successful, the model's id will be updated.
        """
        if not model.is_transient():
            return False
        query = """
        INSERT INTO Property (street_number, street_name, city, post_code, unit)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            self.cursor.execute(
                query,
                (
                    model.street_number,
                    model.street_name,
                    model.city,
                    model.post_code,
                    model.unit,
                ),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()
        model.id = self.cursor.lastrowid

        success = model.id != -1
        if success:
            self.properties_changed.emit()

        return success

    def get_all_properties(self, page: int, page_size: int = 10):
        """
        Returns a list of all properties in the database, paginated.
        """
        offset = (page - 1) * page_size
        query = "SELECT * FROM Property LIMIT ? OFFSET ?"
        self.cursor.execute(query, (page_size, offset))
        rows = self.cursor.fetchall()
        return [PropertyModel(*row) for row in rows]

    def get_num_property_pages(self, page_size: int = 10) -> int:
        """
        Returns the number of pages of properties in the database.
        """
        query = "SELECT COUNT(*) FROM Property"
        self.cursor.execute(query)
        total_properties = self.cursor.fetchone()[0]
        return (total_properties + page_size - 1) // page_size

    def remove_property_by_id(self, ids: list[int]) -> bool:
        """
        Removes a property by id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM Property WHERE id IN ({})".format(
            ",".join("?" for _ in ids)
        )
        self.cursor.execute(query, ids)
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.properties_changed.emit()
        return success

    def remove_property(self, model: PropertyModel) -> bool:
        """
        Removes a property model from the database and returns True if successful and removes the id from the model, False otherwise.
        """
        if model.is_transient():
            return False
        success = self.remove_property_by_id(model.id)
        if success:
            model.id = -1
        return success

    def add_or_update_property(self, model: PropertyModel) -> bool:
        """
        Adds a new property to the database or updates an existing one.
        """
        if model.is_transient():
            return self.add_property(model)
        else:
            return self.update_property(model)

    def update_property(self, model: PropertyModel) -> bool:
        """
        Updates an existing property in the database.
        Returns True if successful, False otherwise.
        """
        query = """
        INSERT INTO Property (id, street_number, street_name, city, post_code, unit)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            street_number = excluded.street_number,
            street_name = excluded.street_name,
            city = excluded.city,
            post_code = excluded.post_code,
            unit = excluded.unit
        """
        try:
            self.cursor.execute(
                query,
                (
                    model.id,
                    model.street_number,
                    model.street_name,
                    model.city,
                    model.post_code,
                    model.unit,
                ),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.properties_changed.emit()

        return success

    def get_property_by_id(self, property_id: int) -> PropertyModel | None:
        """
        Returns a property by id or None if not found.
        """
        query = "SELECT * FROM Property WHERE id = ?"
        self.cursor.execute(query, (property_id,))
        row = self.cursor.fetchone()
        if row:
            return PropertyModel(*row)
        return None

    # bookings
    def add_booking(self, model: BookingModel) -> bool:
        """
        Adds a booking to the database and returns True if successful, False otherwise.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will return False. If successful, the model's id will be updated.
        """
        if not model.is_transient():
            return False
        query = """
        INSERT INTO Booking (customer_id, property_id, date_time)
        VALUES (?, ?, ?)
        """
        try:
            self.cursor.execute(
                query, (model.customer_id, model.property_id, model.when)
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()
        model.id = self.cursor.lastrowid

        success = model.id != -1
        if success:
            self.bookings_changed.emit()

        return success

    def get_all_bookings(self, page: int, page_size: int = 10):
        """
        Returns a list of all bookings in the database, paginated.
        """
        offset = (page - 1) * page_size
        query = "SELECT * FROM Booking LIMIT ? OFFSET ?"
        self.cursor.execute(query, (page_size, offset))
        rows = self.cursor.fetchall()
        return [BookingModel(*row) for row in rows]

    def get_num_booking_pages(self, page_size: int = 10) -> int:
        """
        Returns the number of pages of bookings in the database.
        """
        query = "SELECT COUNT(*) FROM Booking"
        self.cursor.execute(query)
        total_bookings = self.cursor.fetchone()[0]
        return (total_bookings + page_size - 1) // page_size

    def remove_booking_by_id(self, ids: list[int]) -> bool:
        """
        Removes a booking by id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM Booking WHERE id IN ({})".format(
            ",".join("?" for _ in ids)
        )
        self.cursor.execute(query, ids)
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.bookings_changed.emit()
        return success

    def remove_booking(self, model: BookingModel) -> bool:
        """
        Removes a booking model from the database and returns True if successful and removes the id from the model, False otherwise.
        """
        if model.is_transient():
            return False
        success = self.remove_booking_by_id(model.id)
        if success:
            model.id = -1
        return success

    def add_or_update_booking(self, model: BookingModel) -> bool:
        """
        Adds a new booking to the database or updates an existing one.
        """
        if model.is_transient():
            return self.add_booking(model)
        else:
            return self.update_booking(model)

    def update_booking(self, model: BookingModel) -> bool:
        """
        Updates an existing booking in the database.
        Returns True if successful, False otherwise.
        """
        query = """
        INSERT INTO Booking (id, customer_id, property_id, when)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            customer_id = excluded.customer_id,
            property_id = excluded.property_id,
            when = excluded.when
        """
        try:
            self.cursor.execute(
                query,
                (model.id, model.customer_id, model.property_id, model.when),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.bookings_changed.emit()

        return success

    def get_booking_by_id(self, booking_id: int) -> BookingModel | None:
        """
        Returns a booking by id or None if not found.
        """
        query = "SELECT * FROM Booking WHERE id = ?"
        self.cursor.execute(query, (booking_id,))
        row = self.cursor.fetchone()
        if row:
            return BookingModel(*row)
        return None

    def get_bookings_by_customer_id(self, customer_id: int):
        """
        Returns a list of bookings for a specific customer by their id.
        """
        query = "SELECT * FROM Booking WHERE customer_id = ?"
        self.cursor.execute(query, (customer_id,))
        rows = self.cursor.fetchall()
        return [BookingModel(*row) for row in rows]

    def get_bookings_by_property_id(self, property_id: int):
        """
        Returns a list of bookings for a specific property by its id.
        """
        query = "SELECT * FROM Booking WHERE property_id = ?"
        self.cursor.execute(query, (property_id,))
        rows = self.cursor.fetchall()
        return [BookingModel(*row) for row in rows]

    # services
    def add_service(self, model: ServiceModel) -> bool:
        """
        Adds a service to the database and returns True if successful, False otherwise.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will return False. If successful, the model's id will be updated.
        """
        if not model.is_transient():
            return False
        query = """
        INSERT INTO Service (name, base_price)
        VALUES (?, ?)
        """
        try:
            self.cursor.execute(query, (model.name, model.base_price))
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()
        model.id = self.cursor.lastrowid

        success = model.id != -1
        if success:
            self.services_changed.emit()

        return success

    def update_service(self, model: ServiceModel) -> bool:
        """
        Updates an existing service in the database.
        Returns True if successful, False otherwise.
        """
        query = """
        INSERT INTO Service (id, name, base_price)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            base_price = excluded.base_price
        """
        try:
            self.cursor.execute(
                query,
                (model.id, model.name, model.base_price),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.services_changed.emit()

        return success

    def get_service_by_id(self, service_id: int) -> ServiceModel | None:
        """
        Returns a service by id or None if not found.
        """
        query = "SELECT * FROM Service WHERE id = ?"
        self.cursor.execute(query, (service_id,))
        row = self.cursor.fetchone()
        if row:
            return ServiceModel(*row)
        return None

    def get_all_services(self, page: int, page_size: int = 10):
        """
        Returns a list of all services in the database, paginated.
        """
        offset = (page - 1) * page_size
        query = "SELECT * FROM Service LIMIT ? OFFSET ?"
        self.cursor.execute(query, (page_size, offset))
        rows = self.cursor.fetchall()
        return [ServiceModel(*row) for row in rows]

    def get_num_service_pages(self, page_size: int = 10) -> int:
        """
        Returns the number of pages of services in the database.
        """
        query = "SELECT COUNT(*) FROM Service"
        self.cursor.execute(query)
        total_services = self.cursor.fetchone()[0]
        return (total_services + page_size - 1) // page_size

    def remove_service_by_id(self, ids: list[int]) -> bool:
        """
        Removes a service by id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM Service WHERE id IN ({})".format(
            ",".join("?" for _ in ids)
        )
        self.cursor.execute(query, ids)
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.services_changed.emit()
        return success

    def remove_service(self, model: ServiceModel) -> bool:
        """
        Removes a service model from the database and returns True if successful and removes the id from the model, False otherwise.
        """
        if model.is_transient():
            return False
        success = self.remove_service_by_id(model.id)
        if success:
            model.id = -1
        return success

    def add_or_update_service(self, model: ServiceModel) -> bool:
        """
        Adds a new service to the database or updates an existing one.
        """
        if model.is_transient():
            return self.add_service(model)
        else:
            return self.update_service(model)

    # booking services
    def add_booking_service(self, model: BookingServiceModel) -> bool:
        """
        Adds a booking service to the database and returns True if successful, False otherwise.
        If the model has a booking_id or service_id of -1, it is considered transient and will not be added.
        It will return False. If successful, the model's booking_id will be updated
        """
        if model.is_transient():
            return False
        query = """
        INSERT INTO BookingService (booking_id, service_id, completed)
        VALUES (?, ?, ?)
        """
        try:
            self.cursor.execute(
                query,
                (
                    model.booking_id,
                    model.service_id,
                    model.completed,
                ),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        except sqlite3.DatabaseError as e:
            self.last_error = str(e)
            return False
        model.booking_id = self.cursor.lastrowid
        self.connection.commit()

        success = model.booking_id != -1 and model.service_id != -1
        if success:
            self.booking_services_changed.emit()
            self.bookings_changed.emit()

        return success

    def get_all_booking_services(self, page: int, page_size: int = 10):
        """
        Returns a list of all booking services in the database, paginated.
        """
        offset = (page - 1) * page_size
        query = "SELECT * FROM BookingService LIMIT ? OFFSET ?"
        self.cursor.execute(query, (page_size, offset))
        rows = self.cursor.fetchall()
        return [BookingServiceModel(*row) for row in rows]

    def get_num_booking_service_pages(self, page_size: int = 10) -> int:
        """
        Returns the number of pages of booking services in the database.
        """
        query = "SELECT COUNT(*) FROM BookingService"
        self.cursor.execute(query)
        total_booking_services = self.cursor.fetchone()[0]
        return (total_booking_services + page_size - 1) // page_size

    def remove_booking_service_in_booking(self, booking_id: int) -> bool:
        """
        Removes all booking services for a specific booking by its id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM BookingService WHERE booking_id = ?"
        self.cursor.execute(query, (booking_id,))
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.booking_services_changed.emit()
        return success

    def remove_booking_service_by_booking_service_id(
        self, booking_id: int, service_id: int
    ) -> bool:
        """
        Removes a booking service by booking_id and service_id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM BookingService WHERE booking_id = ? AND service_id = ?"
        self.cursor.execute(query, (booking_id, service_id))
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.booking_services_changed.emit()
        return success

    def remove_booking_service(self, model: BookingServiceModel) -> bool:
        """
        Removes a booking service model from the database and returns True if successful and removes the booking_id and service_id from the model, False otherwise.
        """
        if model.is_transient():
            return False
        success = self.remove_booking_service_by_booking_service_id(
            model.booking_id, model.service_id
        )
        if success:
            model.booking_id = -1
            model.service_id = -1
        return success

    def add_or_update_booking_service(self, model: BookingServiceModel) -> bool:
        """
        Adds a new booking service to the database or updates an existing one.
        """
        if model.is_transient():
            return self.add_booking_service(model)
        else:
            return self.update_booking_service(model)

    def update_booking_service(self, model: BookingServiceModel) -> bool:
        """
        Updates an existing booking service in the database.
        Returns True if successful, False otherwise.
        """
        query = """
        INSERT INTO BookingService (booking_id, service_id, completed)
        VALUES (?, ?, ?)
        ON CONFLICT(booking_id, service_id) DO UPDATE SET
            completed = excluded.completed
        """
        try:
            self.cursor.execute(
                query,
                (
                    model.booking_id,
                    model.service_id,
                    model.completed,
                ),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.booking_services_changed.emit()
            self.bookings_changed.emit()

        return success

    def toggle_booking_service_completion(
        self, booking_id: int, service_id: int
    ) -> bool:
        """
        Toggles the completion status of a booking service.
        """
        service = self.get_booking_service_by_booking_id_and_service_id(
            booking_id, service_id
        )
        if service:
            service.completed = not service.completed
            return self.update_booking_service(service)
        return False

    def get_booking_service_by_booking_id_and_service_id(
        self, booking_id: int, service_id: int
    ) -> BookingServiceModel | None:
        """
        Returns a booking service by booking_id and service_id or None if not found.
        """
        query = "SELECT * FROM BookingService WHERE booking_id = ? AND service_id = ?"
        self.cursor.execute(query, (booking_id, service_id))
        row = self.cursor.fetchone()
        if row:
            return BookingServiceModel(*row)
        return None

    def get_booking_services_by_booking_id(self, booking_id: int):
        """
        Returns a list of booking services for a specific booking by its id.
        """
        query = "SELECT * FROM BookingService WHERE booking_id = ?"
        self.cursor.execute(query, (booking_id,))
        rows = self.cursor.fetchall()
        return [BookingServiceModel(*row) for row in rows] if rows else []

    def get_booking_services_by_service_id(self, service_id: int):
        """
        Returns a list of booking services for a specific service by its id.
        """
        query = "SELECT * FROM BookingService WHERE service_id = ?"
        self.cursor.execute(query, (service_id,))
        rows = self.cursor.fetchall()
        return [BookingServiceModel(*row) for row in rows] if rows else []

    # special methods
    # getting the number of bookings for a customer
    def get_num_bookings_for_customer(self, customer_id: int) -> int:
        """
        Returns the number of bookings for a specific customer by their id.
        """
        query = "SELECT COUNT(*) FROM Booking WHERE customer_id = ?"
        self.cursor.execute(query, (customer_id,))
        return self.cursor.fetchone()[0]

    def get_num_bookings_for_property(self, property_id: int) -> int:
        """
        Returns the number of bookings for a specific property by its id.
        """
        query = "SELECT COUNT(*) FROM Booking WHERE property_id = ?"
        self.cursor.execute(query, (property_id,))

    def get_uncompleted_bookings(self):
        """
        Returns a list of all bookings that are not completed.
        """
        query = "SELECT * FROM Booking WHERE id IN (SELECT booking_id FROM BookingService WHERE completed = 0)"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return [BookingServiceModel(*row) for row in rows] if rows else []

    def get_uncompleted_bookings_by_customer_id(self, customer_id: int):
        """
        Returns a list of uncompleted bookings for a specific customer by their id.
        """
        query = """
        SELECT * FROM BookingService
        WHERE booking_id IN (
            SELECT id FROM Booking WHERE customer_id = ?
        ) INNER JOIN Booking ON BookingService.booking_id = Booking.id
        AND BookingService.completed = 0
        )
        """
        self.cursor.execute(query, (customer_id,))
        rows = self.cursor.fetchall()
        return [BookingServiceModel(*row) for row in rows] if rows else []

    def get_number_uncompleted_bookings(self) -> int:
        """
        Returns the number of uncompleted bookings in the database.
        """
        query = "SELECT COUNT(*) FROM Booking WHERE id IN (SELECT booking_id FROM BookingService WHERE completed = 0)"
        self.cursor.execute(query)
        return self.cursor.fetchone()[0]

    def create_payment(self, model: PaymentModel) -> bool:
        """
        Creates a payment record in the database and returns True if successful, False otherwise.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will return False. If successful, the model's id will be updated.
        """
        if not model.is_transient():
            return False
        query = """
        INSERT INTO Payment (booking_id, amount, payment_date)
        VALUES (?, ?, ?)
        """
        try:
            self.cursor.execute(
                query, (model.booking_id, model.amount, model.payment_date)
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()
        model.id = self.cursor.lastrowid

        success = model.id != -1
        if success:
            self.payments_changed.emit()
        return success

    def update_payment(self, model: PaymentModel) -> bool:
        """
        Updates an existing payment in the database.
        Returns True if successful, False otherwise.
        """
        query = """
        INSERT INTO Payment (id, booking_id, amount, payment_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            booking_id = excluded.booking_id,
            amount = excluded.amount,
            payment_date = excluded.payment_date
        """
        try:
            self.cursor.execute(
                query,
                (model.id, model.booking_id, model.amount, model.payment_date),
            )
        except sqlite3.IntegrityError as e:
            self.last_error = str(e)
            return False
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.payments_changed.emit()

        return success

    def add_or_update_payment(self, model: PaymentModel) -> bool:
        """
        Adds a new payment to the database or updates an existing one.
        If the model has an id of -1, it is considered transient and will be assigned a new id.
        Otherwise, it will update the existing payment with the same id.
        Returns True if successful, False otherwise.
        """
        if model.is_transient():
            return self.create_payment(model)
        else:
            return self.update_payment(model)

    def get_payment_by_id(self, payment_id: int) -> PaymentModel | None:
        """
        Returns a payment by id or None if not found.
        """
        query = "SELECT * FROM Payment WHERE id = ?"
        self.cursor.execute(query, (payment_id,))
        row = self.cursor.fetchone()
        if row:
            return PaymentModel(*row)
        return None

    def get_payments_by_booking_id(self, booking_id: int):
        """
        Returns a list of payments for a specific booking by its id.
        """
        query = "SELECT * FROM Payment WHERE booking_id = ?"
        self.cursor.execute(query, (booking_id,))
        rows = self.cursor.fetchall()
        return [PaymentModel(*row) for row in rows] if rows else []

    def get_all_payments(self, page: int, page_size: int = 10):
        """
        Returns a list of all payments in the database, paginated.
        """
        offset = (page - 1) * page_size
        query = "SELECT * FROM Payment LIMIT ? OFFSET ?"
        self.cursor.execute(query, (page_size, offset))
        rows = self.cursor.fetchall()
        return [PaymentModel(*row) for row in rows]

    def get_num_payment_pages(self, page_size: int = 10) -> int:
        """
        Returns the number of pages of payments in the database.
        """
        query = "SELECT COUNT(*) FROM Payment"
        self.cursor.execute(query)
        total_payments = self.cursor.fetchone()[0]
        return (total_payments + page_size - 1) // page_size

    def remove_payment_by_id(self, ids: list[int]) -> bool:
        """
        Removes a payment by id and returns True if successful, False otherwise.
        """
        query = "DELETE FROM Payment WHERE id IN ({})".format(
            ",".join("?" for _ in ids)
        )
        self.cursor.execute(query, ids)
        self.connection.commit()

        success = self.cursor.rowcount > 0
        if success:
            self.payments_changed.emit()
        return success

    def remove_payment(self, model: PaymentModel) -> bool:
        """
        Removes a payment model from the database and returns True if successful and removes the id from the model, False otherwise.
        """
        if model.is_transient():
            return False
        success = self.remove_payment_by_id([model.id])
        if success:
            model.id = -1
        return success

    def get_payments_by_customer_id(self, customer_id: int):
        """
        Returns a list of payments for a specific customer by their id.
        """
        query = """
        SELECT * FROM Payment
        WHERE booking_id IN (
            SELECT id FROM Booking WHERE customer_id = ?
        )
        """
        self.cursor.execute(query, (customer_id,))
        rows = self.cursor.fetchall()
        return [PaymentModel(*row) for row in rows] if rows else []

    def get_payments_by_property_id(self, property_id: int):
        """
        Returns a list of payments for a specific property by its id.
        """
        query = """
        SELECT * FROM Payment
        WHERE booking_id IN (
            SELECT id FROM Booking WHERE property_id = ?
        )
        """
        self.cursor.execute(query, (property_id,))
        rows = self.cursor.fetchall()
        return [PaymentModel(*row) for row in rows] if rows else []

    def get_total_payments_for_booking(self, booking_id: int) -> float:
        """
        Returns the total amount of payments for a specific booking by its id.
        """
        query = "SELECT SUM(amount) FROM Payment WHERE booking_id = ?"
        self.cursor.execute(query, (booking_id,))
        result = self.cursor.fetchone()
        return result[0] if result and result[0] is not None else 0.0

    def get_count_payments_for_booking(self, booking_id: int) -> int:
        """
        Returns the count of payments for a specific booking by its id.
        """
        query = "SELECT COUNT(*) FROM Payment WHERE booking_id = ?"
        self.cursor.execute(query, (booking_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def search_customers(
        self, search_term: str, limit: int = 10
    ) -> list[CustomerModel]:
        """
        Searches for customers by first name, last name, email, or phone number.
        Returns a list of CustomerModel objects that match the search term.
        """
        query = """
        SELECT * FROM Customer
        WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone_number LIKE ?
        LIMIT ?
        """
        search_pattern = f"%{search_term}%"
        self.cursor.execute(
            query,
            (search_pattern, search_pattern, search_pattern, search_pattern, limit),
        )
        rows = self.cursor.fetchall()
        return [CustomerModel(*row) for row in rows] if rows else []

    def search_properties(
        self, search_term: str, limit: int = 10
    ) -> list[PropertyModel]:
        """
        Searches for properties by street number, street name, city, or post code.
        Returns a list of PropertyModel objects that match the search term.
        """
        query = """
        SELECT * FROM Property
        WHERE street_number LIKE ? OR street_name LIKE ? OR city LIKE ? OR post_code LIKE ?
        LIMIT ?
        """
        search_pattern = f"%{search_term}%"
        self.cursor.execute(
            query,
            (search_pattern, search_pattern, search_pattern, search_pattern, limit),
        )
        rows = self.cursor.fetchall()
        return [PropertyModel(*row) for row in rows] if rows else []

    def search_bookings(
        self, search_term: str, limit: int = 10, time: Tuple[datetime] = (None, None)
    ) -> list[BookingModel]:
        """
        Searches for bookings by customer id or property id.
        Returns a list of BookingModel objects that match the search term.
        """
        start_time = (
            str(time[0]) if time != None and time[0] != None else "1970-01-01 00:00:00"
        )
        end_time = (
            str(time[1]) if time != None and time[1] != None else "9999-12-31 23:59:59"
        )
        query = """
        SELECT * FROM Booking
        WHERE (customer_id IN (
            SELECT id FROM Customer WHERE first_name LIKE :pattern OR last_name LIKE :pattern OR email LIKE :pattern OR phone_number LIKE :pattern
        ) OR property_id IN (
            SELECT id FROM Property WHERE street_number LIKE :pattern OR street_name LIKE :pattern OR city LIKE :pattern OR post_code LIKE :pattern
        ) OR date_time LIKE :pattern)
        AND date_time BETWEEN :start AND :end
        LIMIT :limit
        """
        search_pattern = f"%{search_term}%"
        self.cursor.execute(
            query,
            {
                "pattern": search_pattern,
                "start": start_time,
                "end": end_time,
                "limit": limit,
            },
        )
        rows = self.cursor.fetchall()
        return [BookingModel(*row) for row in rows] if rows else []

    def search_services(self, search_term: str, limit: int = 10) -> list[ServiceModel]:
        """
        Searches for services by name.
        Returns a list of ServiceModel objects that match the search term.
        """
        query = "SELECT * FROM Service WHERE name LIKE ? LIMIT ?"
        search_pattern = f"%{search_term}%"
        self.cursor.execute(query, (search_pattern, limit))
        rows = self.cursor.fetchall()
        return [ServiceModel(*row) for row in rows] if rows else []

    def is_booking_completed(self, booking_id: int) -> bool:
        """
        Checks if a booking is completed by its id.
        """
        query = """
        SELECT COUNT(*) FROM Booking WHERE id = ? AND id NOT IN (
            SELECT booking_id from BookingService WHERE completed = 0
        )
        """
        self.cursor.execute(query, (booking_id,))
        result = self.cursor.fetchone()
        return result[0] > 0

    def booking_get_paid_total_cost(self, booking_id: int) -> Tuple[float, float]:
        query = """
        /* make sure has number or 0 */
        SELECT COALESCE(payment_summary.total, 0), COALESCE(service_summary.total, 0) FROM Booking
        /* get the paid amount, could be null if there's no payments */
        LEFT JOIN (
            SELECT SUM(Payment.amount) AS total FROM Payment WHERE booking_id = :booking_id
        ) AS payment_summary
        /* get the owed total cost, shouldn't be null as at least one service should be on a booking */
        LEFT JOIN (
            SELECT SUM(base_price) AS total FROM BookingService LEFT JOIN
            Service ON BookingService.service_id = Service.id WHERE BookingService.booking_id = :booking_id
        ) AS service_summary
        """
        self.cursor.execute(query, {"booking_id": booking_id})
        result = self.cursor.fetchone()
        return result if result is not None else (0, 0)

    def booking_has_pending_payments(self, booking_id: int) -> bool:
        """
        Checks if a booking has any pending payments.
        """
        paid, total = self.booking_get_paid_total_cost(booking_id)
        return paid < total
