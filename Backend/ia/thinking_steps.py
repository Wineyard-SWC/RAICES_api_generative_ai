"""
Nombre:
    thinking_steps.py

Descripción:
    Módulo que simula pasos de pensamiento durante la generación de respuestas, 
    proporcionando una experiencia más fluida y realista al usuario.

    Module that simulates thinking steps during response generation,
    offering a smoother and more realistic user experience.

Autor / Author:
    Abdiel Fritsche Barajas

Fecha de creación / Created: 2025-03-28
Última modificación / Last modified: 2025-03-29
Versión / Version: 1.0.0
"""

# ────────────────────────────────
# Librerías estándar / Standard libraries
import sys
import asyncio
from typing import Optional,Callable


class ThinkingSteps:
    """
    Clase para manejar la simulación de pasos de pensamiento durante la generación de respuestas.

    Class for handling the simulation of thinking steps during response generation.
    """

    __slots__ = ["callback",
                 "steps",
                 "_current_step",
                 ]
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        """
        Inicializa el simulador de pensamiento.

        Initializes the thinking simulator.

        Args:
            callback (Callable, optional): Función opcional que se llamará en cada paso.
                                           Si no se proporciona, se imprime en consola.
                                           /
                                           Optional function to be called at each step.
                                           If not provided, it will print to the console.
        """
        self.callback = callback or self._default_callback
        self.steps = []
        self._current_step = None
    
    def _default_callback(self, message: str):
        """
        Callback por defecto que imprime el mensaje en consola.

        Default callback that prints the message to the console.
        """
        sys.stdout.write(f"\r{message}")
        sys.stdout.flush()
    
    async def add_step(self, message: str, duration: float = 1.0):
        """
        Añade un nuevo paso de pensamiento, muestra el mensaje y espera un tiempo determinado.

        Adds a new thinking step, displays the message and waits a specified duration.

        Args:
            message (str): Mensaje del paso a mostrar / Step message to display.
            duration (float): Tiempo de espera en segundos / Delay time in seconds.
        """
        full_message = f"⚙️ {message}..."
        self.steps.append(full_message)
        self._current_step = full_message
        self.callback(full_message)
        await asyncio.sleep(duration)
    
    async def complete(self, final_message: str = "✅ Respuesta generada!"):
        """
        Completa la secuencia de pensamiento mostrando un mensaje final.

        Completes the thinking sequence by displaying a final message.

        Args:
            final_message (str): Mensaje final que se mostrará / Final message to display.
        """
        self.callback(final_message)
        self._current_step = None
        if self.callback == self._default_callback:
            sys.stdout.write("\n")
            sys.stdout.flush()
