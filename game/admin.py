from django.contrib import admin
from .models import GameRoom, GameParticipant


@admin.register(GameRoom)
class GameRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'target_date', 'target_time', 'time_remaining_seconds', 'created_at']
    list_filter = ['status', 'target_date']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'time_remaining_seconds', 'target_datetime']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'status')
        }),
        ('Hora Objetivo del Juego', {
            'fields': ('target_date', 'target_time', 'target_datetime', 'time_remaining_seconds')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['reiniciar_sala_hoy', 'programar_manana']
    
    def reiniciar_sala_hoy(self, request, queryset):
        from django.utils import timezone
        from datetime import time
        
        for room in queryset:
            room.status = 'waiting'
            room.target_date = timezone.now().date()
            room.target_time = time(11, 0)  # 11:00 AM
            room.save()
        
        self.message_user(request, f"✅ {queryset.count()} sala(s) programada(s) para hoy a las 11:00 AM")
    reiniciar_sala_hoy.short_description = "🔄 Programar para hoy 11:00 AM"
    
    def programar_manana(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta, time
        
        for room in queryset:
            room.status = 'waiting'
            room.target_date = timezone.now().date() + timedelta(days=1)
            room.target_time = time(11, 0)
            room.save()
        
        self.message_user(request, f"✅ {queryset.count()} sala(s) programada(s) para mañana a las 11:00 AM")
    programar_manana.short_description = "📅 Programar para mañana 11:00 AM"


@admin.register(GameParticipant)
class GameParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'joined_at', 'is_active']
    list_filter = ['is_active', 'joined_at', 'room']
    search_fields = ['user__username', 'room__name']
    readonly_fields = ['joined_at']
    
    def has_add_permission(self, request):
        # No permitir agregar participantes manualmente
        return False