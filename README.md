# multiprocessing-messaging
A message passing and event based communication system for Python multiprocessing processes.


## Install
Use Pip to install this package.
```bash
> pip install pip install https://github.com/Abd0s/multiprocessing-messaging
````
> 
## Example usage
The code bellow shows a minimal usage example. Messages are defined as subclasses of
the `Message` base class. Message handlers within process are registered using the `OnMessage`
decorator and the process class is marked with the `MessageHandler` decorator to inject the message
handling functionality.

Additionally, a `wait_for_message` function is available to wait for messages from other process
and synchronize processes.

Received messages are automatically parsed into the defined message dataclasses and optionally
made available to the registered message handler methods.
```python
import mpCommunication
import multiprocessing as mp

@dataclasses.dataclass
class SomeMessage(mpCommunication.Message):
    name: str
    description: str

@mpCommunication.MessageHandler
class ExampleProcess(mp.Process):

    def __init__(self, connection: mp.Queue):
        super().__init__()

        self.connection = connection

    def run(self):
        while True:
            self.update()

    def update(self):
        self.handle_messages(self.connection)

    @mpCommunication.OnMessage(SomeMessage)
    def print_pid(self, message: SomeMessage):
        print(message.name, flush=True)
        print(mpCommunication.wait_for_message(self.connection, SomeMessage).description, flush=True)  # Wait for another message
        self.connection.put(SomeMessage(name="Foo", description="A Foo"))  # Send back the same message
```

## Documentation
Documentation exists in the form of Google style docstrings within the code itself.

## Caveats
Because the `handle_message()` method needs to continuously run to handle messages, message handlers
should be short of execution and not block. Otherwise, message handling might get blocked or delayed.

The `wait_for_message()` function discards any other message received other than the one waited for due
current implementation details. Messages might get lost if not taken care of.

