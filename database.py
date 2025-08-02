import sqlite3
from datetime import datetime
from dataclasses import dataclass

from util import Signal


# -1 id means transient object


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


class Database:
    customers_changed: Signal
    properties_changed: Signal
    bookings_changed: Signal

    last_error: str = ""

    def __init__(self, db_name="lawn_database.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.customers_changed = Signal()
        self.properties_changed = Signal()
        self.bookings_changed = Signal()
        self.last_error = ""

        self.cursor.execute("PRAGMA foreign_keys = ON")

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
        print(property_id)
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
