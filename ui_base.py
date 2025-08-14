import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk

from app import State

import dateparser

from database import Access
from util import Signal


class ModelEditor(ctk.CTkToplevel):
    def __init__(self, model, on_complete, master=None):
        super().__init__(master)
        self.model = model
        self.on_complete = on_complete
        self.title("Edit Model")
        self.geometry("400x300")

        # disable close button
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        # Create UI elements to edit the model
        self.label = ctk.CTkLabel(
            master=self, text=f"Editing {model.__class__.__name__}"
        )
        self.label.pack(pady=10)

        # Add more UI elements as needed to edit the model's attributes
        self.save_button = ctk.CTkButton(
            master=self, text="Save", command=self.save_model
        )
        self.save_button.pack(pady=10)

        self.inputs = dict()
        # get all the fields of the model
        for field in model.__dataclass_fields__.keys():
            if field == "id":
                continue

            entry = ctk.CTkEntry(master=self, placeholder_text=field)
            entry.pack(pady=5)
            entry.insert(0, getattr(model, field, ""))
            entry.bind("<Return>", lambda e, f=field: setattr(model, f, entry.get()))
            entry.bind("<FocusOut>", lambda e, f=field: setattr(model, f, entry.get()))
            self.inputs[field] = entry

    def save_model(self):
        # Logic to save the model changes
        for field, entry in self.inputs.items():
            setattr(self.model, field, entry.get())
        self.on_complete(self.model)
        self.destroy()


class TableUser:
    def gather_data(self, page_index: int, page_size: int = 10):
        raise NotImplementedError

    def get_max_pages(self, page_size: int):
        raise NotImplementedError

    def delete_items(self, selected: list):
        raise NotImplementedError

    def edit_item(self, item):
        raise NotImplementedError


class TableView(ctk.CTkFrame):
    page_index: int = 1
    page_size: int = 10
    cached_page_count: int = 0

    def __init__(
        self,
        user: TableUser,
        access: Access = Access.WRITE,
        master=None,
        columns=None,
        **kwargs,
    ):

        super().__init__(master, **kwargs)
        self.user = user

        style = ttk.Style()

        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#2a2d2e",
            foreground="white",
            rowheight=25,
            fieldbackground="#343638",
            bordercolor="#343638",
            borderwidth=0,
        )
        style.map("Treeview", background=[("selected", "#22559b")])

        style.configure(
            "Treeview.Heading", background="#565b5e", foreground="white", relief="flat"
        )
        style.map("Treeview.Heading", background=[("active", "#3484F0")])

        # create a Treeview widget, with pagination buttons at the bottom
        self.treeview = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.treeview.heading(col, text=col)
            self.treeview.column(col, anchor="center")
        self.treeview.pack(expand=True, fill="both")
        self.treeview.bind("<Double-1>", self.on_double_click)
        if access == Access.WRITE:
            self.treeview.bind("<Button-3>", self.on_right_click)

        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(expand=False, fill="x", pady=5)

        # make the buttons frame transparent
        self.buttons_frame.configure(fg_color="transparent")

        self.previous_button = ctk.CTkButton(
            master=self.buttons_frame, text="Previous", command=self.previous_page
        )
        self.previous_button.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.next_button = ctk.CTkButton(
            master=self.buttons_frame, text="Next", command=self.next_page
        )
        self.next_button.grid(row=0, column=1, sticky="e", padx=5, pady=5)

        self.get_page_count()

        self.page_count_label = ctk.CTkLabel(
            master=self.buttons_frame,
            text=f"Page 1 of {self.cached_page_count}",
        )
        self.page_count_label.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.grid_rowconfigure(0, weight=7)
        self.grid_rowconfigure(1, weight=1)

        self.load_data()

    def on_double_click(self, event):
        pass

    def on_right_click(self, event):
        selected = self.treeview.selection()
        if not selected:
            return

        # context menu for right click
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(
            label="Delete", command=lambda: self.context_menu_delete(selected)
        )
        context_menu.add_command(
            label="Edit",
            command=lambda: self.context_menu_edit(selected),
        )
        context_menu.post(event.x_root, event.y_root)

    def context_menu_delete(self, selected: list):
        to_delete = []
        for item in selected:
            values = self.treeview.item(item, "values")
            to_delete.append(int(values[0]))

        self.user.delete_items(to_delete)

    def context_menu_edit(self, selected: list):
        if not selected:
            return

        self.user.edit_item(int(self.treeview.item(selected[0], "values")[0]))

    def previous_page(self):
        if self.page_index > 1:
            self.page_index -= 1
            self.load_data()

            self.set_page_label_text()

    def next_page(self):
        max_pages = self.get_page_count()
        if self.page_index < max_pages:
            self.page_index += 1
            self.load_data()

            self.set_page_label_text()

    def load_data(self):
        max_pages = self.get_page_count()

        self.page_index = min(self.page_index, max_pages)
        self.page_index = max(self.page_index, 1)

        data = self.user.gather_data(self.page_index, self.page_size)
        self.set_data(data)

    def set_data(self, data):
        self.treeview.delete(*self.treeview.get_children())
        for index, item in enumerate(data):
            self.treeview.insert("", str(index), values=item.to_list())

        self.set_page_label_text()

    def get_page_count(self):
        self.cached_page_count = self.user.get_max_pages(self.page_size)
        return self.cached_page_count

    def set_page_label_text(self):
        self.page_count_label.configure(
            text=f"Page {self.page_index} of {self.cached_page_count}"
        )


empty_ordering_function = lambda x: 1
custom_colour_function = lambda x: None


class SearchbarWithCompletion(ctk.CTkFrame):
    def __init__(
        self,
        title,
        search_fn,
        on_choose,
        order=empty_ordering_function,
        colour_fn=custom_colour_function,
        master=None,
    ):
        super().__init__(master)
        self.title = title
        self.search_fn = search_fn
        self.on_choose = on_choose
        self.order = order
        self.colour_fn = colour_fn

        self.selected_label = ctk.CTkEntry(
            master=self, placeholder_text=f"Selected {self.title}"
        )
        self.selected_label.configure(state="readonly")
        self.selected_label.pack(pady=5, fill="x", padx=10)
        self.selected = None

        self.search_entry = ctk.CTkEntry(master=self, placeholder_text="Search")
        self.search_entry.pack(expand=True, fill="x", padx=10, pady=10)

        self.options = ctk.CTkScrollableFrame(self)
        self.options.pack(expand=True, fill="both", padx=10, pady=10)

        # as the user types, we will show the results in this frame
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.on_search()

    def on_search(self, event=None):
        search_text = self.search_entry.get().strip()
        results = self.search_fn(search_text)
        results = sorted(results, key=self.order)
        self.update_options(results)

    def choose(self, i):
        self.selected_label.configure(state="normal")
        self.selected_label.delete(0, "end")
        self.selected_label.insert(0, str(i))
        self.selected = i
        self.selected_label.configure(state="readonly")
        self.on_choose(i)

    def update_options(self, results):
        for widget in self.options.winfo_children():
            widget.destroy()

        for item in results:
            option_button = ctk.CTkButton(
                master=self.options,
                text=str(item),
                command=lambda i=item: self.choose(i),
            )
            option_button.pack(fill="x", padx=5, pady=2)
            if self.colour_fn:
                colour = self.colour_fn(item)
                if colour:
                    option_button.configure(fg_color=colour)

    def clear_selection(self):
        self.selected_label.configure(state="normal")
        self.selected_label.delete(0, "end")
        self.selected_label.configure(state="readonly")
        self.selected = None

        self.search_entry.delete(0, "end")


class DatetimeValidatedEntry(ctk.CTkFrame):
    def __init__(self, master=None, placeholder_text="Enter date and time"):
        super().__init__(master)

        self.entry = ctk.CTkEntry(
            master=self, placeholder_text=placeholder_text, fg_color="transparent"
        )
        self.entry.pack(expand=True, fill="x", padx=10, pady=10)

        self.entry.bind("<FocusOut>", self.validate_datetime)
        self.entry.bind("<Return>", self.validate_datetime)
        self.entry.bind("<KeyRelease>", self.validate_datetime)
        self.valid_time = None
        self.original_fg_color = self.entry.cget("fg_color")

        self.calculated_datetime = ctk.CTkLabel(
            master=self, text="Calculated DateTime will appear here"
        )
        self.calculated_datetime.pack(pady=5)

    def parse_datetime(self, s):
        try:
            return dateparser.parse(s, settings={"PREFER_DATES_FROM": "future"})
        except ValueError:
            return None

    def validate_datetime(self, event=None):
        got = self.parse_datetime(self.entry.get())
        if got is None:
            self.valid_time = None
            self.configure(fg_color="red")
            self.calculated_datetime.configure(text="Invalid DateTime")
        else:
            self.valid_time = got
            self.configure(fg_color=self.original_fg_color)
            self.calculated_datetime.configure(
                text=f"Calculated DateTime: {got.strftime('%Y-%m-%d %H:%M')}"
            )

    def clear(self):
        self.configure(fg_color=self.original_fg_color)
        self.entry.delete(0, "end")
        self.valid_time = None


class DateTimeRangeEntry(ctk.CTkFrame):
    def __init__(self, master=None, placeholder_text="Enter date and time range"):
        super().__init__(master)

        self.signal = Signal()

        self.start_entry = DatetimeValidatedEntry(
            master=self, placeholder_text="Start DateTime"
        )
        self.start_entry.pack(expand=True, fill="x", padx=10, pady=5)

        self.end_entry = DatetimeValidatedEntry(
            master=self, placeholder_text="End DateTime"
        )
        self.end_entry.pack(expand=True, fill="x", padx=10, pady=5)

        self.valid_range = None
        self.start_entry.entry.bind("<FocusOut>", self.validate_range)
        self.start_entry.entry.bind("<Return>", self.validate_range)
        self.end_entry.entry.bind("<FocusOut>", self.validate_range)
        self.end_entry.entry.bind("<Return>", self.validate_range)

    def validate_range(self, _):
        if not self.start_entry.valid_time or not self.end_entry.valid_time:
            self.valid_range = None
            self.signal.emit()
            return False

        if self.start_entry.valid_time >= self.end_entry.valid_time:
            self.valid_range = None
            self.signal.emit()
            return False

        self.valid_range = (self.start_entry.valid_time, self.end_entry.valid_time)
        self.signal.emit()
        return True
