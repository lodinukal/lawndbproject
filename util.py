from typing import Callable


# Signal class to handle events, can also accept arguments
class Signal:
    _handlers: list[Callable]

    def __init__(self):
        self._handlers = []

    def connect(self, handler: Callable):
        """Connect a handler to the signal."""
        self._handlers.append(handler)

    def emit(self):
        """Emit the signal to all connected handlers."""
        for handler in self._handlers:
            handler()
