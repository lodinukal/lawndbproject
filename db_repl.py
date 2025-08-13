import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
connection = db.cursor()

while True:
    try:
        query = input("Enter SQL query: ")
        if query.lower() == "exit":
            break
        connection.execute(query)
        db.commit()
        # check if data returned
        got = connection.fetchall()
        if got:
            for row in got:
                print(row)
        else:
            print("No rows returned.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
