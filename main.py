from app import State
from ui import Ui
from database import Database

from fakes import generate_customer, generate_property

from argparse import ArgumentParser


def main():
    db = Database()
    # parser = ArgumentParser(
    #     prog="Lawn Database", description="A database for lawn care service management."
    # )
    # subparsers = parser.add_subparsers(
    #     title="subcommands", required=True, dest="command"
    # )
    # reset = subparsers.add_parser("reset")
    # fake_customer = subparsers.add_parser("fake_customer")
    # fake_property = subparsers.add_parser("fake_property")
    # fake_property.add_argument("owner_id", type=int)

    # args = parser.parse_args()
    # match (args.command):
    #     case "reset":
    #         db.reset()
    #         print("Resetting database...")
    #         return
    #     case "fake_customer":
    #         c = generate_customer()
    #         print(c)
    #         return
    #     case "fake_property":
    #         owner_id = args.owner_id
    #         p = generate_property()
    #         p.owner = owner_id
    #         print(p)
    #         return
    #     case _:
    #         pass

    state = State(db)
    ui = Ui(state)
    ui.mainloop()


if __name__ == "__main__":
    main()
