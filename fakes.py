from faker import Faker

from database import Database, CustomerModel, PropertyModel, BookingModel

fake = Faker(locale="en_AU")


def generate_customer() -> CustomerModel:
    model = CustomerModel(
        id=-1,
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        phone=fake.phone_number(),
    )
    return model


def generate_property() -> PropertyModel:
    model = PropertyModel(
        id=-1,
        street_number=fake.building_number(),
        street_name=fake.street_name(),
        unit=fake.building_number() if fake.boolean(10) else None,
        city=fake.city(),
        post_code=fake.postcode(),
    )
    return model


def generate_booking(customer_id: int, property_id: int):
    model = BookingModel(
        id=-1,
        customer_id=customer_id,
        property_id=property_id,
        when=fake.date_time_this_year(False, True),
    )
    return model
