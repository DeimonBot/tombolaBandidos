from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from .models import GameRoom, GameParticipant
from datetime import time, date


@login_required
def home(request):
    """Redirige a la sala de espera"""
    return redirect('waiting_room')


@login_required
def waiting_room(request):
    """Vista de la sala de espera con temporizador sincronizado"""
    
    with transaction.atomic():
        # Obtener o crear LA ÚNICA sala activa
        room, created = GameRoom.objects.get_or_create(
            status='waiting',
            defaults={
                'name': 'Sala Principal',
                'target_date': date.today(),  # Corregido: era 'target_data'
                'target_time': time(11, 0)
            }
        )
        
        if created:
            print(f"🆕 Nueva sala creada: ID {room.id}")
        else:
            print(f"🎮 Usando sala existente: ID {room.id}")
            
            # Si la sala expiró, reiniciarla para mañana a la misma hora
            if room.is_expired:
                print(f"⏰ Sala expirada, reiniciando...")
                # Mantener la misma hora pero cambiar la fecha a mañana
                from datetime import timedelta
                room.target_date = date.today() + timedelta(days=1)
                room.status = 'waiting'
                room.save()
    
    # Registrar participante
    participant, created = GameParticipant.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={'is_active': True}
    )
    
    if not created:
        participant.is_active = True
        participant.save()
    
    # Calcular tiempo final usando la nueva propiedad
    tiempo_final_timestamp = int(room.target_datetime.timestamp() * 1000)
    
    # Contar jugadores
    num_jugadores = GameParticipant.objects.filter(
        room=room,
        is_active=True
    ).count()
    
    # DEBUG
    print(f"👤 Usuario: {request.user.username}")
    print(f"🏠 Sala ID: {room.id}")
    print(f"📅 Fecha objetivo: {room.target_date}")
    print(f"🕐 Hora objetivo: {room.target_time}")
    print(f"⏰ Timestamp: {tiempo_final_timestamp}")
    print(f"⏱️ Segundos restantes: {room.time_remaining_seconds}")
    print(f"👥 Jugadores: {num_jugadores}")
    
    context = {
        'room': room,
        'tiempo_final_timestamp': tiempo_final_timestamp,
        'num_jugadores': num_jugadores,
    }
    
    return render(request, 'waiting_room.html', context)


@login_required
def game_start(request):
    """Vista cuando inicia el juego"""
    return render(request, 'game_start.html')


@login_required
def get_room_info(request):
    """API para obtener info de la sala"""
    room = GameRoom.objects.filter(status='waiting').first()
    
    if not room:
        return JsonResponse({'error': 'No hay sala activa'}, status=404)
    
    num_jugadores = GameParticipant.objects.filter(
        room=room,
        is_active=True
    ).count()
    
    return JsonResponse({
        'num_jugadores': num_jugadores,
        'status': room.status,
        'time_remaining': room.time_remaining_seconds
    })


@login_required
def sync_time(request):
    """API para sincronizar tiempo"""
    room = GameRoom.objects.filter(status='waiting').first()
    
    if not room:
        return JsonResponse({'error': 'No hay sala activa'}, status=404)
    
    # Usar la propiedad target_datetime en lugar de end_time
    tiempo_final_timestamp = int(room.target_datetime.timestamp() * 1000)
    
    return JsonResponse({
        'tiempo_final_timestamp': tiempo_final_timestamp,
        'server_time': int(timezone.now().timestamp() * 1000)
    })