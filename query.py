from dataclasses import dataclass
from datetime import date
import inspect
from sqlite3 import Row
import traceback
from typing import Callable, TypeVar

from pydantic import ValidationError
import pydantic
import database
import schema
import scripts

T = TypeVar("T")


@dataclass
class Result[T]:
    error: str | None
    value: list[T] | None
    lastrowid: int | None = None

    def one(self) -> T | None:
        if self.value and len(self.value) == 1:
            return self.value[0]
        return None

    def unwrap_or(self, default: list[T]) -> list[T]:
        return self.value if self.value else (default or [])

    def unwrap_one_or(self, default: T) -> T:
        return self.value[0] if self.value and len(self.value) == 1 else default

    def unwrap_or_else(self, fallback: Callable[[], list[T]]) -> list[T]:
        return self.value if self.value else fallback()

    def unwrap_one_or_else(self, fallback: Callable[[], T]) -> T:
        return self.value[0] if self.value and len(self.value) == 1 else fallback()


def debug_passthrough(transformer) -> T:
    def wrapper(*args: any, **kwargs: any) -> T:
        result = transformer(*args, **kwargs)
        print("Debug Passthrough:", args, kwargs, "->", result)
        return result

    return wrapper


def __execute(
    transformer: Callable[[Row], T], script: str, params: dict = None
) -> Result[T]:
    result = database.execute(script, params)
    # transformer = debug_passthrough(transformer)
    try:
        new_data = (
            list(map(lambda row: transformer(**row), result.data))
            if result.data
            else []
        )
        return Result[T](error=result.error, value=new_data, lastrowid=result.lastrowid)
    except ValidationError as e:
        print(inspect.stack()[1][3])
        print("Error occurred:", e.json())
        print(traceback.format_exc(limit=10))
        return Result[T](error=str(e), value=[])


def passthrough(*args: any, **kwargs: any) -> T:
    return args[0] if args else None


def extract_count_int(count: int) -> int | None:
    return count if count is not None else None


##
## Person management
##


def create_person(
    username: str,
    first_name: str,
    last_name: str,
    email: str,
    phone_number: str,
    hashed_password: str,
) -> Result[schema.Person]:
    return __execute(
        schema.Person,
        scripts.CREATE_PERSON,
        {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone_number,
            "hashed_password": hashed_password,
        },
    )


def delete_person(person_id: int) -> Result[None]:
    return __execute(passthrough, scripts.DELETE_PERSON, {"person_id": person_id})


def get_person_by_id(person_id: int) -> Result[schema.Person]:
    return __execute(schema.Person, scripts.GET_PERSON_BY_ID, {"person_id": person_id})


def get_person_by_email(email: str) -> Result[schema.Person]:
    return __execute(schema.Person, scripts.GET_PERSON_BY_EMAIL, {"email": email})


def get_person_by_username(username: str) -> Result[schema.Person]:
    return __execute(
        schema.Person, scripts.GET_PERSON_BY_USERNAME, {"username": username}
    )


def login_person(username: str, hashed_password: str) -> Result[schema.Person]:
    return __execute(
        schema.Person,
        scripts.LOGIN_PERSON,
        {"username": username, "hashed_password": hashed_password},
    )


def set_person_employee(person_id: int) -> Result[None]:
    return __execute(passthrough, scripts.SET_PERSON_EMPLOYEE, {"person_id": person_id})


def set_person_customer(person_id: int) -> Result[None]:
    return __execute(passthrough, scripts.SET_PERSON_CUSTOMER, {"person_id": person_id})


def get_person_count() -> Result[int]:
    return __execute(extract_count_int, scripts.GET_PERSON_COUNT)


def get_person_count_by_role(is_employee: bool) -> Result[int]:
    return __execute(
        extract_count_int,
        scripts.GET_PERSON_COUNT_BY_ROLE,
        {"is_employee": 1 if is_employee else 0},
    )


def get_person_page(offset: int, limit: int) -> Result[schema.Person]:
    return __execute(
        schema.Person,
        scripts.GET_PERSON_PAGE,
        {
            "limit": limit,
            "offset": offset,
        },
    )


def search_persons(query: str, offset: int, limit: int) -> Result[schema.Person]:
    if not query:
        return get_person_page(offset, limit)
    return __execute(
        schema.Person,
        scripts.SEARCH_PERSONS,
        {
            "query": f"%{query}%",
            "limit": limit,
            "offset": offset,
        },
    )


##
## Property management
##


def create_property(
    street_address: str,
    city: str,
    state: str,
    post_code: str,
) -> Result[schema.Property]:
    return __execute(
        schema.Property,
        scripts.CREATE_PROPERTY,
        {
            "street_address": street_address,
            "city": city,
            "state": state,
            "post_code": post_code,
        },
    )


def delete_property(property_id: int) -> Result[None]:
    return __execute(passthrough, scripts.DELETE_PROPERTY, {"property_id": property_id})


def get_property_by_id(property_id: int) -> Result[schema.Property]:
    return __execute(
        schema.Property, scripts.GET_PROPERTY_BY_ID, {"property_id": property_id}
    )


def get_property_by_address(street_address: str) -> Result[schema.Property]:
    return __execute(
        schema.Property,
        scripts.GET_PROPERTY_BY_ADDRESS,
        {"street_address": street_address},
    )


def get_property_count() -> Result[int]:
    return __execute(extract_count_int, scripts.GET_PROPERTY_COUNT)


def get_property_page(offset: int, limit: int) -> Result[schema.Property]:
    return __execute(
        schema.Property,
        scripts.GET_PROPERTY_PAGE,
        {
            "offset": offset,
            "limit": limit,
        },
    )


def search_properties(query: str, offset: int, limit: int) -> Result[schema.Property]:
    if not query:
        return get_property_page(offset, limit)
    return __execute(
        schema.Property,
        scripts.SEARCH_PROPERTIES,
        {
            "query": f"%{query}%",
            "offset": offset,
            "limit": limit,
        },
    )


##
## Booking management
##


def create_booking(
    property_id: int, person_id: int, booking_date: date
) -> Result[schema.Booking]:
    return __execute(
        schema.Booking,
        scripts.CREATE_BOOKING,
        {
            "property_id": property_id,
            "person_id": person_id,
            "booking_date": booking_date,
        },
    )


def delete_booking(booking_id: int) -> Result[None]:
    return __execute(passthrough, scripts.DELETE_BOOKING, {"booking_id": booking_id})


def update_booking_completion(booking_id: int, completed: bool) -> Result[None]:
    return __execute(
        passthrough,
        scripts.UPDATE_BOOKING_COMPLETION,
        {"booking_id": booking_id, "completed": completed},
    )


def get_booking_by_id(booking_id: int) -> Result[schema.Booking]:
    return __execute(
        schema.Booking, scripts.GET_BOOKING_BY_ID, {"booking_id": booking_id}
    )


def get_booking_by_person(person_id: int) -> Result[schema.Booking]:
    return __execute(
        schema.Booking, scripts.GET_BOOKINGS_BY_PERSON, {"person_id": person_id}
    )


def get_booking_by_property(property_id: int) -> Result[schema.Booking]:
    return __execute(
        schema.Booking, scripts.GET_BOOKINGS_BY_PROPERTY, {"property_id": property_id}
    )


def get_booking_count() -> Result[int]:
    return __execute(extract_count_int, scripts.GET_BOOKING_COUNT)


def get_booking_page(offset: int, limit: int) -> Result[schema.Booking]:
    return __execute(
        schema.Booking,
        scripts.GET_BOOKING_PAGE,
        {
            "offset": offset,
            "limit": limit,
        },
    )


class BookingStrings(pydantic.BaseModel):
    person_name: str
    property_name: str
    booking_date: date

    def __str__(self) -> str:
        return f"{self.person_name} for {self.property_name} on {self.booking_date}"


def get_booking_string(booking_id: int) -> Result[BookingStrings]:
    return __execute(
        BookingStrings, scripts.GET_BOOKING_STRING, {"booking_id": booking_id}
    )


def search_bookings(query: str, offset: int, limit: int) -> Result[schema.Booking]:
    if not query:
        return get_booking_page(offset, limit)
    return __execute(
        schema.Booking,
        scripts.SEARCH_BOOKINGS,
        {
            "query": f"%{query}%",
            "offset": offset,
            "limit": limit,
        },
    )


##
## Service management
##


def create_service(id: str, description: str, price: float) -> Result[schema.Service]:
    return __execute(
        schema.Service,
        scripts.CREATE_SERVICE,
        {
            "service_id": id,
            "description": description,
            "price": price,
        },
    )


def delete_service(service_id: str) -> Result[None]:
    return __execute(passthrough, scripts.DELETE_SERVICE, {"service_id": service_id})


def get_service_by_id(service_id: str) -> Result[schema.Service]:
    return __execute(
        schema.Service, scripts.GET_SERVICE_BY_ID, {"service_id": service_id}
    )


def get_service_count() -> Result[int]:
    return __execute(extract_count_int, scripts.GET_SERVICE_COUNT)


def get_service_page(offset: int, limit: int) -> Result[schema.Service]:
    return __execute(
        schema.Service,
        scripts.GET_SERVICE_PAGE,
        {
            "offset": offset,
            "limit": limit,
        },
    )


def search_services(query: str, offset: int, limit: int) -> Result[schema.Service]:
    if not query:
        return get_service_page(offset, limit)
    return __execute(
        schema.Service,
        scripts.SEARCH_SERVICES,
        {
            "query": f"%{query}%",
            "offset": offset,
            "limit": limit,
        },
    )


class BookingCost(pydantic.BaseModel):
    total: float


def get_booking_cost(booking_id: int) -> Result[BookingCost]:
    return __execute(BookingCost, scripts.GET_BOOKING_COST, {"booking_id": booking_id})


##
## Booking Service Management
##


def create_booking_service(
    booking_id: str, service_id: str, duration: int
) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.CREATE_BOOKING_SERVICE,
        {
            "booking_id": booking_id,
            "service_id": service_id,
            "duration": duration,
        },
    )


def delete_booking_service(booking_id: int, service_id: str) -> Result[None]:
    return __execute(
        passthrough,
        scripts.DELETE_BOOKING_SERVICE,
        {"booking_id": booking_id, "service_id": service_id},
    )


def delete_bookings_services(booking_id: int) -> Result[None]:
    return __execute(
        passthrough,
        scripts.DELETE_BOOKINGS_SERVICES,
        {"booking_id": booking_id},
    )


def get_service_by_booking_and_service(
    booking_id: int, service_id: str
) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICE_BY_BOOKING_AND_SERVICE,
        {"booking_id": booking_id, "service_id": service_id},
    )


def toggle_completion_booking_service(booking_id: int, service_id: str) -> Result[None]:
    return __execute(
        passthrough,
        scripts.TOGGLE_COMPLETION_BOOKING_SERVICE,
        {"booking_id": booking_id, "service_id": service_id},
    )


def get_services_by_booking(booking_id: int) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICES_BY_BOOKING,
        {"booking_id": booking_id},
    )


def get_service_count_by_booking(booking_id: int) -> Result[int]:
    return __execute(
        extract_count_int,
        scripts.GET_SERVICE_COUNT_BY_BOOKING,
        {"booking_id": booking_id},
    )


def get_service_page_by_booking(
    booking_id: int, offset: int, limit: int
) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICE_PAGE_BY_BOOKING,
        {"booking_id": booking_id, "offset": offset, "limit": limit},
    )


class BookingServiceStrings(pydantic.BaseModel):
    person_name: str
    property_name: str
    service_name: str
    price: float
    duration: int
    completed: bool


def get_booking_service_string(
    booking_id: int, service_id: str
) -> Result[BookingServiceStrings]:
    return __execute(
        BookingServiceStrings,
        scripts.GET_BOOKING_SERVICE_STRING,
        {"booking_id": booking_id, "service_id": service_id},
    )


def get_services_by_booking(booking_id: int) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICES_BY_BOOKING,
        {"booking_id": booking_id},
    )


class BookingServiceCompletion(pydantic.BaseModel):
    completed: int
    total: int


def get_completed_service_count_by_booking(
    booking_id: int,
) -> Result[BookingServiceCompletion]:
    return __execute(
        BookingServiceCompletion,
        scripts.GET_COMPLETED_SERVICE_COUNT_BY_BOOKING,
        {"booking_id": booking_id},
    )


def search_services_by_booking(
    booking_id: int, query: str, offset: int, limit: int
) -> Result[schema.BookingService]:
    if not query:
        return get_service_page_by_booking(booking_id, offset, limit)
    return __execute(
        schema.BookingService,
        scripts.SEARCH_SERVICES_BY_BOOKING,
        {
            "booking_id": booking_id,
            "query": f"%{query}%",
            "offset": offset,
            "limit": limit,
        },
    )


def get_services_by_date(
    start_date: date, end_date: date
) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICES_BY_DATE,
        {"start_date": start_date, "end_date": end_date},
    )


def get_services_person_and_date(
    person_id: int, start_date: date, end_date: date
) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICES_PERSON_AND_DATE,
        {
            "person_id": person_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


##
## Payment Management
##


def create_payment(
    booking_id: int, amount: float, payment_date: date
) -> Result[schema.Payment]:
    return __execute(
        schema.Payment,
        scripts.CREATE_PAYMENT,
        {
            "booking_id": booking_id,
            "amount": amount,
            "payment_date": payment_date.isoformat(),
        },
    )


def delete_payment(payment_id: int) -> Result[None]:
    return __execute(
        passthrough,
        scripts.DELETE_PAYMENT,
        {"payment_id": payment_id},
    )


def delete_payments_by_booking(booking_id: int) -> Result[None]:
    return __execute(
        passthrough,
        scripts.DELETE_PAYMENTS_BY_BOOKING,
        {"booking_id": booking_id},
    )


def get_payment_by_id(payment_id: int) -> Result[schema.Payment]:
    return __execute(
        schema.Payment,
        scripts.GET_PAYMENT_BY_ID,
        {"payment_id": payment_id},
    )


def get_payments_by_booking(booking_id: int) -> Result[schema.Payment]:
    return __execute(
        schema.Payment,
        scripts.GET_PAYMENTS_BY_BOOKING,
        {"booking_id": booking_id},
    )


def get_payment_count(booking_id: int) -> Result[int]:
    return __execute(
        int,
        scripts.GET_PAYMENT_COUNT,
        {"booking_id": booking_id},
    )


def get_payment_page(
    booking_id: int, offset: int, limit: int
) -> Result[schema.Payment]:
    return __execute(
        schema.Payment,
        scripts.GET_PAYMENT_PAGE,
        {"booking_id": booking_id, "offset": offset, "limit": limit},
    )


def search_payments(
    booking_id: int, query: str, offset: int, limit: int
) -> Result[schema.Payment]:
    if not query:
        return get_payment_page(booking_id, offset, limit)
    return __execute(
        schema.Payment,
        scripts.SEARCH_PAYMENTS,
        {
            "booking_id": booking_id,
            "query": f"%{query}%",
            "offset": offset,
            "limit": limit,
        },
    )


class PaymentTotals(pydantic.BaseModel):
    total_amount: float
    total_count: int


def get_payment_totals_by_booking(booking_id: int) -> Result[PaymentTotals]:
    return __execute(
        PaymentTotals,
        scripts.GET_PAYMENT_TOTALS_BY_BOOKING,
        {"booking_id": booking_id},
    )


##
## Roster Management
##


def create_roster(person_id: int, booking_service_id: int) -> Result[schema.Roster]:
    return __execute(
        schema.Roster,
        scripts.CREATE_ROSTER,
        {"person_id": person_id, "booking_service_id": booking_service_id},
    )


def delete_roster(person_id: int, booking_service_id: int) -> Result[None]:
    return __execute(
        passthrough,
        scripts.DELETE_ROSTER,
        {"person_id": person_id, "booking_service_id": booking_service_id},
    )


def get_people_by_service(booking_service_id: int) -> Result[list[schema.Person]]:
    return __execute(
        list[schema.Person],
        scripts.GET_PEOPLE_BY_SERVICE,
        {"booking_service_id": booking_service_id},
    )


def get_services_by_person(person_id: int) -> Result[list[schema.BookingService]]:
    return __execute(
        list[schema.BookingService],
        scripts.GET_SERVICES_BY_PERSON,
        {"person_id": person_id},
    )


def get_people_count_by_service(booking_service_id: int) -> Result[int]:
    return __execute(
        int,
        scripts.GET_PEOPLE_COUNT_BY_SERVICE,
        {"booking_service_id": booking_service_id},
    )


def get_service_count_by_person(person_id: int) -> Result[int]:
    return __execute(
        int,
        scripts.GET_SERVICE_COUNT_BY_PERSON,
        {"person_id": person_id},
    )


def get_people_page_by_service(
    booking_service_id: int, offset: int, limit: int
) -> Result[schema.Person]:
    return __execute(
        schema.Person,
        scripts.GET_PEOPLE_PAGE_BY_SERVICE,
        {"booking_service_id": booking_service_id, "offset": offset, "limit": limit},
    )


def get_services_page_by_person(
    person_id: int, offset: int, limit: int
) -> Result[schema.BookingService]:
    return __execute(
        schema.BookingService,
        scripts.GET_SERVICES_PAGE_BY_PERSON,
        {"person_id": person_id, "offset": offset, "limit": limit},
    )
