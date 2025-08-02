import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk


class ErrorDialog(ctk.CTkToplevel):
    def __init__(self, message: str, master=None):
        super().__init__(master)
        self.title("Error")
        self.geometry("300x150")
        self.maxsize(600, 300)

        self.label = ctk.CTkLabel(master=self, text=message)
        self.label.pack(pady=20)

        self.ok_button = ctk.CTkButton(master=self, text="OK", command=self.destroy)
        self.ok_button.pack(pady=10)


class ModelEditor(ctk.CTkToplevel):
    def __init__(self, model, on_complete, master=None):
        super().__init__(master)
        self.model = model
        self.on_complete = on_complete
        self.title("Edit Model")
        self.geometry("400x300")

        # disable close button
        self.protocol("WM_DELETE_WINDOW", lambda: self.save_model())

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

    def __init__(
        self,
        user: TableUser,
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

    def next_page(self):
        max_pages = self.user.get_max_pages(self.page_size)
        if self.page_index < max_pages:
            self.page_index += 1
            self.load_data()

    def load_data(self):
        max_pages = self.user.get_max_pages(self.page_size)

        self.page_index = min(self.page_index, max_pages)
        self.page_index = max(self.page_index, 1)

        data = self.user.gather_data(self.page_index, self.page_size)
        self.set_data(data)

    def set_data(self, data):
        self.treeview.delete(*self.treeview.get_children())
        for index, item in enumerate(data):
            self.treeview.insert("", str(index), values=item.to_list())
