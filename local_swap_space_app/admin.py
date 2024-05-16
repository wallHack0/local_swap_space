from django.contrib import admin
from .models import Item, ItemImage


# Definicja klasy admina dla obrazów przedmiotów jako elementu wstawianego
class ItemImageAdmin(admin.StackedInline):
    model = ItemImage
    extra = 1


# Definicja klasy admina dla przedmiotów
class ItemAdmin(admin.ModelAdmin):
    inlines = [ItemImageAdmin]  # Umożliwia dodanie obrazów przedmiotów bezpośrednio w formularzu przedmiotu


# Rejestracja modelu Item w panelu administracyjnym z użyciem zdefiniowanej klasy ItemAdmin
admin.site.register(Item, ItemAdmin)

# Opcjonalna rejestracja modelu ItemImage w panelu administracyjnym.
admin.site.register(ItemImage)
