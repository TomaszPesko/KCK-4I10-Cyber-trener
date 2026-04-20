import tkinter as tk


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("E-trener")

        # ===== ROZMIAR OKNA (np. 70% ekranu) =====
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        width = int(screen_w * 0.7)
        height = int(screen_h * 0.7)

        self.geometry(f"{width}x{height}")
        self.resizable(False, False)

        # ===== KONTAINER NA WIDOKI =====
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}

        for F in (
            MainMenu,
            AddSeriesMenu,
            DummyStats,
            DummyProgress,
            DummyLoadSeries,
            AddLive,
            AddFromFile,
        ):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        self.show_frame(MainMenu)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()


# ===== WIDOKI =====


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        tk.Label(self, text="Menu główne", font=("Arial", 20)).pack(pady=20)

        tk.Button(
            self,
            text="Dodaj serię",
            command=lambda: controller.show_frame(AddSeriesMenu),
        ).pack(pady=5)

        tk.Button(
            self,
            text="Wczytaj serię",
            command=lambda: controller.show_frame(DummyLoadSeries),
        ).pack(pady=5)

        tk.Button(
            self, text="Statystyki", command=lambda: controller.show_frame(DummyStats)
        ).pack(pady=5)

        tk.Button(
            self, text="Progres", command=lambda: controller.show_frame(DummyProgress)
        ).pack(pady=5)

        tk.Button(self, text="Wyjście", command=controller.quit).pack(pady=20)


# ===== MENU DODAWANIA SERII =====


class AddSeriesMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        self.back_button()

        tk.Label(self, text="Dodaj serię", font=("Arial", 20)).pack(pady=40)

        tk.Button(
            self, text="Dodaj na żywo", command=lambda: controller.show_frame(AddLive)
        ).pack(pady=5)

        tk.Button(
            self,
            text="Wczytaj z pliku",
            command=lambda: controller.show_frame(AddFromFile),
        ).pack(pady=5)

    def back_button(self):
        tk.Button(
            self, text="←", command=lambda: self.controller.show_frame(MainMenu)
        ).place(x=10, y=10)


# ===== DUMMY WIDOKI =====


class BaseDummy(tk.Frame):
    def __init__(self, parent, controller, title):
        super().__init__(parent)
        self.controller = controller

        tk.Button(
            self, text="←", command=lambda: controller.show_frame(MainMenu)
        ).place(x=10, y=10)

        tk.Label(self, text=title, font=("Arial", 20)).pack(pady=50)


class DummyStats(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Statystyki")


class DummyProgress(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Progres")


class DummyLoadSeries(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Wczytaj serię")


# ===== PODMENU DODAWANIA =====


class AddLive(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Dodaj na żywo")


class AddFromFile(BaseDummy):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Wczytaj z pliku")


# ===== START =====

if __name__ == "__main__":
    app = App()
    app.mainloop()
