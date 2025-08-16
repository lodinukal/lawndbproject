import auth

CREATE_TABLES = """
-- sqlite
CREATE TABLE IF NOT EXISTS Person (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone_number VARCHAR(15) NOT NULL,
    -- default to making a customer
    is_employee BOOLEAN NOT NULL DEFAULT 0,
    hashed_password VARCHAR(256) NOT NULL
);
CREATE TABLE IF NOT EXISTS Property (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    post_code VARCHAR(10) NOT NULL
);
CREATE TABLE IF NOT EXISTS Booking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    property_id INTEGER NOT NULL,
    /* iso8601 */
    booking_date TEXT NOT NULL,
    FOREIGN KEY (person_id) REFERENCES Person(id),
    FOREIGN KEY (property_id) REFERENCES Property(id)
);
CREATE TABLE IF NOT EXISTS Service (
    id VARCHAR(100) PRIMARY KEY,
    description TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);
CREATE TABLE IF NOT EXISTS BookingService (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    duration INTEGER NOT NULL DEFAULT 60,
    FOREIGN KEY (booking_id) REFERENCES Booking(id),
    FOREIGN KEY (service_id) REFERENCES Service(id)
);
-- many payments can be made for a booking
CREATE TABLE IF NOT EXISTS Payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_date TEXT NOT NULL,
    -- iso8601
    FOREIGN KEY (booking_id) REFERENCES Booking(id)
);
CREATE TABLE IF NOT EXISTS Roster (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    booking_service_id INTEGER NOT NULL,
    FOREIGN KEY (person_id) REFERENCES Person(id),
    FOREIGN KEY (booking_service_id) REFERENCES BookingService(id)
);
"""

# on conflict ignore, as we already have an admin user
CREATE_ADMIN_USER = """
INSERT INTO Person (id, first_name, last_name, email, phone_number, is_employee, hashed_password, username)
VALUES (1, 'Admin', 'User', 'admin@example.com', '123-456-7890', 1, "{}", 'admin') ON CONFLICT DO NOTHING
""".format(
    auth.hash_plaintext("admin123")
)

DROP_TABLES = """
DROP TABLE IF EXISTS Roster;
DROP TABLE IF EXISTS BookingService;
DROP TABLE IF EXISTS Payment;
DROP TABLE IF EXISTS Booking;
DROP TABLE IF EXISTS Service;
DROP TABLE IF EXISTS Property;
DROP TABLE IF EXISTS Person;
"""


##
## Person Management
##

# Creates a person, defaulting to customer
CREATE_PERSON = """
INSERT INTO Person (first_name, last_name, email, phone_number, is_employee, username, hashed_password)
VALUES (:first_name, :last_name, :email, :phone_number, 0, :username, :hashed_password)
"""

# Deletes a person
# :person_id integer - The id of the person to delete
DELETE_PERSON = """
DELETE FROM Person WHERE id = :person_id
"""

# Get a person by ID
# :person_id integer - The id of the person to retrieve
GET_PERSON_BY_ID = """
SELECT * FROM Person WHERE id = :person_id
"""

# Get a person by email
# :email string - The email of the person to retrieve
GET_PERSON_BY_EMAIL = """
SELECT * FROM Person WHERE email = :email
"""

# Get a person by username
# :username string - The username of the person to retrieve
GET_PERSON_BY_USERNAME = """
SELECT * FROM Person WHERE username = :username
"""

# Tries to log in a person
# :username string - The username of the person trying to log in
# :hashed_password string - The hashed password of the person trying to log in
LOGIN_PERSON = """
SELECT * FROM Person WHERE username = :username AND hashed_password = :hashed_password
"""

# Set person employee
# :person_id integer - The id of the person to update
SET_PERSON_EMPLOYEE = """
UPDATE Person SET is_employee = 1 WHERE id = :person_id
"""

# Set person customer
# :person_id integer - The id of the person to update
SET_PERSON_CUSTOMER = """
UPDATE Person SET is_employee = 0 WHERE id = :person_id
"""

# Get person count
GET_PERSON_COUNT = """
SELECT COUNT(*) as count FROM Person
"""

# Get person count by role
# :is_employee boolean - The role of the persons to count
GET_PERSON_COUNT_BY_ROLE = """
SELECT COUNT(*) as count FROM Person WHERE is_employee = :is_employee
"""

# Get a page of persons
# :limit integer - The maximum number of persons to return
# :offset integer - The number of persons to skip
GET_PERSON_PAGE = """
SELECT * FROM Person LIMIT :limit OFFSET :offset
"""

# Searches for a given person
# :query string - The search query to use
# :limit integer - The maximum number of persons to return
# :offset integer - The number of persons to skip
SEARCH_PERSONS = """
SELECT * FROM Person WHERE first_name LIKE :query OR last_name LIKE :query OR email LIKE :query OR phone_number LIKE :query LIMIT :limit OFFSET :offset
"""

##
## Property Management
##

# Creates a property
# :street_address string - The street address of the property
# :city string - The city of the property
# :state string - The state of the property
# :post_code string - The postal code of the property
CREATE_PROPERTY = """
INSERT INTO Property (street_address, city, state, post_code)
VALUES (:street_address, :city, :state, :post_code)
"""

# Deletes a property
# :property_id integer - The id of the property to delete
DELETE_PROPERTY = """
DELETE FROM Property WHERE id = :property_id
"""

# Get a property by ID
# :property_id integer - The id of the property to retrieve
GET_PROPERTY_BY_ID = """
SELECT * FROM Property WHERE id = :property_id
"""

# Get a property by address
# :street_address string - The street address of the property to retrieve
GET_PROPERTY_BY_ADDRESS = """
SELECT * FROM Property WHERE street_address = :street_address
"""

# Get property count
GET_PROPERTY_COUNT = """
SELECT COUNT(*) as count FROM Property
"""

# Get a page of properties
# :limit integer - The maximum number of properties to return
# :offset integer - The number of properties to skip
GET_PROPERTY_PAGE = """
SELECT * FROM Property LIMIT :limit OFFSET :offset
"""

# Searches for a given property
# :query string - The search query to use
# :limit integer - The maximum number of properties to return
# :offset integer - The number of properties to skip
SEARCH_PROPERTIES = """
SELECT * FROM Property WHERE street_address LIKE :query OR city LIKE :query OR state LIKE :query OR post_code LIKE :query LIMIT :limit OFFSET :offset
"""

##
## Booking Management
##

# Create a booking
# :person_id integer - The id of the person making the booking
# :property_id integer - The id of the property being booked
# :booking_date string - The date of the booking (ISO 8601 format)
# :price decimal - The price of the booking
CREATE_BOOKING = """
INSERT INTO Booking (person_id, property_id, booking_date)
VALUES (:person_id, :property_id, :booking_date)
"""

# Delete a booking
# :booking_id integer - The id of the booking to delete
DELETE_BOOKING = """
DELETE FROM Booking WHERE id = :booking_id
"""

# Sets a booking's completion
# :booking_id integer - The id of the booking to update
# :completed boolean - The new completion status of the booking
UPDATE_BOOKING_COMPLETION = """
UPDATE Booking SET completed = :completed WHERE id = :booking_id
"""

# Get a booking by ID
# :booking_id integer - The id of the booking to retrieve
GET_BOOKING_BY_ID = """
SELECT * FROM Booking WHERE id = :booking_id
"""

# Get bookings by person
# :person_id integer - The id of the person whose bookings to retrieve
GET_BOOKINGS_BY_PERSON = """
SELECT * FROM Booking WHERE person_id = :person_id
"""

# Get bookings by property
# :property_id integer - The id of the property whose bookings to retrieve
GET_BOOKINGS_BY_PROPERTY = """
SELECT * FROM Booking WHERE property_id = :property_id
"""

# Get booking count
GET_BOOKING_COUNT = """
SELECT COUNT(*) as count FROM Booking
"""

# Get a page of bookings
# :limit integer - The maximum number of bookings to return
# :offset integer - The number of bookings to skip
GET_BOOKING_PAGE = """
SELECT * FROM Booking LIMIT :limit OFFSET :offset
"""

# Searches for a given booking
# :query string - The search query to use
# :limit integer - The maximum number of bookings to return
# :offset integer - The number of bookings to skip
SEARCH_BOOKINGS = """
SELECT * FROM Booking WHERE booking_date LIKE :query 
LIMIT :limit OFFSET :offset
"""

##
## Service Management
##

# Creates a service
# :service_id string - The name of the service
# :description string - The description of the service
# :price decimal - The price of the service
CREATE_SERVICE = """
INSERT INTO Service (id, description, price)
VALUES (:service_id, :description, :price)
"""

# Deletes a service
# :id integer - The id of the service to delete
DELETE_SERVICE = """
DELETE FROM Service WHERE id = :service_id
"""

# Gets a service by ID
# :service_id integer - The id of the service to retrieve
GET_SERVICE_BY_ID = """
SELECT * FROM Service WHERE id = :service_id
"""

# Get service count
GET_SERVICE_COUNT = """
SELECT COUNT(*) as count FROM Service
"""

# Get a page of services
# :limit integer - The maximum number of services to return
# :offset integer - The number of services to skip
GET_SERVICE_PAGE = """
SELECT * FROM Service LIMIT :limit OFFSET :offset
"""

# Searches for a given service
# :query string - The search query to use
# :limit integer - The maximum number of services to return
# :offset integer - The number of services to skip
SEARCH_SERVICES = """
SELECT * FROM Service WHERE id LIKE :query OR description LIKE :query OR price LIKE :query LIMIT :limit OFFSET :offset
"""

##
## Booking service management
##

# Creates a booking service
# :booking_id integer - The id of the booking to associate with the service
# :service_id integer - The id of the service to associate with the booking
# :duration integer - The duration of the service in minutes
CREATE_BOOKING_SERVICE = """
INSERT INTO BookingService (booking_id, service_id, duration)
VALUES (:booking_id, :service_id, :duration)
"""

# Deletes a booking service
# :booking_id integer - The id of the booking to disassociate from the service
# :service_id integer - The id of the service to disassociate from the booking
DELETE_BOOKING_SERVICE = """
DELETE FROM BookingService WHERE booking_id = :booking_id AND service_id = :service_id
"""

# Gets the services for a booking
# :booking_id integer - The id of the booking whose services to retrieve
GET_SERVICES_BY_BOOKING = """
SELECT * FROM BookingService WHERE booking_id = :booking_id
"""

# Gets service count for a booking
# :booking_id integer - The id of the booking whose service count to retrieve
GET_SERVICE_COUNT_BY_BOOKING = """
SELECT COUNT(*) as count FROM BookingService WHERE booking_id = :booking_id
"""

# Gets a page of services for a booking
# :booking_id integer - The id of the booking whose services to retrieve
# :limit integer - The maximum number of services to return
# :offset integer - The number of services to skip
GET_SERVICE_PAGE_BY_BOOKING = """
SELECT * FROM BookingService WHERE booking_id = :booking_id LIMIT :limit OFFSET :offset
"""

# Searches the services for a booking
# :booking_id integer - The id of the booking whose services to search
# :query string - The search query to use
# :limit integer - The maximum number of services to return
# :offset integer - The number of services to skip
SEARCH_SERVICES_BY_BOOKING = """
SELECT * FROM BookingService WHERE booking_id = :booking_id AND (service_id LIKE :query OR duration LIKE :query) LIMIT :limit OFFSET :offset
"""

##
## Payment Management
##

# Creates a payment
# :booking_id integer - The id of the booking being paid for
# :amount decimal - The amount of the payment
# :booking_date string - The date of the payment (ISO 8601 format)
CREATE_PAYMENT = """
INSERT INTO Payment (booking_id, amount, booking_date)
VALUES (:booking_id, :amount, :booking_date)
"""

# Get a payment by ID
# :payment_id integer - The id of the payment to retrieve
GET_PAYMENT_BY_ID = """
SELECT * FROM Payment WHERE id = :payment_id
"""

# Get payments by booking
# :booking_id integer - The id of the booking whose payments to retrieve
GET_PAYMENTS_BY_BOOKING = """
SELECT * FROM Payment WHERE booking_id = :booking_id
"""

# Get payment count
GET_PAYMENT_COUNT = """
SELECT COUNT(*) as count FROM Payment
"""

# Get a page of payments
# :limit integer - The maximum number of payments to return
# :offset integer - The number of payments to skip
GET_PAYMENT_PAGE = """
SELECT * FROM Payment LIMIT :limit OFFSET :offset
"""

# Searches for a given payment
# :query string - The search query to use
# :limit integer - The maximum number of payments to return
# :offset integer - The number of payments to skip
SEARCH_PAYMENTS = """
SELECT * FROM Payment WHERE amount LIKE :query OR booking_date LIKE :query LIMIT :limit OFFSET :offset
"""

##
## Roster Management
##

# Creates a rostering for a booking for a person
# :person_id integer - The id of the person to associate with the booking
# :booking_service_id integer - The id of the booking service to associate with the person
CREATE_ROSTER = """
INSERT INTO Roster (person_id, booking_service_id)
VALUES (:person_id, :booking_service_id)
"""

# Deletes a rostering for a booking for a person
# :person_id integer - The id of the person to disassociate from the booking
# :booking_service_id integer - The id of the booking service to disassociate from the person
DELETE_ROSTER = """
DELETE FROM Roster WHERE person_id = :person_id AND booking_service_id = :booking_service_id
"""

# Gets all the people in a given service for a booking
# :booking_service_id integer - The id of the booking service whose people to retrieve
GET_PEOPLE_BY_SERVICE = """
SELECT * FROM Roster WHERE booking_service_id = :booking_service_id
"""

# Gets all the booking services for a person
# :person_id integer - The id of the person whose booking services to retrieve
GET_SERVICES_BY_PERSON = """
SELECT * FROM Roster WHERE person_id = :person_id
"""

# Gets the count of people in a service for a booking
# :booking_service_id integer - The id of the booking service whose people count to retrieve
GET_PEOPLE_COUNT_BY_SERVICE = """
SELECT COUNT(*) as count FROM Roster WHERE booking_service_id = :booking_service_id
"""

# Gets the count of booking services for a person
# :person_id integer - The id of the person whose booking services count to retrieve
GET_SERVICE_COUNT_BY_PERSON = """
SELECT COUNT(*) as count FROM Roster WHERE person_id = :person_id
"""

# Gets a page of people by a service's bookings
# :booking_service_id integer - The id of the booking service whose people to retrieve
# :limit integer - The maximum number of people to return
# :offset integer - The number of people to skip
GET_PEOPLE_PAGE_BY_SERVICE = """
SELECT * FROM Roster WHERE booking_service_id = :booking_service_id LIMIT :limit OFFSET :offset
"""

# Gets a page of services for a person
# :person_id integer - The id of the person whose services to retrieve
# :limit integer - The maximum number of services to return
# :offset integer - The number of services to skip
GET_SERVICES_PAGE_BY_PERSON = """
SELECT * FROM Roster WHERE person_id = :person_id LIMIT :limit OFFSET :offset
"""
