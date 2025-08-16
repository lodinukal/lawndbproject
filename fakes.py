from faker import Faker

import auth
from schema import Booking, Person, Property

fake = Faker(locale="en_AU")


def generate_person() -> Person:
    model = Person(
        id=-1,
        username=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        phone_number=fake.phone_number(),
        is_employee=False,
        hashed_password=auth.hash_plaintext(fake.password()),
    )
    return model


def generate_property() -> Property:
    model = Property(
        id=-1,
        street_address=fake.street_address(),
        city=fake.city(),
        post_code=fake.postcode(),
        state=fake.state(),
    )
    return model


def generate_booking(customer_id: int, property_id: int):
    model = Booking(
        id=-1,
        person_id=customer_id,
        property_id=property_id,
        when=fake.date_between(start_date="today", end_date="1m"),
        completed=fake.boolean(),
        price=round(fake.pydecimal(left_digits=3, right_digits=2, positive=True), 2),
    )
    return model
