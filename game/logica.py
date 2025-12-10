"""
LÓGICA PURA DEL JUEGO DE TÓMBOLA
Versión 2.0 - Creada desde cero con validaciones correctas
"""
import random
from typing import List, Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class TombolaLogic:
    """Clase con toda la lógica del juego de Tómbola"""
    
    # Rangos de números por columna (0-indexed)
    RANGOS_COLUMNAS = [
        (1, 10),   # Columna 0: 1-10
        (11, 20),  # Columna 1: 11-20
        (21, 30),  # Columna 2: 21-30
        (31, 40),  # Columna 3: 31-40
        (41, 50),  # Columna 4: 41-50
        (51, 60),  # Columna 5: 51-60
        (61, 70),  # Columna 6: 61-70
        (71, 80),  # Columna 7: 71-80
        (81, 90),  # Columna 8: 81-90
    ]
    
    # ============================================
    # GENERACIÓN DE CARTONES
    # ============================================
    
    @staticmethod
    def generar_carton() -> List[List[Optional[int]]]:
        """
        Genera un cartón válido de Tómbola
        
        REGLAS:
        - 3 filas x 9 columnas
        - Cada fila tiene exactamente 5 números (intercalados)
        - Total de 15 números por cartón
        - Columna 0: números 1-10, Columna 1: 11-20, etc.
        - Cada columna tiene entre 1 y 3 números
        - Números ordenados de menor a mayor en cada columna
        - Patrón intercalado: las posiciones con números alternan entre filas
        
        Returns:
            Matriz 3x9 con números y None
        """
        max_intentos = 100
        
        for intento in range(max_intentos):
            carton = [[None for _ in range(9)] for _ in range(3)]
            
            # Paso 1: Decidir qué columnas tendrán números en cada fila
            # asegurando que cada fila tenga 5 números y cada columna 1-3
            distribucion = TombolaLogic._generar_distribucion_columnas()
            
            if not distribucion:
                continue
            
            # Paso 2: Asignar números específicos a cada posición
            for fila_idx, columnas_con_numeros in enumerate(distribucion):
                for col in columnas_con_numeros:
                    inicio, fin = TombolaLogic.RANGOS_COLUMNAS[col]
                    
                    # Obtener números ya usados en esta columna
                    usados = [
                        carton[f][col] 
                        for f in range(3) 
                        if carton[f][col] is not None
                    ]
                    
                    # Números disponibles en este rango
                    disponibles = [
                        n for n in range(inicio, fin + 1) 
                        if n not in usados
                    ]
                    
                    if not disponibles:
                        break  # No hay números disponibles, reintentar
                    
                    carton[fila_idx][col] = random.choice(disponibles)
            
            # Paso 3: Ordenar números dentro de cada columna (de arriba a abajo)
            for col in range(9):
                numeros_en_columna = []
                filas_con_numero = []
                
                for fila in range(3):
                    if carton[fila][col] is not None:
                        numeros_en_columna.append(carton[fila][col])
                        filas_con_numero.append(fila)
                
                # Ordenar y reasignar
                numeros_en_columna.sort()
                for i, fila in enumerate(filas_con_numero):
                    carton[fila][col] = numeros_en_columna[i]
            
            # Paso 4: Validar antes de retornar
            if TombolaLogic._es_carton_valido(carton):
                logger.info(f"Cartón válido generado en intento {intento + 1}")
                return carton
        
        # Si no se pudo generar, lanzar excepción
        raise Exception(
            f"No se pudo generar un cartón válido después de {max_intentos} intentos"
        )
    
    @staticmethod
    def _generar_distribucion_columnas() -> Optional[List[List[int]]]:
        """
        Genera una distribución válida de columnas para las 3 filas.
        
        REGLAS:
        - Cada fila debe tener exactamente 5 columnas con números
        - Cada columna debe tener entre 1 y 3 números en total
        - Total: 15 números (5 por fila x 3 filas)
        - Patrón intercalado: alternar posiciones vacías y llenas
        
        Returns:
            Lista de 3 listas, cada una con 5 índices de columnas (0-8)
            Ejemplo: [[0,2,3,5,7], [1,2,4,6,8], [0,3,4,7,8]]
            O None si no se pudo generar
        """
        max_intentos = 100
        
        for _ in range(max_intentos):
            # Contador de números por columna
            contador_columnas = [0] * 9
            distribucion = []
            
            for fila in range(3):
                # Filtrar columnas disponibles (que tengan menos de 3 números)
                columnas_disponibles = [
                    c for c in range(9) 
                    if contador_columnas[c] < 3
                ]
                
                if len(columnas_disponibles) < 5:
                    break  # No hay suficientes columnas disponibles
                
                # Seleccionar 5 columnas aleatorias
                columnas_seleccionadas = random.sample(columnas_disponibles, 5)
                columnas_seleccionadas.sort()
                
                # Actualizar contador
                for col in columnas_seleccionadas:
                    contador_columnas[col] += 1
                
                distribucion.append(columnas_seleccionadas)
            
            # Validar que se generaron 3 filas
            if len(distribucion) != 3:
                continue
            
            # Validar que cada columna tenga al menos 1 número
            if not all(count >= 1 for count in contador_columnas):
                continue
            
            # Validar que ninguna columna tenga más de 3
            if not all(count <= 3 for count in contador_columnas):
                continue
            
            # Validar que el total sea 15
            if sum(contador_columnas) != 15:
                continue
            
            return distribucion
        
        return None
    
    @staticmethod
    def _es_carton_valido(carton: List[List[Optional[int]]]) -> bool:
        """
        Valida que el cartón cumpla todas las reglas de Tómbola
        
        Returns:
            True si el cartón es válido, False en caso contrario
        """
        # 1. Verificar dimensiones (3 filas x 9 columnas)
        if len(carton) != 3:
            logger.warning("Cartón inválido: no tiene 3 filas")
            return False
        
        if any(len(fila) != 9 for fila in carton):
            logger.warning("Cartón inválido: alguna fila no tiene 9 columnas")
            return False
        
        # 2. Cada fila debe tener exactamente 5 números
        for idx, fila in enumerate(carton):
            count = sum(1 for n in fila if n is not None)
            if count != 5:
                logger.warning(f"Cartón inválido: fila {idx} tiene {count} números (debe ser 5)")
                return False
        
        # 3. Total debe ser 15 números
        total = sum(1 for fila in carton for n in fila if n is not None)
        if total != 15:
            logger.warning(f"Cartón inválido: tiene {total} números (debe ser 15)")
            return False
        
        # 4. Cada columna debe tener entre 1 y 3 números
        for col in range(9):
            count = sum(1 for fila in carton if fila[col] is not None)
            if count < 1 or count > 3:
                logger.warning(f"Cartón inválido: columna {col} tiene {count} números (debe ser 1-3)")
                return False
        
        # 5. Verificar rangos correctos por columna
        for col in range(9):
            inicio, fin = TombolaLogic.RANGOS_COLUMNAS[col]
            for fila in range(3):
                num = carton[fila][col]
                if num is not None:
                    if not (inicio <= num <= fin):
                        logger.warning(
                            f"Cartón inválido: número {num} en columna {col} "
                            f"no está en rango {inicio}-{fin}"
                        )
                        return False
        
        # 6. Números ordenados en cada columna (de arriba a abajo)
        for col in range(9):
            numeros_columna = [
                carton[fila][col] 
                for fila in range(3) 
                if carton[fila][col] is not None
            ]
            
            if numeros_columna != sorted(numeros_columna):
                logger.warning(f"Cartón inválido: columna {col} no está ordenada")
                return False
        
        # 7. No debe haber números duplicados
        todos_numeros = [n for fila in carton for n in fila if n is not None]
        if len(todos_numeros) != len(set(todos_numeros)):
            logger.warning("Cartón inválido: hay números duplicados")
            return False
        
        return True
    
    # ============================================
    # SORTEO DE NÚMEROS
    # ============================================
    
    @staticmethod
    def sortear_numero(numeros_sorteados: List[int]) -> Optional[int]:
        """
        Sortea un número del 1 al 90 que no haya sido sorteado
        
        Args:
            numeros_sorteados: Lista de números ya sorteados
            
        Returns:
            Número sorteado (1-90) o None si ya se sortearon todos
        """
        disponibles = [
            n for n in range(1, 91) 
            if n not in numeros_sorteados
        ]
        
        if not disponibles:
            return None
        
        return random.choice(disponibles)
    
    # ============================================
    # MARCAR NÚMEROS EN CARTÓN
    # ============================================
    
    @staticmethod
    def marcar_numero(
        carton: List[List[Optional[int]]], 
        numero: int, 
        marcados: List[int]
    ) -> bool:
        """
        Marca un número en el cartón si existe
        
        Args:
            carton: Matriz 3x9 del cartón
            numero: Número sorteado (1-90)
            marcados: Lista de números ya marcados (se modifica in-place)
            
        Returns:
            True si el número estaba en el cartón y se marcó, False si no
        """
        for fila in carton:
            if numero in fila:
                if numero not in marcados:
                    marcados.append(numero)
                return True
        
        return False
    
    # ============================================
    # VERIFICACIÓN DE PREMIOS (UN SOLO GANADOR POR TIPO)
    # ============================================
    
    @staticmethod
    def verificar_ambo(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> bool:
        """
        Verifica si hay al menos 2 números marcados en UNA MISMA fila
        
        AMBO = Primer jugador en completar 2 números en cualquier fila
        """
        marcados_set = set(marcados)
        
        for fila in carton:
            numeros_fila = [n for n in fila if n is not None]
            marcados_en_fila = sum(1 for n in numeros_fila if n in marcados_set)
            
            if marcados_en_fila >= 2:
                return True
        
        return False
    
    @staticmethod
    def verificar_terno(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> bool:
        """
        Verifica si hay al menos 3 números marcados en UNA MISMA fila
        
        TERNO = Primer jugador en completar 3 números en cualquier fila
        """
        marcados_set = set(marcados)
        
        for fila in carton:
            numeros_fila = [n for n in fila if n is not None]
            marcados_en_fila = sum(1 for n in numeros_fila if n in marcados_set)
            
            if marcados_en_fila >= 3:
                return True
        
        return False
    
    @staticmethod
    def verificar_quaterna(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> bool:
        """
        Verifica si hay al menos 4 números marcados en UNA MISMA fila
        
        QUATERNA = Primer jugador en completar 4 números en cualquier fila
        """
        marcados_set = set(marcados)
        
        for fila in carton:
            numeros_fila = [n for n in fila if n is not None]
            marcados_en_fila = sum(1 for n in numeros_fila if n in marcados_set)
            
            if marcados_en_fila >= 4:
                return True
        
        return False
    
    @staticmethod
    def verificar_cinquina(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> bool:
        """
        Verifica si hay 5 números marcados en UNA MISMA fila (fila completa)
        
        CINQUINA = Primer jugador en completar 5 números (fila completa)
        """
        marcados_set = set(marcados)
        
        for fila in carton:
            numeros_fila = [n for n in fila if n is not None]
            marcados_en_fila = sum(1 for n in numeros_fila if n in marcados_set)
            
            if marcados_en_fila == 5:
                return True
        
        return False
    
    @staticmethod
    def verificar_tombola(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> bool:
        """
        Verifica si todos los 15 números del cartón están marcados
        
        TOMBOLA = Primer jugador en completar los 15 números del cartón
        Este premio FINALIZA LA PARTIDA
        """
        marcados_set = set(marcados)
        
        todos_numeros = [n for fila in carton for n in fila if n is not None]
        
        # Debe haber exactamente 15 números
        if len(todos_numeros) != 15:
            return False
        
        # Todos deben estar marcados
        return all(n in marcados_set for n in todos_numeros)
    
    @staticmethod
    def obtener_estado_premios(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> Dict[str, bool]:
        """
        Obtiene el estado actual de todos los premios para un cartón
        
        Returns:
            Dict con el estado de cada premio:
            {
                'ambo': True/False,
                'terno': True/False,
                'quaterna': True/False,
                'cinquina': True/False,
                'tombola': True/False
            }
        """
        return {
            'ambo': TombolaLogic.verificar_ambo(carton, marcados),
            'terno': TombolaLogic.verificar_terno(carton, marcados),
            'quaterna': TombolaLogic.verificar_quaterna(carton, marcados),
            'cinquina': TombolaLogic.verificar_cinquina(carton, marcados),
            'tombola': TombolaLogic.verificar_tombola(carton, marcados)
        }
    
    # ============================================
    # UTILIDADES
    # ============================================
    
    @staticmethod
    def imprimir_carton(
        carton: List[List[Optional[int]]], 
        marcados: Optional[List[int]] = None
    ) -> str:
        """
        Genera una representación visual del cartón en texto
        
        Args:
            carton: Matriz del cartón
            marcados: Lista de números marcados (opcional)
            
        Returns:
            String con representación visual del cartón
        """
        if marcados is None:
            marcados = []
        
        marcados_set = set(marcados)
        lineas = []
        
        # Encabezado con números de columna
        header = "Col:  " + "  ".join([f"{i+1:2d}" for i in range(9)])
        lineas.append(header)
        lineas.append("-" * 60)
        
        for idx, fila in enumerate(carton):
            fila_str = f"F{idx+1}: "
            for num in fila:
                if num is None:
                    fila_str += "  -- "
                elif num in marcados_set:
                    fila_str += f" [{num:2d}]"
                else:
                    fila_str += f"  {num:2d} "
            lineas.append(fila_str)
        
        return "\n".join(lineas)
    
    @staticmethod
    def generar_codigo_partida() -> str:
        """
        Genera un código único de 6 caracteres para una partida
        
        Returns:
            String de 6 caracteres alfanuméricos en mayúsculas
        """
        import string
        caracteres = string.ascii_uppercase + string.digits
        return ''.join(random.choices(caracteres, k=6))
    
    @staticmethod
    def obtener_estadisticas_carton(
        carton: List[List[Optional[int]]], 
        marcados: List[int]
    ) -> Dict:
        """
        Obtiene estadísticas detalladas del cartón
        
        Returns:
            Dict con estadísticas completas
        """
        marcados_set = set(marcados)
        todos_numeros = [n for fila in carton for n in fila if n is not None]
        marcados_en_carton = [n for n in todos_numeros if n in marcados_set]
        faltantes = [n for n in todos_numeros if n not in marcados_set]
        
        # Estadísticas por fila
        stats_filas = []
        for idx, fila in enumerate(carton):
            nums_fila = [n for n in fila if n is not None]
            marcados_fila = [n for n in nums_fila if n in marcados_set]
            stats_filas.append({
                'fila': idx + 1,
                'total': len(nums_fila),
                'marcados': len(marcados_fila),
                'porcentaje': (len(marcados_fila) / len(nums_fila) * 100) if nums_fila else 0
            })
        
        return {
            'total_numeros': len(todos_numeros),
            'numeros_marcados': len(marcados_en_carton),
            'numeros_faltantes': faltantes,
            'porcentaje_completado': (
                len(marcados_en_carton) / len(todos_numeros) * 100
            ) if todos_numeros else 0,
            'estadisticas_filas': stats_filas,
            'premios': TombolaLogic.obtener_estado_premios(carton, marcados)
        }