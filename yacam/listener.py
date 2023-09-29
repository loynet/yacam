import atexit
import logging

from session import ModSession
import socketio

logger = logging.getLogger(__name__)


class PostListener:
    def __init__(self, session: ModSession, callbacks: list[callable(dict)]):
        self.session = session
        self.callbacks = callbacks

        self.io = socketio.Client(http_session=session)

        @self.io.event
        def connect():
            self.io.emit('room', 'globalmanage-recent-hashed')

        @self.io.on('newPost')
        def new_post(data):
            for c in self.callbacks:
                c(data)

        # Disconnect at exit
        atexit.register(lambda: (
            self.io.disconnect(),
            logger.info("Disconnected")
        ))

    def run(self):
        self.io.connect(f'wss://{self.session.domain}/', transports=['websocket'])
        logger.info("Connected")
        # Blocks until the connection is stopped
        self.io.wait()
