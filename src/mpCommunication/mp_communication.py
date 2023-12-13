"""Framework for inter-process communication using messages


Typical usage example:

@dataclasses.dataclass
class SomeMessage(Message):
    name: str
    description: str

@MessageHandler
class ExampleProcess(mp.Process):

    def __init__(self, connection: mp.Queue):
        super().__init__()

        self.connection = connection

    def run(self):
        loop(self.update, "Slave process")

    def update(self):
        self.handle_messages(self.connection)

    @OnMessage(SomeMessage)
    def print_pid(self, message: SomeMessage):
        print(message.name, flush=True)
        print(wait_for_message(self.connection, SomeMessage).description, flush=True)  # Wait for another message
        self.connection.put(SomeMessage(name="Foo", description="A Foo"))  # Send back the same message
"""
import multiprocessing as mp
import logging
import dataclasses
import queue
import inspect
from typing import Type, TypeVar

logger = logging.getLogger("mpCommunication")


@dataclasses.dataclass
class Message:
    """Base class for messages

    Attributes:
        sender: The name of the process were this message was created.
    """
    sender: str = dataclasses.field(default_factory=lambda: mp.current_process().name, init=False)


def OnMessage(message: Type[Message]):
    """Decorator to register a method as handler for the given message.

    Args:
        message: The message to handle.
    """

    def wrapper(func):
        func._message_handler = message
        return func

    return wrapper


def MessageHandler(cls):
    """Class decorator to give a class the ability to handle messages."""
    # Add a dictionary containing all the message handlers later used to handle messages
    cls._message_handlers = dict()
    for method_name in dir(cls):
        try:
            method = getattr(cls, method_name)
            if hasattr(method, "_message_handler"):
                cls._message_handlers.update({getattr(method, "_message_handler"): method})
        except AttributeError:  # Workaround for some classes that expect an instance due a descriptor
            pass

    def handle_messages(self, connection_queue: mp.Queue) -> None:  # noqa (disables IDE inspecting for self)
        """Handles messages available on the multiprocessing connection queue.

        Args:
            connection_queue: The multiprocessing queue to receive and handle messages from.
        """
        try:
            while True:
                message = connection_queue.get_nowait()  # Get a new messages until queue is empty
                logger.debug(f"Handling message: {message}")
                try:
                    func = self._message_handlers[message.__class__]  # Get the message handler method
                    try:
                        inspect.signature(func).parameters["message"]  # Check to see if the method expects the message
                    except KeyError:
                        func(self)
                    else:
                        func(self, message=message)
                except KeyError:
                    logger.debug(f"No handler registered for message: {message}")
        except queue.Empty:
            return

    # Add method to the class
    setattr(cls, "handle_messages", handle_messages)
    return cls


# Type annotation here ensures that autocompletion and type checks work for the message returned inline with the message
# waited for

T = TypeVar("T", bound=Message)

def wait_for_message(connection_queue: mp.Queue, messages: list[Type[T]] | Type[T], timeout: float | None = None) -> T:
    """Wait until the message is received, anything else received in the meantime is discarded for now.

    Args:
        connection_queue: The multiprocessing queue where to wait for the messages.
        messages: The message(s) to wait for.
        timeout: If not None blocks at most `timeout` getting any message from `connection_queue` before raising
            `queue.Empty`.

    Returns:
        The received message waited for.
    """

    if type(messages) is not list:
        messages = [messages]

    logger.debug(f"Waiting for messages: {[message.__name__ for message in messages]}")
    while True:
        received_message = connection_queue.get(timeout=timeout)

        if type(received_message) in messages:
            return received_message
        logger.debug(f"Discarding {received_message}")
