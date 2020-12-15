#!/usr/bin/env python3
# wh00t chat server

import ntpath
import os
import random
import time
import logging.config
from __init__ import __version__
from dotenv import load_dotenv
from datetime import datetime
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from bin.handles import handles


class Wh00tServer:
    SERVER_VERSION = __version__
    HOST = ''
    BUFFER_SIZE = 1024
    EXIT_STRING = '/exit'

    clients = {}
    addresses = {}
    messageHistory = []

    def __init__(self, logging_object, home_path, port):
        self.home_path = home_path
        self.logger = logging_object.getLogger(type(self).__name__)
        self.logger.setLevel(logging.INFO)

        self.server = None
        self.address = (self.HOST, port)
        self.handleOptions = handles()

    def run(self):
        try:
            self.server = socket(AF_INET, SOCK_STREAM)
            self.server.bind(self.address)
            self.server.listen(5)
            self.logger.info(f'Server v{self.SERVER_VERSION} Waiting for connection...')
            accept_thread = Thread(target=self.accept_incoming_connections)
            accept_thread.start()
            accept_thread.join()
            self.server.close()
        except OSError as os_error:
            self.logger.error(f'Received an OSError: {(str(os_error))}')
            self.server.close()
            exit()
        except KeyboardInterrupt:
            self.logger.warning('Received a KeyboardInterrupt... now exiting')
            self.server.close()
            os._exit(1)

    @staticmethod
    def message_time():
        return datetime.fromtimestamp(time.time()).strftime('%m/%d %H:%M')

    def accept_incoming_connections(self):
        while True:
            user_handle = random.choice(self.handleOptions)
            client = None
            try:
                client, client_address = self.server.accept()
                connected_text = f'~ You are connected to server v{self.SERVER_VERSION}... as {user_handle} ~'
                intro_help_message = f'\n~ Type \'{self.EXIT_STRING}\' or press ESC key to exit ~'
                self.logger.info(f'{client_address[0]}:{client_address[1]} has connected as {user_handle}.')
                client.send(bytes(connected_text, 'utf8'))
                client.send(bytes(intro_help_message, 'utf8'))

                for historical_message in self.messageHistory:
                    client.send(bytes(historical_message, 'utf8'))

                self.addresses[client] = client_address
                Thread(target=self.handle_client, args=(client, user_handle)).start()
            except IOError as io_error:
                self.logger.warning(f'Received IOError for {user_handle}: {str(io_error)}')
                self.handle_client_exit(client, user_handle)
                break
            except ConnectionResetError as connection_reset_error:
                self.logger.warning(f'Received ConnectionResetError for {user_handle}: {str(connection_reset_error)}')
                self.handle_client_exit(client, user_handle)
                break

    def handle_client(self, client, user_handle):
        self.broadcast(bytes(f'\n~ {user_handle} has connected at {self.message_time()} ~', 'utf8'))
        self.clients[client] = user_handle

        while True:
            try:
                message = client.recv(self.BUFFER_SIZE)
                if message != bytes(self.EXIT_STRING, 'utf8'):
                    self.broadcast(message, f'\n| {user_handle} ({self.message_time()}) | ')
                    time.sleep(.025)
                else:
                    client.send(bytes(self.EXIT_STRING, 'utf8'))
                    self.handle_client_exit(client, user_handle)
                    break
            except IOError as io_error:
                self.logger.warning(f'Received IOError for {user_handle}: {str(io_error)}')
                self.handle_client_exit(client, user_handle)
                break
            except ConnectionResetError as connection_reset_error:
                self.logger.warning(f'Received ConnectionResetError for {user_handle}: {str(connection_reset_error)}')
                self.handle_client_exit(client, user_handle)
                break

    def handle_client_exit(self, client, user_handle):
        client.close()
        del self.clients[client]
        self.logger.info(f'{user_handle} has disconnected.')
        self.broadcast(bytes(f'\n~ {user_handle} has left the chat at {self.message_time()} ~', 'utf8'))

    def broadcast(self, message, prefix=''):
        for sock in self.clients:
            sock.send(bytes(prefix, 'utf8') + message)
        self.messageHistory.append(prefix + message.decode('utf-8'))
        if len(self.messageHistory) > 35:
            self.messageHistory.pop(0)


if __name__ == '__main__':
    HOME_PATH = ntpath.dirname(__file__)
    logging.config.fileConfig(fname=os.path.join(HOME_PATH, 'bin/logging.conf'), disable_existing_loggers=False)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    try:
        load_dotenv()
        SERVER_PORT = int(os.getenv('SERVER_PORT'))
        wh00t_server = Wh00tServer(logging, HOME_PATH, SERVER_PORT)
        wh00t_server.run()
    except TypeError as type_error:
        logger.error('Received TypeError: Check that the .env project file is configured correctly')
        exit()
