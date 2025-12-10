from django.urls import path
from . import views, views_tombola

urlpatterns = [
    path('', views.home, name='home'),
    path('waiting-room/', views.waiting_room, name='waiting_room'),
    path('game-start/', views.game_start, name='game_start'),
    path('api/room-info/', views.get_room_info, name='get_room_info'),
    path('api/sync-time/', views.sync_time, name='sync_time'),

    # Vistas del juego Tombola (views_tombola.py nuevo)
    path('lobby/', views_tombola.lobby, name='lobby'),
    path('sala/<str:codigo>/', views_tombola.sala_juego, name='sala_juego'),
    
    # API endpoints Tombola
    path('api/crear-partida/', views_tombola.crear_partida, name='crear_partida'),
    path('api/unirse/<str:codigo>/', views_tombola.unirse_partida, name='unirse_partida'),
    path('api/iniciar/<str:codigo>/', views_tombola.iniciar_partida, name='iniciar_partida'),
    path('api/sortear/<str:codigo>/', views_tombola.sortear_numero, name='sortear_numero'),
    path('api/estado/<str:codigo>/', views_tombola.estado_partida, name='estado_partida'),
    path('api/salir/<str:codigo>/', views_tombola.salir_partida, name='salir_partida'),
    path('api/historial/<str:codigo>/', views_tombola.historial_partida, name='historial_partida'),
]