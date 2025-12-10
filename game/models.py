from django.db import models
from django.utils import timezone
from datetime import timedelta, time, datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class GameRoom(models.Model):
    """Modelo para manejar las salas de juego"""
    STATUS_CHOICES = [
        ('waiting', 'Esperando'),
        ('playing', 'Jugando'),
        ('finished', 'Finalizado'),
    ]
    
    name = models.CharField(max_length=100, default="Sala Principal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    
    # Hora específica del día
    target_time = models.TimeField(default=time(12, 00))  # 11:00 AM por defecto
    
    # Fecha para el juego
    target_date = models.DateField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    @property
    def target_datetime(self):
        """Combina fecha y hora objetivo en la zona horaria correcta"""
        from django.conf import settings
        import pytz
        
        # Crear datetime naive
        naive_datetime = datetime.combine(self.target_date, self.target_time)
        
        # Localizarlo en la zona horaria de settings
        local_tz = pytz.timezone(settings.TIME_ZONE)
        localized_datetime = local_tz.localize(naive_datetime)
        
        return localized_datetime

    @property
    def time_remaining_seconds(self):
        """Devuelve los segundos restantes hasta la hora objetivo"""
        now = timezone.now()
        target = self.target_datetime
        remaining = (target - now).total_seconds()
        return max(0, int(remaining))
    
    @property
    def is_expired(self):
        """Verifica si ya pasó la hora objetivo"""
        return timezone.now() >= self.target_datetime


class GameParticipant(models.Model):
    """Modelo para registrar jugadores en una sala"""
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['room', 'user']
        ordering = ['joined_at']
    
    def __str__(self):
        return f"{self.user.username} en {self.room.name}"


# ============================================
# MODELOS PARA EL JUEGO DE TOMBOLA
# ============================================

class Game(models.Model):
    """Representa una partida de Tombola"""
    STATUS_CHOICES = [
        ('waiting', 'Esperando jugadores'),
        ('in_progress', 'En progreso'),
        ('finished', 'Finalizada'),
        ('cancelled', 'Cancelada'),
    ]
    
    code = models.CharField(max_length=6, unique=True, db_index=True)
    #host = models.ForeignKey(user, on_delete=models.CASCADE, related_name='hosted_games')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    max_players = models.IntegerField(
        default=10,
        validators=[MinValueValidator(2), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Estado del sorteo
    current_number = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    drawn_numbers = models.JSONField(default=list)  # [1, 5, 23, 45, ...]
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"Game {self.code} - {self.status}"
    
    def get_total_drawn(self):
        """Retorna cantidad de números sorteados"""
        return len(self.drawn_numbers) if self.drawn_numbers else 0
    
    def is_full(self):
        """Verifica si la partida está llena"""
        return self.players.count() >= self.max_players
    
    def can_start(self):
        """Verifica si la partida puede iniciarse"""
        return self.status == 'waiting' and self.players.count() >= 2


class Player(models.Model):
    """Representa un jugador dentro de una partida de Tombola"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_players')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='players')
    nickname = models.CharField(max_length=50)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_ready = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'game']
        ordering = ['joined_at']
        indexes = [
            models.Index(fields=['game', 'user']),
        ]
    
    def __str__(self):
        return f"{self.nickname} en {self.game.code}"
    
    def get_total_prizes(self):
        """Retorna cantidad de premios ganados"""
        return self.prizes.count()


class Carton(models.Model):
    """
    Cartón de Tombola
    - 3 filas x 9 columnas
    - 5 números por fila (15 números en total)
    - Números del 1 al 90
    - Columna 0: 1-10, Columna 1: 11-20, ..., Columna 8: 81-90
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='cartones')
    numbers = models.JSONField()  # [[1, None, 23, ...], [...], [...]]
    marked = models.JSONField(default=list)  # [1, 23, 45, ...]
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['player']),
        ]
    
    def __str__(self):
        return f"Carton de {self.player.nickname}"
    
    def get_completion_percentage(self):
        """Retorna porcentaje de completitud del cartón"""
        total = sum(1 for fila in self.numbers for n in fila if n is not None)
        if total == 0:
            return 0
        marcados = len(self.marked) if self.marked else 0
        return (marcados / total) * 100


class Prize(models.Model):
    """Premios ganados en la partida"""
    PRIZE_TYPES = [
        ('ambo', 'Ambo (2 en fila)'),
        ('terno', 'Terno (3 en fila)'),
        ('quaterna', 'Quaterna (4 en fila)'),
        ('cinquina', 'Cinquina (5 en fila)'),
        ('tombola', 'Tombola (cartón completo)'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='prizes')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='prizes')
    prize_type = models.CharField(max_length=20, choices=PRIZE_TYPES)
    carton = models.ForeignKey(Carton, on_delete=models.CASCADE, related_name='prizes_won')
    awarded_at = models.DateTimeField(auto_now_add=True)
    
    # Información adicional sobre el premio
    numbers_at_win = models.JSONField(default=list)  # Números marcados al ganar
    drawn_count = models.IntegerField(default=0)  # Cantidad de números sorteados al ganar
    
    class Meta:
        unique_together = ['game', 'prize_type']  # Solo un ganador por premio por partida
        ordering = ['awarded_at']
        indexes = [
            models.Index(fields=['game', 'prize_type']),
            models.Index(fields=['player']),
        ]
    
    def __str__(self):
        return f"{self.prize_type} - {self.player.nickname}"


class GameEvent(models.Model):
    """Registro de eventos de la partida para replay y auditoría"""
    EVENT_TYPES = [
        ('game_created', 'Partida creada'),
        ('player_joined', 'Jugador unido'),
        ('player_left', 'Jugador salió'),
        ('game_started', 'Partida iniciada'),
        ('number_drawn', 'Número sorteado'),
        ('prize_won', 'Premio ganado'),
        ('game_finished', 'Partida finalizada'),
        ('game_cancelled', 'Partida cancelada'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    data = models.JSONField(default=dict)  # Datos adicionales del evento
    timestamp = models.DateTimeField(auto_now_add=True)
    player = models.ForeignKey(
        Player, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='events'
    )
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['game', 'timestamp']),
            models.Index(fields=['game', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"