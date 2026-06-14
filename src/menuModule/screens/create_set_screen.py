from src.menuModule.screens.base_screens import BaseScreen


class CreateSetScreen(BaseScreen):
    def __init__(self, navigator_cb):
        super().__init__(
            "Nowa Seria Treningowa", "Wybierz sposób zapisu lub perspektywę AI."
        )
        self.add_option("Start", lambda: print("[Camera] Starting stream..."))
        self.add_option(
            "Perspektywa z przodu", lambda: print("[AI Model] Perspective: Front")
        )
        self.add_option(
            "Perspektywa z boku", lambda: print("[AI Model] Perspective: Side")
        )
        self.add_option(
            "Zdefiniuj Serię Ręcznie", lambda: navigator_cb("manual_definition")
        )
        self.add_option("Zapisz serię", lambda: print("[Database] Auto-saving set..."))
        self.add_option("Wróć", lambda: navigator_cb("main_page"))
