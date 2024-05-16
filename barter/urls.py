"""
URL configuration for barter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.urls import path
from local_swap_space_app.views import (RegisterView, CustomLoginView, DashboardView, ItemDetailView, AddItemView,
                                        ItemUpdateView, AddImageView, DeleteImageView, UserProfileView,
                                        OtherUserProfileView, LikedItemsView, like_item, MatchUserListView, ChatView,
                                        send_message, delete_chat_and_related_data)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('item/<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('add_item/', AddItemView.as_view(), name='add_item'),
    path('item/edit/<int:pk>/', ItemUpdateView.as_view(), name='edit_item'),
    path('item/<int:pk>/add_image/', AddImageView.as_view(), name='add_image'),
    path('image/<int:pk>/delete/', DeleteImageView.as_view(), name='delete_image'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('user/<str:username>/', OtherUserProfileView.as_view(), name='other-user-profile'),
    path('liked_items/', LikedItemsView.as_view(), name='liked_items'),
    path('like-item/<int:item_id>/', like_item, name='like-item'),
    path('matches/', MatchUserListView.as_view(), name='match_list'),
    path('delete-chat/<int:chat_id>/', delete_chat_and_related_data, name='delete_chat'),
    path('chat/<int:pk>/', ChatView.as_view(), name='chat_detail'),
    path('chat/<int:chat_id>/send_message/', send_message, name='send_message'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
