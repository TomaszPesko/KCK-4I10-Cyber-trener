from src.menuModule.screens.base_screen import BaseScreen


class MainScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__("CyberTrener AI", "Witaj! Wybierz moduł z menu po lewej.")
        self.add_option("Tworzenie serii", lambda: navigator_cb("create_set"))
        self.add_option("Wczytywanie serii", lambda: navigator_cb("load_set"))
        self.add_option("Analiza postępów", lambda: navigator_cb("analyze_progress"))
        self.add_option("Zamknij program", lambda: navigator_cb("close"))
