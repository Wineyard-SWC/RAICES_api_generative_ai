import sys
import asyncio

from typing import Optional,Callable

class ThinkingSteps:
    """
    Clase para manejar la simulación de pasos de pensamiento durante la generación de respuestas.
    """
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        """
        Inicializa el simulador de pensamiento.
        
        Args:
            callback: Función opcional que se llamará con cada paso de pensamiento.
                     Si es None, se imprimirá el paso en sys.stdout.
        """
        self.callback = callback or self._default_callback
        self.steps = []
        self._current_step = None
    
    def _default_callback(self, message: str):
        """Callback por defecto que imprime en la consola"""
        sys.stdout.write(f"\r{message}")
        sys.stdout.flush()
    
    async def add_step(self, message: str, duration: float = 1.0):
        """
        Añade un paso de pensamiento y lo muestra durante la duración especificada.
        
        Args:
            message: El mensaje del paso de pensamiento.
            duration: La duración en segundos antes de continuar al siguiente paso.
        """
        full_message = f"⚙️ {message}..."
        self.steps.append(full_message)
        self._current_step = full_message
        self.callback(full_message)
        await asyncio.sleep(duration)
    
    async def complete(self, final_message: str = "✅ Respuesta generada!"):
        """
        Completa la secuencia de pasos de pensamiento.
        
        Args:
            final_message: Mensaje final a mostrar.
        """
        self.callback(final_message)
        self._current_step = None
        # Limpiar la línea actual en la terminal
        if self.callback == self._default_callback:
            sys.stdout.write("\n")
            sys.stdout.flush()
