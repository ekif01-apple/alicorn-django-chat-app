from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("health/", views.health, name="health"),
    path(
        "conversations/",
        views.ConversationListCreateAPI.as_view(),
        name="conversations",
    ),
    path(
        "conversations/<int:convo_id>/messages/",
        views.ConversationMessagesAPI.as_view(),
        name="messages",
    ),
    path(
        "conversations/<int:convo_id>/read/",
        views.ConversationMarkReadAPI.as_view(),
        name="mark_read",
    ),
    path("users/", views.UserSearchAPI.as_view(), name="user_search"),
]
