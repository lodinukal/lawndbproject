-- sqlite
CREATE TABLE IF NOT EXISTS Customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone_number VARCHAR(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS Property (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street_number INTEGER NOT NULL,
    -- could be null
    unit VARCHAR(10),
    street_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    post_code VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS Booking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    property_id INTEGER NOT NULL,
    /* iso8601 */
    date_time TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES Customer(id),
    FOREIGN KEY (property_id) REFERENCES Property(id)
);

CREATE TABLE IF NOT EXISTS Service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS BookingService (
    booking_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    duration INTEGER NOT NULL, -- duration in minutes
    additional_cost DECIMAL(10, 2) NOT NULL,
    notes TEXT,
    completed BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (booking_id, service_id),
    FOREIGN KEY (booking_id) REFERENCES Booking(id),
    FOREIGN KEY (service_id) REFERENCES Service(id)
);

-- many payments can be made for a booking
CREATE TABLE IF NOT EXISTS Payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_date TEXT NOT NULL, -- iso8601
    FOREIGN KEY (booking_id) REFERENCES Booking(id)
);