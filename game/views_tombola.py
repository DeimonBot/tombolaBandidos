"""
VISTAS PARA EL JUEGO DE TOMBOLA
Separa la lógica de waiting_room del juego principal
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_http_methods
from .models import Game, Player, Carton, Prize, GameEvent
from .logica import TombolaLogic
import json
import logging

logger = logging.getLogger(__name__)


# ============================================
# VISTAS HTML
# ============================================

@login_required
def lobby(request):
    """Vista del lobby - Lista de partidas disponibles"""
    # Obtener partidas en espera que no estén llenas
    partidas_disponibles = Game.objects.filter(
        status='waiting'
    ).select_related('host').prefetch_related('players')
    
    # Obtener partidas en progreso donde el usuario participa
    mis_partidas = Game.objects.filter(
        players__user=request.user,
        status='in_progress'
    ).distinct()
    
    context = {
        'partidas_disponibles': partidas_disponibles,
        'mis_partidas': mis_partidas,
    }
    
    return render(request, 'game/lobby.html', context)


@login_required
def sala_juego(request, codigo):
    """Vista principal de la sala de juego"""
    partida = get_object_or_404(Game, code=codigo)
    
    # Verificar que el usuario es parte de la partida
    try:
        jugador = Player.objects.get(user=request.user, game=partida)
    except Player.DoesNotExist:
        return redirect('game:lobby')
    
    # Obtener cartón del jugador
    carton = Carton.objects.filter(player=jugador).first()
    
    # Verificar si el jugador es el host
    es_host = partida.host == request.user
    
    context = {
        'partida': partida,
        'jugador': jugador,
        'carton': carton,
        'es_host': es_host,
    }
    
    return render(request, 'game/sala_juego.html', context)


# ============================================
# API ENDPOINTS
# ============================================

@login_required
@require_http_methods(["POST"])
def crear_partida(request):
    """Crea una nueva partida de Tombola"""
    try:
        data = json.loads(request.body) if request.body else {}
        max_players = data.get('max_players', 10)
        
        # Validar max_players
        if not (2 <= max_players <= 100):
            return JsonResponse({
                'error': 'El número de jugadores debe estar entre 2 y 100'
            }, status=400)
        
        # Generar código único
        codigo = TombolaLogic.generar_codigo_partida()
        intentos = 0
        while Game.objects.filter(code=codigo).exists() and intentos < 10:
            codigo = TombolaLogic.generar_codigo_partida()
            intentos += 1
        
        if intentos >= 10:
            return JsonResponse({
                'error': 'No se pudo generar un código único'
            }, status=500)
        
        # Crear partida
        with transaction.atomic():
            partida = Game.objects.create(
                code=codigo,
                host=request.user,
                status='waiting',
                max_players=max_players
            )
            
            # Registrar evento
            GameEvent.objects.create(
                game=partida,
                event_type='game_created',
                data={'host': request.user.username, 'max_players': max_players}
            )
        
        logger.info(f"Partida {codigo} creada por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'codigo': codigo,
            'mensaje': 'Partida creada exitosamente',
            'max_players': max_players
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error al crear partida: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def unirse_partida(request, codigo):
    """Un jugador se une a una partida existente"""
    try:
        data = json.loads(request.body) if request.body else {}
        nickname = data.get('nickname', request.user.username)
        
        # Validar nickname
        if not nickname or len(nickname) > 50:
            return JsonResponse({
                'error': 'Nickname inválido (máximo 50 caracteres)'
            }, status=400)
        
        # Buscar partida
        partida = get_object_or_404(Game, code=codigo)
        
        # Validar que la partida está esperando jugadores
        if partida.status != 'waiting':
            return JsonResponse({
                'error': 'La partida ya comenzó o finalizó'
            }, status=400)
        
        # Validar que el usuario no esté ya en la partida
        if Player.objects.filter(user=request.user, game=partida).exists():
            return JsonResponse({
                'error': 'Ya estás en esta partida'
            }, status=400)
        
        # Validar cupo
        if partida.is_full():
            return JsonResponse({
                'error': 'Partida llena'
            }, status=400)
        
        # Validar nickname único en la partida
        if Player.objects.filter(game=partida, nickname=nickname).exists():
            return JsonResponse({
                'error': 'Este nickname ya está en uso en esta partida'
            }, status=400)
        
        # Crear jugador y cartón en una transacción
        with transaction.atomic():
            jugador = Player.objects.create(
                user=request.user,
                game=partida,
                nickname=nickname
            )
            
            # Generar cartón para el jugador usando la LÓGICA
            carton_data = TombolaLogic.generar_carton()
            carton = Carton.objects.create(
                player=jugador,
                numbers=carton_data,
                marked=[]
            )
            
            # Registrar evento
            GameEvent.objects.create(
                game=partida,
                event_type='player_joined',
                data={'nickname': nickname, 'user': request.user.username},
                player=jugador
            )
        
        logger.info(f"{nickname} se unió a la partida {codigo}")
        
        return JsonResponse({
            'success': True,
            'mensaje': f'{nickname} se unió a la partida',
            'player_id': jugador.id,
            'carton_id': carton.id,
            'carton': carton_data
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error al unirse a partida {codigo}: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def iniciar_partida(request, codigo):
    """Inicia la partida (solo el host puede hacerlo)"""
    try:
        partida = get_object_or_404(Game, code=codigo)
        
        # Verificar que es el host
        if partida.host != request.user:
            return JsonResponse({
                'error': 'Solo el host puede iniciar la partida'
            }, status=403)
        
        # Verificar que la partida puede iniciar
        if not partida.can_start():
            return JsonResponse({
                'error': 'Se necesitan al menos 2 jugadores para iniciar'
            }, status=400)
        
        # Verificar estado
        if partida.status != 'waiting':
            return JsonResponse({
                'error': 'La partida ya inició o finalizó'
            }, status=400)
        
        # Cambiar estado
        with transaction.atomic():
            partida.status = 'in_progress'
            partida.started_at = timezone.now()
            partida.drawn_numbers = []
            partida.current_number = None
            partida.save()
            
            # Registrar evento
            GameEvent.objects.create(
                game=partida,
                event_type='game_started',
                data={'players_count': partida.players.count()}
            )
        
        logger.info(f"Partida {codigo} iniciada por {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'mensaje': 'Partida iniciada',
            'started_at': partida.started_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error al iniciar partida {codigo}: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def sortear_numero(request, codigo):
    """Sortea un nuevo número usando la LÓGICA"""
    try:
        partida = get_object_or_404(Game, code=codigo)
        
        # Verificar que es el host
        if partida.host != request.user:
            return JsonResponse({
                'error': 'Solo el host puede sortear números'
            }, status=403)
        
        # Verificar estado
        if partida.status != 'in_progress':
            return JsonResponse({
                'error': 'La partida no está en progreso'
            }, status=400)
        
        # Sortear número usando la LÓGICA
        numeros_sorteados = partida.drawn_numbers or []
        
        # Validar que no se han sorteado todos
        if len(numeros_sorteados) >= 90:
            return JsonResponse({
                'error': 'Ya se sortearon todos los números (1-90)'
            }, status=400)
        
        numero = TombolaLogic.sortear_numero(numeros_sorteados)
        
        if numero is None:
            return JsonResponse({
                'error': 'No hay más números disponibles para sortear'
            }, status=400)
        
        # Usar transacción para atomicidad
        with transaction.atomic():
            # Guardar número
            numeros_sorteados.append(numero)
            partida.drawn_numbers = numeros_sorteados
            partida.current_number = numero
            partida.save()
            
            # Marcar automáticamente en todos los cartones usando la LÓGICA
            cartones = Carton.objects.select_for_update().filter(player__game=partida)
            for carton in cartones:
                marcados = carton.marked or []
                TombolaLogic.marcar_numero(carton.numbers, numero, marcados)
                carton.marked = marcados
                carton.save()
            
            # Registrar evento
            GameEvent.objects.create(
                game=partida,
                event_type='number_drawn',
                data={
                    'number': numero, 
                    'total_drawn': len(numeros_sorteados),
                    'host': request.user.username
                }
            )
            
            # Verificar premios
            nuevos_premios = verificar_premios_partida(partida)
        
        logger.info(f"Número {numero} sorteado en partida {codigo}")
        
        return JsonResponse({
            'success': True,
            'numero': numero,
            'total_sorteados': len(numeros_sorteados),
            'nuevos_premios': nuevos_premios
        })
    
    except Exception as e:
        logger.error(f"Error al sortear número en partida {codigo}: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


def verificar_premios_partida(partida):
    """
    Verifica y otorga premios usando la LÓGICA
    
    Returns:
        Lista de nuevos premios otorgados
    """
    cartones = Carton.objects.filter(player__game=partida).select_related('player')
    nuevos_premios = []
    
    # Orden jerárquico de premios
    premios_jerarquia = ['tombola', 'cinquina', 'quaterna', 'terno', 'ambo']
    
    for tipo_premio in premios_jerarquia:
        # Si ya existe este premio, pasar al siguiente
        if Prize.objects.filter(game=partida, prize_type=tipo_premio).exists():
            continue
        
        # Buscar ganador
        for carton in cartones:
            marcados = carton.marked or []
            
            # Obtener función de verificación correspondiente
            funcion = getattr(TombolaLogic, f'verificar_{tipo_premio}')
            
            if funcion(carton.numbers, marcados):
                # Crear premio
                prize = Prize.objects.create(
                    game=partida,
                    player=carton.player,
                    prize_type=tipo_premio,
                    carton=carton,
                    numbers_at_win=marcados.copy(),
                    drawn_count=len(partida.drawn_numbers)
                )
                
                # Registrar evento
                GameEvent.objects.create(
                    game=partida,
                    event_type='prize_won',
                    data={
                        'prize_type': tipo_premio,
                        'winner': carton.player.nickname,
                        'numbers_drawn': len(partida.drawn_numbers)
                    },
                    player=carton.player
                )
                
                nuevos_premios.append({
                    'tipo': tipo_premio,
                    'ganador': carton.player.nickname,
                    'numeros_sorteados': len(partida.drawn_numbers)
                })
                
                logger.info(f"{tipo_premio} ganado por {carton.player.nickname} en partida {partida.code}")
                
                # Si ganó tombola, terminar partida
                if tipo_premio == 'tombola':
                    partida.status = 'finished'
                    partida.finished_at = timezone.now()
                    partida.save()
                    
                    # Registrar evento
                    GameEvent.objects.create(
                        game=partida,
                        event_type='game_finished',
                        data={
                            'winner': carton.player.nickname,
                            'total_numbers_drawn': len(partida.drawn_numbers)
                        }
                    )
                    
                    logger.info(f"Partida {partida.code} finalizada. Ganador: {carton.player.nickname}")
                    return nuevos_premios  # Terminar verificación
                
                break  # Solo un ganador por premio
    
    return nuevos_premios


@login_required
def estado_partida(request, codigo):
    """Retorna el estado actual de la partida"""
    try:
        partida = get_object_or_404(Game, code=codigo)
        
        # Verificar que el usuario es parte de la partida
        es_host = partida.host == request.user
        es_jugador = Player.objects.filter(user=request.user, game=partida).exists()
        
        if not (es_host or es_jugador):
            return JsonResponse({
                'error': 'No tienes acceso a esta partida'
            }, status=403)
        
        # Obtener jugadores con sus cartones
        jugadores = []
        for player in partida.players.all().prefetch_related('cartones'):
            cartones_data = []
            for c in player.cartones.all():
                # Calcular estadísticas del cartón
                stats = TombolaLogic.obtener_estadisticas_carton(c.numbers, c.marked or [])
                
                cartones_data.append({
                    'id': c.id,
                    'numbers': c.numbers,
                    'marked': c.marked or [],
                    'completion': stats['porcentaje_completado']
                })
            
            jugadores.append({
                'id': player.id,
                'nickname': player.nickname,
                'is_ready': player.is_ready,
                'is_connected': player.is_connected,
                'cartones': cartones_data,
                'total_premios': player.get_total_prizes()
            })
        
        # Obtener premios
        premios = []
        for prize in partida.prizes.all().select_related('player'):
            premios.append({
                'tipo': prize.prize_type,
                'ganador': prize.player.nickname,
                'fecha': prize.awarded_at.isoformat(),
                'numeros_sorteados': prize.drawn_count
            })
        
        return JsonResponse({
            'codigo': partida.code,
            'estado': partida.status,
            'numero_actual': partida.current_number,
            'numeros_sorteados': partida.drawn_numbers or [],
            'total_sorteados': partida.get_total_drawn(),
            'jugadores': jugadores,
            'total_jugadores': len(jugadores),
            'max_jugadores': partida.max_players,
            'premios': premios,
            'es_host': es_host,
            'created_at': partida.created_at.isoformat(),
            'started_at': partida.started_at.isoformat() if partida.started_at else None,
            'finished_at': partida.finished_at.isoformat() if partida.finished_at else None
        })
    
    except Exception as e:
        logger.error(f"Error al obtener estado de partida {codigo}: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def salir_partida(request, codigo):
    """Permite a un jugador salir de una partida"""
    try:
        partida = get_object_or_404(Game, code=codigo)
        
        # Buscar al jugador
        try:
            player = Player.objects.get(user=request.user, game=partida)
        except Player.DoesNotExist:
            return JsonResponse({
                'error': 'No estás en esta partida'
            }, status=404)
        
        # No permitir salir si la partida está en progreso
        if partida.status == 'in_progress':
            return JsonResponse({
                'error': 'No puedes salir de una partida en progreso'
            }, status=400)
        
        nickname = player.nickname
        
        with transaction.atomic():
            # Registrar evento antes de eliminar
            GameEvent.objects.create(
                game=partida,
                event_type='player_left',
                data={'nickname': nickname}
            )
            
            # Eliminar jugador (cascade eliminará cartones)
            player.delete()
            
            # Si era el host y hay otros jugadores, transferir host
            if partida.host == request.user:
                otros_jugadores = partida.players.all()
                if otros_jugadores.exists():
                    nuevo_host = otros_jugadores.first()
                    partida.host = nuevo_host.user
                    partida.save()
                    logger.info(f"Host transferido a {nuevo_host.nickname} en partida {codigo}")
                else:
                    # Si no hay jugadores, cancelar partida
                    partida.status = 'cancelled'
                    partida.save()
                    logger.info(f"Partida {codigo} cancelada por falta de jugadores")
        
        logger.info(f"{nickname} salió de la partida {codigo}")
        
        return JsonResponse({
            'success': True,
            'mensaje': f'{nickname} salió de la partida'
        })
    
    except Exception as e:
        logger.error(f"Error al salir de partida {codigo}: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


@login_required
def historial_partida(request, codigo):
    """Retorna el historial completo de eventos de una partida"""
    try:
        partida = get_object_or_404(Game, code=codigo)
        
        # Verificar acceso
        es_host = partida.host == request.user
        es_jugador = Player.objects.filter(user=request.user, game=partida).exists()
        
        if not (es_host or es_jugador):
            return JsonResponse({
                'error': 'No tienes acceso a esta partida'
            }, status=403)
        
        # Obtener eventos
        eventos = []
        for event in partida.events.all().select_related('player'):
            eventos.append({
                'tipo': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'data': event.data,
                'player': event.player.nickname if event.player else None
            })
        
        return JsonResponse({
            'codigo': codigo,
            'eventos': eventos,
            'total_eventos': len(eventos)
        })
    
    except Exception as e:
        logger.error(f"Error al obtener historial de partida {codigo}: {str(e)}")
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)