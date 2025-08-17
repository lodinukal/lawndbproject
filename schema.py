from datetime import date
from pydantic import BaseModel, EmailStr


class DbModel(BaseModel):
    id: int


class Person(DbModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    is_employee: bool
    hashed_password: str

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the person.
        """
        return f"{self.first_name} {self.last_name} ({'Employee' if self.is_employee else 'Customer'})"


class Property(DbModel):
    street_address: str
    city: str
    state: str
    post_code: str

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the property.
        """
        return f"{self.street_address}, {self.city}, {self.state}, {self.post_code}"


class Booking(DbModel):
    person_id: int
    property_id: int
    booking_date: date

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the booking.
        """
        return f"Booking {self.id} for {self.person_id} at {self.property_id} on {self.booking_date}"


class Service(DbModel):
    id: str
    description: str
    price: float

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the service.
        """
        return f"{self.id} - {self.description} (${self.price:.2f})"


class BookingService(DbModel):
    booking_id: int
    service_id: str
    # in minutes
    duration: int
    completed: bool

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the booking service.
        """
        return f"BookingService {self.id} - Booking {self.booking_id} - Service {self.service_id} - Duration {self.duration} minutes - Completed {self.completed}"


class Payment(DbModel):
    booking_id: int
    amount: float
    payment_date: date

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the payment.
        """
        return f"Payment {self.id} - Booking {self.booking_id} - Amount ${self.amount:.2f} - Date {self.payment_date}"


class Roster(DbModel):
    person_id: int
    booking_service_id: int

    def __str__(self) -> str:
        """
        Returns a nicely formatted string representation of the roster.
        """
        return f"Roster {self.id} - Person {self.person_id} - BookingService {self.booking_service_id}"
