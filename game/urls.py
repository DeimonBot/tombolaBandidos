from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('waiting-room/', views.waiting_room, name='waiting_room'),
    path('game-start/', views.game_start, name='game_start'),
    path('api/room-info/', views.get_room_info, name='get_room_info'),
    path('api/sync-time/', views.sync_time, name='sync_time'),
]