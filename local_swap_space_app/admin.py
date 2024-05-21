from django.contrib import admin
from .models import User, Item, Category, Like, Match, Chat, Message, Rating, ItemImage


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'city']
    search_fields = ['username', 'email']
    # If you want to customize the map widget
    settings_overrides = {
        'DEFAULT_CENTER': (0, 0),
        'DEFAULT_ZOOM': 2,
    }


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'owner', 'status']
    search_fields = ['name', 'description']
    list_filter = ['status', 'category']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['item', 'liker', 'liked_on']
    search_fields = ['item__name', 'liker__username']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['like_one', 'like_two', 'matched_on']
    search_fields = ['like_one__item__name', 'like_two__item__name']


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['participant_one', 'participant_two', 'created_at']
    search_fields = ['participant_one__username', 'participant_two__username']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['chat', 'sender', 'sent_at']
    search_fields = ['chat__participant_one__username', 'chat__participant_two__username', 'sender__username']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['rated_user', 'rating_user', 'rating']
    search_fields = ['rated_user__username', 'rating_user__username']


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ['item', 'image']
