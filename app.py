from database import Database
from datetime import datetime

from typing import Optional

from fakes import generate_customer, generate_property, generate_booking

from util import Signal


class State:
    database: Database

    def __init__(self, database: Database):
        self.database = database

    def add_fake_customer(self) -> Optional[int]:
        """
        returns the id of the customer or -1 if it failed to add
        """
        new_customer_model = generate_customer()
        if self.database.add_customer(new_customer_model):
            return new_customer_model.id
        return None

    def add_fake_property(self) -> Optional[int]:
        """
        returns the id of the property or -1 if it failed to add
        """
        new_property_model = generate_property()
        if self.database.add_property(new_property_model):
            return new_property_model.id
        return None

    def add_fake_booking(self, customer_id: int, property_id: int) -> Optional[int]:
        """
        returns the id of the booking or -1 if it failed to add
        """
        new_booking_model = generate_booking(customer_id, property_id)
        if self.database.add_booking(new_booking_model):
            return new_booking_model.id
        return None
