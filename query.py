from dataclasses import dataclass
from datetime import date
from sqlite3 import Row
from typing import Callable, TypeVar

from pydantic import ValidationError
import database
import schema
import scripts

T = TypeVar("T")


@dataclass
class Result[T]:
    error: str | None
    value: list[T] | None

    def one(self) -> T | None:
        if self.value and len(self.value) == 1:
            return self.value[0]
        return None


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
        return Result[T](error=result.error, value=new_data)
    except ValidationError as e:
        print("Error occurred:", e.json())
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


def create_service(
    service_id: str, description: str, price: float
) -> Result[schema.Service]:
    return __execute(
        schema.Service,
        scripts.CREATE_SERVICE,
        {
            "service_id": service_id,
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
