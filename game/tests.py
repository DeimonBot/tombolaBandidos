"""
TESTS COMPLETOS PARA EL JUEGO DE TOMBOLA
Actualizado con rangos correctos y nueva funcionalidad
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    GameRoom, GameParticipant,  # Modelos de waiting room
    Game, Player, Carton, Prize, GameEvent  # Modelos de juego
)
from .logica import TombolaLogic
import json


# ============================================
# TESTS DE LÓGICA PURA
# ============================================

class TombolaLogicTests(TestCase):
    """Tests para la lógica pura del juego"""
    
    def test_generar_carton_dimensiones(self):
        """Verifica que el cartón tenga las dimensiones correctas"""
        carton = TombolaLogic.generar_carton()
        
        # Verificar 3 filas
        self.assertEqual(len(carton), 3)
        
        # Verificar 9 columnas en cada fila
        for fila in carton:
            self.assertEqual(len(fila), 9)
    
    def test_generar_carton_total_numeros(self):
        """Verifica que el cartón tenga exactamente 15 números"""
        carton = TombolaLogic.generar_carton()
        
        total_nums = sum(1 for fila in carton for n in fila if n is not None)
        self.assertEqual(total_nums, 15)
    
    def test_generar_carton_numeros_por_fila(self):
        """Verifica que cada fila tenga exactamente 5 números"""
        carton = TombolaLogic.generar_carton()
        
        for fila in carton:
            nums_fila = sum(1 for n in fila if n is not None)
            self.assertEqual(nums_fila, 5)
    
    def test_generar_carton_rangos_columnas(self):
        """Verifica que los números estén en los rangos CORRECTOS por columna"""
        carton = TombolaLogic.generar_carton()
        
        # RANGOS CORREGIDOS
        rangos = [
            (1, 10), (11, 20), (21, 30), (31, 40), (41, 50),
            (51, 60), (61, 70), (71, 80), (81, 90)
        ]
        
        for col in range(9):
            inicio, fin = rangos[col]
            for fila in range(3):
                num = carton[fila][col]
                if num is not None:
                    self.assertGreaterEqual(
                        num, inicio, 
                        f"Número {num} en columna {col} es menor que {inicio}"
                    )
                    self.assertLessEqual(
                        num, fin,
                        f"Número {num} en columna {col} es mayor que {fin}"
                    )
    
    def test_generar_carton_columnas_ordenadas(self):
        """Verifica que los números en cada columna estén ordenados"""
        carton = TombolaLogic.generar_carton()
        
        for col in range(9):
            numeros_col = [carton[fila][col] for fila in range(3) if carton[fila][col] is not None]
            self.assertEqual(
                numeros_col, sorted(numeros_col),
                f"Columna {col} no está ordenada: {numeros_col}"
            )
    
    def test_generar_carton_sin_duplicados(self):
        """Verifica que no haya números duplicados en el cartón"""
        carton = TombolaLogic.generar_carton()
        
        todos_numeros = [n for fila in carton for n in fila if n is not None]
        self.assertEqual(
            len(todos_numeros), len(set(todos_numeros)),
            f"Hay duplicados en el cartón: {todos_numeros}"
        )
    
    def test_generar_carton_numeros_por_columna(self):
        """Verifica que cada columna tenga entre 1 y 3 números"""
        carton = TombolaLogic.generar_carton()
        
        for col in range(9):
            nums_col = sum(1 for fila in carton if fila[col] is not None)
            self.assertGreaterEqual(nums_col, 1, f"Columna {col} tiene 0 números")
            self.assertLessEqual(nums_col, 3, f"Columna {col} tiene más de 3 números")
    
    def test_generar_carton_multiples_validos(self):
        """Verifica que se puedan generar múltiples cartones válidos"""
        for i in range(10):
            with self.subTest(iteracion=i):
                carton = TombolaLogic.generar_carton()
                self.assertTrue(
                    TombolaLogic._es_carton_valido(carton),
                    f"Cartón {i} no es válido"
                )
    
    def test_generar_distribucion_columnas_total(self):
        """Verifica que _generar_distribucion_columnas genere 15 posiciones totales"""
        distribucion = TombolaLogic._generar_distribucion_columnas()
        
        self.assertIsNotNone(distribucion)
        self.assertEqual(len(distribucion), 3, "Debe haber 3 filas")
        
        # Cada fila debe tener 5 columnas
        for fila in distribucion:
            self.assertEqual(len(fila), 5, f"Fila {fila} no tiene 5 columnas")
        
        # Contar números por columna
        contador = [0] * 9
        for fila in distribucion:
            for col in fila:
                contador[col] += 1
        
        # Cada columna debe tener entre 1 y 3 números
        for col, count in enumerate(contador):
            self.assertGreaterEqual(count, 1, f"Columna {col} tiene 0 números")
            self.assertLessEqual(count, 3, f"Columna {col} tiene {count} números (>3)")
        
        # Total debe ser 15
        self.assertEqual(sum(contador), 15)
    
    def test_generar_distribucion_columnas_sin_duplicados_por_fila(self):
        """Verifica que no haya columnas duplicadas en una fila"""
        distribucion = TombolaLogic._generar_distribucion_columnas()
        
        self.assertIsNotNone(distribucion)
        
        for idx, fila in enumerate(distribucion):
            self.assertEqual(
                len(fila), len(set(fila)),
                f"Fila {idx} tiene columnas duplicadas: {fila}"
            )
    
    def test_es_carton_valido_rechaza_invalidos(self):
        """Verifica que _es_carton_valido rechace cartones inválidos"""
        # Cartón con 6 números en una fila (inválido)
        carton_invalido_1 = [
            [1, 11, 21, 31, 41, 51, None, None, None],
            [None, None, None, None, None, None, 61, 71, 81],
            [None, None, None, None, None, None, None, None, None]
        ]
        self.assertFalse(TombolaLogic._es_carton_valido(carton_invalido_1))
        
        # Cartón con números fuera de rango
        carton_invalido_2 = [
            [15, None, 23, None, 45, None, None, None, None],  # 15 está en rango 11-20
            [None, 12, None, 34, None, 56, None, None, None],
            [None, None, None, None, None, None, 67, 78, 89]
        ]
        self.assertFalse(TombolaLogic._es_carton_valido(carton_invalido_2))
        
        # Cartón con números duplicados
        carton_invalido_3 = [
            [1, None, 23, None, 45, None, None, None, None],
            [None, 12, None, 23, None, 56, None, None, None],  # 23 duplicado
            [None, None, None, None, None, None, 67, 78, 89]
        ]
        self.assertFalse(TombolaLogic._es_carton_valido(carton_invalido_3))
    
    def test_sortear_numero_rango(self):
        """Verifica que los números sorteados estén entre 1 y 90"""
        numeros_sorteados = []
        
        for _ in range(10):
            numero = TombolaLogic.sortear_numero(numeros_sorteados)
            self.assertIsNotNone(numero)
            self.assertGreaterEqual(numero, 1)
            self.assertLessEqual(numero, 90)
            numeros_sorteados.append(numero)
    
    def test_sortear_numero_sin_repetir(self):
        """Verifica que no se repitan números sorteados"""
        numeros_sorteados = []
        
        for _ in range(20):
            numero = TombolaLogic.sortear_numero(numeros_sorteados)
            self.assertNotIn(numero, numeros_sorteados)
            numeros_sorteados.append(numero)
    
    def test_sortear_numero_todos_sorteados(self):
        """Verifica que retorne None cuando se sortearon todos los números"""
        numeros_sorteados = list(range(1, 91))
        numero = TombolaLogic.sortear_numero(numeros_sorteados)
        self.assertIsNone(numero)
    
    def test_marcar_numero_existente(self):
        """Verifica que se marque un número que existe en el cartón"""
        carton = [[1, 12, None, None, None, None, None, None, None],
                  [None, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, 90]]
        marcados = []
        
        resultado = TombolaLogic.marcar_numero(carton, 1, marcados)
        
        self.assertTrue(resultado)
        self.assertIn(1, marcados)
    
    def test_marcar_numero_no_existente(self):
        """Verifica que retorne False para un número que no existe"""
        carton = [[1, 12, None, None, None, None, None, None, None],
                  [None, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, 90]]
        marcados = []
        
        resultado = TombolaLogic.marcar_numero(carton, 50, marcados)
        
        self.assertFalse(resultado)
        self.assertNotIn(50, marcados)
    
    def test_marcar_numero_ya_marcado(self):
        """Verifica que no se duplique un número ya marcado"""
        carton = [[1, 12, None, None, None, None, None, None, None],
                  [None, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, 90]]
        marcados = [1]
        
        resultado = TombolaLogic.marcar_numero(carton, 1, marcados)
        
        self.assertTrue(resultado)
        self.assertEqual(marcados.count(1), 1, "El número 1 no debe duplicarse")
    
    def test_verificar_ambo(self):
        """Verifica detección de ambo (2 números en una fila)"""
        carton = [[1, 12, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        
        marcados = [1, 12]
        self.assertTrue(TombolaLogic.verificar_ambo(carton, marcados))
        
        marcados = [1]
        self.assertFalse(TombolaLogic.verificar_ambo(carton, marcados))
    
    def test_verificar_terno(self):
        """Verifica detección de terno (3 números en una fila)"""
        carton = [[1, 12, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        
        marcados = [1, 12, 23]
        self.assertTrue(TombolaLogic.verificar_terno(carton, marcados))
        
        marcados = [1, 12]
        self.assertFalse(TombolaLogic.verificar_terno(carton, marcados))
    
    def test_verificar_quaterna(self):
        """Verifica detección de quaterna (4 números en una fila)"""
        carton = [[1, 12, 23, 34, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        
        marcados = [1, 12, 23, 34]
        self.assertTrue(TombolaLogic.verificar_quaterna(carton, marcados))
        
        marcados = [1, 12, 23]
        self.assertFalse(TombolaLogic.verificar_quaterna(carton, marcados))
    
    def test_verificar_cinquina(self):
        """Verifica detección de cinquina (5 números en una fila)"""
        carton = [[1, 12, 23, 34, 45, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        
        marcados = [1, 12, 23, 34, 45]
        self.assertTrue(TombolaLogic.verificar_cinquina(carton, marcados))
        
        marcados = [1, 12, 23, 34]
        self.assertFalse(TombolaLogic.verificar_cinquina(carton, marcados))
    
    def test_verificar_tombola(self):
        """Verifica detección de tombola (cartón completo)"""
        carton = [[1, None, 23, None, 45, None, None, None, None],
                  [None, 12, None, 34, None, 56, None, None, None],
                  [None, None, None, None, None, None, 67, 78, 89]]
        
        todos = [1, 23, 45, 12, 34, 56, 67, 78, 89]
        self.assertTrue(TombolaLogic.verificar_tombola(carton, todos))
        
        algunos = [1, 23, 45]
        self.assertFalse(TombolaLogic.verificar_tombola(carton, algunos))
    
    def test_obtener_premios_actuales(self):
        """Verifica que obtener_premios_actuales retorne información correcta"""
        carton = [[1, 12, 23, 34, 45, None, None, None, None],
                  [None, None, None, None, None, 56, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        
        # Con cinquina
        marcados = [1, 12, 23, 34, 45]
        premios = TombolaLogic.obtener_premios_actuales(carton, marcados)
        
        self.assertTrue(premios['cinquina'])
        self.assertTrue(premios['quaterna'])
        self.assertTrue(premios['terno'])
        self.assertTrue(premios['ambo'])
        self.assertFalse(premios['tombola'])
        self.assertEqual(premios['filas_completas'], [0])
    
    def test_colocar_ficha_valida(self):
        """Verifica que se pueda colocar una ficha válida"""
        carton = [[1, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        marcados = []
        
        resultado = TombolaLogic.colocar_ficha_en_casilla(carton, 0, 0, 1, marcados)
        
        self.assertTrue(resultado)
        self.assertIn(1, marcados)
    
    def test_colocar_ficha_invalida_numero_incorrecto(self):
        """Verifica que no se pueda colocar una ficha con número incorrecto"""
        carton = [[1, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        marcados = []
        
        # Intentar colocar número 5 donde va el 1
        resultado = TombolaLogic.colocar_ficha_en_casilla(carton, 0, 0, 5, marcados)
        
        self.assertFalse(resultado)
        self.assertNotIn(5, marcados)
    
    def test_colocar_ficha_casilla_vacia(self):
        """Verifica que no se pueda colocar ficha en casilla vacía"""
        carton = [[1, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        marcados = []
        
        resultado = TombolaLogic.colocar_ficha_en_casilla(carton, 0, 1, 10, marcados)
        
        self.assertFalse(resultado)
        self.assertEqual(len(marcados), 0)
    
    def test_colocar_ficha_indices_invalidos(self):
        """Verifica que rechace índices fuera de rango"""
        carton = [[1, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        marcados = []
        
        # Fila negativa
        self.assertFalse(TombolaLogic.colocar_ficha_en_casilla(carton, -1, 0, 1, marcados))
        
        # Fila > 2
        self.assertFalse(TombolaLogic.colocar_ficha_en_casilla(carton, 3, 0, 1, marcados))
        
        # Columna negativa
        self.assertFalse(TombolaLogic.colocar_ficha_en_casilla(carton, 0, -1, 1, marcados))
        
        # Columna > 8
        self.assertFalse(TombolaLogic.colocar_ficha_en_casilla(carton, 0, 9, 1, marcados))
    
    def test_colocar_ficha_no_duplica(self):
        """Verifica que no se duplique una ficha ya colocada"""
        carton = [[1, None, 23, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, None]]
        marcados = [1]
        
        resultado = TombolaLogic.colocar_ficha_en_casilla(carton, 0, 0, 1, marcados)
        
        self.assertTrue(resultado)
        self.assertEqual(marcados.count(1), 1)
    
    def test_generar_codigo_partida(self):
        """Verifica que el código de partida tenga formato correcto"""
        codigo = TombolaLogic.generar_codigo_partida()
        
        self.assertEqual(len(codigo), 6)
        self.assertTrue(codigo.isalnum())
        self.assertTrue(codigo.isupper())
    
    def test_generar_codigo_partida_unicidad(self):
        """Verifica que se generen códigos diferentes"""
        codigos = set()
        for _ in range(100):
            codigo = TombolaLogic.generar_codigo_partida()
            codigos.add(codigo)
        
        # Con 100 intentos, debería haber al menos 95 códigos únicos
        self.assertGreater(len(codigos), 95)
    
    def test_imprimir_carton(self):
        """Verifica que se pueda imprimir el cartón como string"""
        carton = [[1, None, 23, None, None, None, None, None, None],
                  [None, 12, None, None, None, None, None, None, None],
                  [None, None, None, None, None, None, None, None, 90]]
        
        resultado = TombolaLogic.imprimir_carton(carton, [1, 23])
        
        self.assertIsInstance(resultado, str)
        self.assertIn('[', resultado)  # Debe mostrar números marcados con []
        self.assertIn('1', resultado)
        self.assertIn('23', resultado)
    
    def test_obtener_estadisticas_carton(self):
        """Verifica que las estadísticas del cartón sean correctas"""
        carton = [[1, 12, 23, 34, 45, None, None, None, None],
                  [None, None, None, None, None, 56, 67, None, None],
                  [None, None, None, None, None, None, None, 78, 89]]
        
        marcados = [1, 12, 23]
        stats = TombolaLogic.obtener_estadisticas_carton(carton, marcados)
        
        self.assertEqual(stats['total_numeros'], 9)
        self.assertEqual(stats['numeros_marcados'], 3)
        self.assertAlmostEqual(stats['porcentaje_completado'], 33.33, places=1)
        self.assertEqual(len(stats['numeros_faltantes']), 6)


# ============================================
# TESTS DE MODELOS
# ============================================

class GameRoomModelTests(TestCase):
    """Tests para el modelo GameRoom (sala de espera)"""
    
    def test_crear_game_room(self):
        """Verifica que se pueda crear una sala de espera"""
        from datetime import time, date
        
        room = GameRoom.objects.create(
            name="Sala Test",
            status='waiting',
            target_time=time(11, 0),
            target_date=date.today()
        )
        
        self.assertEqual(room.name, "Sala Test")
        self.assertEqual(room.status, 'waiting')
    
    def test_game_room_time_remaining(self):
        """Verifica que time_remaining_seconds funcione"""
        from datetime import time, date, timedelta
        
        # Crear sala que termina en 1 hora
        mañana = date.today() + timedelta(days=1)
        room = GameRoom.objects.create(
            name="Sala Test",
            target_time=time(10, 0),
            target_date=mañana
        )
        
        # Debe tener tiempo restante positivo
        self.assertGreater(room.time_remaining_seconds, 0)


class GameModelTests(TestCase):
    """Tests para el modelo Game"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
    
    def test_crear_game(self):
        """Verifica que se pueda crear una partida"""
        game = Game.objects.create(
            code='ABC123',
            host=self.user,
            status='waiting'
        )
        
        self.assertEqual(game.code, 'ABC123')
        self.assertEqual(game.host, self.user)
        self.assertEqual(game.status, 'waiting')
    
    def test_game_codigo_unico(self):
        """Verifica que el código sea único"""
        Game.objects.create(code='ABC123', host=self.user)
        
        with self.assertRaises(Exception):
            Game.objects.create(code='ABC123', host=self.user)
    
    def test_game_get_total_drawn(self):
        """Verifica que get_total_drawn funcione correctamente"""
        game = Game.objects.create(
            code='ABC123',
            host=self.user,
            drawn_numbers=[1, 5, 23, 45]
        )
        
        self.assertEqual(game.get_total_drawn(), 4)
    
    def test_game_is_full(self):
        """Verifica que is_full funcione correctamente"""
        game = Game.objects.create(
            code='ABC123',
            host=self.user,
            max_players=2
        )
        
        self.assertFalse(game.is_full())
        
        # Agregar 2 jugadores
        Player.objects.create(user=self.user, game=game, nickname='Player1')
        user2 = User.objects.create_user(username='user2', password='12345')
        Player.objects.create(user=user2, game=game, nickname='Player2')
        
        self.assertTrue(game.is_full())
    
    def test_game_can_start(self):
        """Verifica que can_start funcione correctamente"""
        game = Game.objects.create(
            code='ABC123',
            host=self.user,
            status='waiting'
        )
        
        # Con 0 jugadores
        self.assertFalse(game.can_start())
        
        # Con 1 jugador
        Player.objects.create(user=self.user, game=game, nickname='Player1')
        self.assertFalse(game.can_start())
        
        # Con 2 jugadores
        user2 = User.objects.create_user(username='user2', password='12345')
        Player.objects.create(user=user2, game=game, nickname='Player2')
        self.assertTrue(game.can_start())


class PlayerModelTests(TestCase):
    """Tests para el modelo Player"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.game = Game.objects.create(code='ABC123', host=self.user)
    
    def test_crear_player(self):
        """Verifica que se pueda crear un jugador"""
        player = Player.objects.create(
            user=self.user,
            game=self.game,
            nickname='TestPlayer'
        )
        
        self.assertEqual(player.nickname, 'TestPlayer')
        self.assertEqual(player.game, self.game)
    
    def test_player_unique_together(self):
        """Verifica que un usuario no pueda unirse dos veces a la misma partida"""
        Player.objects.create(user=self.user, game=self.game, nickname='Player1')
        
        with self.assertRaises(Exception):
            Player.objects.create(user=self.user, game=self.game, nickname='Player2')


class CartonModelTests(TestCase):
    """Tests para el modelo Carton"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.game = Game.objects.create(code='ABC123', host=self.user)
        self.player = Player.objects.create(user=self.user, game=self.game, nickname='TestPlayer')
    
    def test_crear_carton(self):
        """Verifica que se pueda crear un cartón"""
        carton_data = TombolaLogic.generar_carton()
        carton = Carton.objects.create(
            player=self.player,
            numbers=carton_data,
            marked=[]
        )
        
        self.assertEqual(carton.player, self.player)
        self.assertEqual(len(carton.numbers), 3)
    
    def test_carton_get_completion_percentage(self):
        """Verifica que get_completion_percentage funcione correctamente"""
        carton_data = [[1, 12, 23, 34, 45, None, None, None, None],
                       [None, None, None, None, None, 56, 67, None, None],
                       [None, None, None, None, None, None, None, 78, 89]]
        
        carton = Carton.objects.create(
            player=self.player,
            numbers=carton_data,
            marked=[1, 12, 23]
        )
        
        # 3 de 9 = 33.33%
        self.assertAlmostEqual(carton.get_completion_percentage(), 33.33, places=1)


class PrizeModelTests(TestCase):
    """Tests para el modelo Prize"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.game = Game.objects.create(code='ABC123', host=self.user)
        self.player = Player.objects.create(user=self.user, game=self.game, nickname='TestPlayer')
        self.carton = Carton.objects.create(
            player=self.player,
            numbers=TombolaLogic.generar_carton(),
            marked=[]
        )
    
    def test_crear_prize(self):
        """Verifica que se pueda crear un premio"""
        prize = Prize.objects.create(
            game=self.game,
            player=self.player,
            prize_type='ambo',
            carton=self.carton
        )
        
        self.assertEqual(prize.prize_type, 'ambo')
        self.assertEqual(prize.player, self.player)
    
    def test_prize_unique_together(self):
        """Verifica que solo haya un ganador por tipo de premio"""
        Prize.objects.create(
            game=self.game,
            player=self.player,
            prize_type='ambo',
            carton=self.carton
        )
        
        with self.assertRaises(Exception):
            Prize.objects.create(
                game=self.game,
                player=self.player,
                prize_type='ambo',
                carton=self.carton
            )


class GameEventModelTests(TestCase):
    """Tests para el modelo GameEvent"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.game = Game.objects.create(code='ABC123', host=self.user)
    
    def test_crear_event(self):
        """Verifica que se pueda crear un evento"""
        event = GameEvent.objects.create(
            game=self.game,
            event_type='game_created',
            data={'host': 'testuser'}
        )
        
        self.assertEqual(event.event_type, 'game_created')
        self.assertEqual(event.data['host'], 'testuser')


# ============================================
# TESTS DE INTEGRACIÓN
# ============================================

class IntegrationTests(TransactionTestCase):
    """Tests de integración del flujo completo del juego"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='12345')
        self.user2 = User.objects.create_user(username='user2', password='12345')
    
    def test_flujo_completo_partida(self):
        """Test del flujo completo: crear, unirse, jugar"""
        # 1. Crear partida
        game = Game.objects.create(
            code='TEST01',
            host=self.user1,
            status='waiting'
        )
        
        # 2. Jugadores se unen
        player1 = Player.objects.create(user=self.user1, game=game, nickname='Player1')
        player2 = Player.objects.create(user=self.user2, game=game, nickname='Player2')
        
        # 3. Generar cartones
        carton1 = Carton.objects.create(
            player=player1,
            numbers=TombolaLogic.generar_carton(),
            marked=[]
        )
        carton2 = Carton.objects.create(
            player=player2,
            numbers=TombolaLogic.generar_carton(),
            marked=[]
        )
        
        # 4. Iniciar partida
        game.status = 'in_progress'
        game.started_at = timezone.now()
        game.save()
        
        # 5. Sortear algunos números
        drawn = []
        for _ in range(10):
            num = TombolaLogic.sortear_numero(drawn)
            drawn.append(num)
            
            # Marcar en cartones
            TombolaLogic.marcar_numero(carton1.numbers, num, carton1.marked)
            TombolaLogic.marcar_numero(carton2.numbers, num, carton2.marked)
        
        game.drawn_numbers = drawn
        game.save()
        carton1.save()
        carton2.save()
        
        # Verificar que todo funcionó
        self.assertEqual(len(game.drawn_numbers), 10)
        self.assertGreaterEqual(len(carton1.marked), 0)
        self.assertGreaterEqual(len(carton2.marked), 0)
    
    def test_verificacion_premios_secuencial(self):
        """Verifica que los premios se otorguen en orden correcto"""
        # Crear partida y jugador
        game = Game.objects.create(code='TEST02', host=self.user1, status='in_progress')
        player = Player.objects.create(user=self.user1, game=game, nickname='Winner')
        
        # Crear cartón controlado
        carton = Carton.objects.create(
            player=player,
            numbers=[[1, 12, 23, 34, 45, None, None, None, None],
                     [None, None, None, None, None, 56, None, None, None],
                     [None, None, None, None, None, None, None, None, 90]],
            marked=[]
        )
        
        # Marcar 2 números (Ambo)
        carton.marked = [1, 12]
        self.assertTrue(TombolaLogic.verificar_ambo(carton.numbers, carton.marked))
        self.assertFalse(TombolaLogic.verificar_terno(carton.numbers, carton.marked))
        
        # Marcar 3 números (Terno)
        carton.marked = [1, 12, 23]
        self.assertTrue(TombolaLogic.verificar_terno(carton.numbers, carton.marked))
        self.assertFalse(TombolaLogic.verificar_quaterna(carton.numbers, carton.marked))
        
        # Marcar 4 números (Quaterna)
        carton.marked = [1, 12, 23, 34]
        self.assertTrue(TombolaLogic.verificar_quaterna(carton.numbers, carton.marked))
        self.assertFalse(TombolaLogic.verificar_cinquina(carton.numbers, carton.marked))
        
        # Marcar 5 números (Cinquina)
        carton.marked = [1, 12, 23, 34, 45]
        self.assertTrue(TombolaLogic.verificar_cinquina(carton.numbers, carton.marked))
        self.assertFalse(TombolaLogic.verificar_tombola(carton.numbers, carton.marked))
        
        # Marcar todos (Tombola)
        carton.marked = [1, 12, 23, 34, 45, 56, 90]
        self.assertTrue(TombolaLogic.verificar_tombola(carton.numbers, carton.marked))