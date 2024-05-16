from django.apps import AppConfig


# Definicja klasy konfiguracyjnej dla aplikacji Django.
class LocalSwapSpaceAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Ustawienie domyślnego typu pola autoincrement (klucz główny).
    name = 'local_swap_space_app'  # Nazwa aplikacji wewnątrz projektu Django.

    def ready(self):
        # Import sygnałów podczas ładowania aplikacji.
        # To zagwarantuje, że wszystkie sygnały zdefiniowane w 'local_swap_space_app.signals' będą zarejestrowane i aktywne.
        import local_swap_space_app.signals
