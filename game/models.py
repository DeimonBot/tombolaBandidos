from django.db import models
from django.utils import timezone
from datetime import timedelta, time, datetime


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