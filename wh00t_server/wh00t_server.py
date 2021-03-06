#!/usr/bin/env python3
# wh00t chat server

import ntpath
import os
import sys
import ast
import random
import time
import logging.config
from typing import List, Any, NoReturn, Tuple, Optional
from __init__ import __version__
from dotenv import load_dotenv
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from bin.handles import handles
from wh00t_core.library.utils import package_data, message_time


class Wh00tServer:
    SERVER_VERSION: str = __version__
    HOST: str = ''
    BUFFER_SIZE: int = 1024
    EXIT_STRING: str = '/exit'
    APP_ID: str = 'wh00t_server'
    APP_PROFILE: str = 'app'

    clients: dict = {}
    addresses: dict = {}
    messageHistory: List[str] = []

    def __init__(self, logging_object: Any, home_path: str, port: int):
        self.home_path: str = home_path
        self.logger: Any = logging_object.getLogger(type(self).__name__)
        self.logger.setLevel(logging.INFO)

        self.server: Optional[socket] = None
        self.address: Tuple[str, int] = (self.HOST, port)
        self.handleOptions: List[str] = handles()

    def run(self) -> NoReturn:
        try:
            self.server: socket = socket(AF_INET, SOCK_STREAM)
            self.server.bind(self.address)
            self.server.listen(5)
            self.logger.info(f'Server v{self.SERVER_VERSION} Waiting for connection...')
            accept_thread: Thread = Thread(target=self.accept_incoming_connections)
            accept_thread.start()
            accept_thread.join()
            self.server.close()
        except OSError as os_error:
            self.logger.error(f'Received an OSError: {(str(os_error))}')
            self.server.close()
            sys.exit()
        except KeyboardInterrupt:
            self.logger.warning('Received a KeyboardInterrupt... now exiting')
            self.server.close()
            os._exit(1)

    def accept_incoming_connections(self) -> NoReturn:
        while True:
            user_handle: str = random.choice(self.handleOptions)
            client: Optional[socket] = None
            try:
                client, client_address = self.server.accept()
                self.addresses[client]: Any = client_address
                self.logger.info(f'{client_address[0]}:{client_address[1]} has connected as {user_handle}.')
                connect_group_alert = package_data(self.APP_ID, self.APP_PROFILE, 'broadcast_intro',
                                                   f'~ {self.addresses[client]} has connected'
                                                   f' at {message_time()} ~')
                self.broadcast(bytes(connect_group_alert, 'utf8'))
                Thread(target=self.handle_client, args=(client, user_handle)).start()
            except IOError as io_error:
                self.logger.warning(f'Received IOError: {str(io_error)}')
                self.handle_client_exit(client, user_handle)
                break
            except ConnectionResetError as connection_reset_error:
                self.logger.warning(f'Received ConnectionResetError: {str(connection_reset_error)}')
                self.handle_client_exit(client, user_handle)
                break

    def handle_client(self, client: socket, user_handle: str) -> NoReturn:
        self.clients[client]: str = user_handle

        while True:
            try:
                package: str = client.recv(self.BUFFER_SIZE).decode('utf8', errors='replace')
                package_dict: dict = ast.literal_eval(package)
                if package_dict['message'] == '':
                    self.clients[client]: str = package_dict['id']
                    self.logger.info(f'{self.addresses[client]}:{user_handle} is now {self.clients[client]}.')
                    connect_user_alert = package_data(self.APP_ID, 'app', 'client_intro',
                                                      f'~ You are connected to server '
                                                      f'v{self.SERVER_VERSION}... '
                                                      f'as {self.clients[client]} ~')
                    client.send(bytes(connect_user_alert, 'utf8'))
                    if package_dict['profile'] != 'app':
                        self.client_intro_message_history(client, self.messageHistory)
                elif package_dict['message'] == self.EXIT_STRING:
                    new_package = package_data(self.APP_ID, self.APP_PROFILE, 'client_exit', self.EXIT_STRING)
                    client.send(bytes(new_package, 'utf8'))
                    self.handle_client_exit(client, self.clients[client], package_dict['profile'])
                    break
                else:
                    self.broadcast(bytes(package, 'utf8'))
                    time.sleep(.025)
            except SyntaxError as syntax_error:
                self.logger.warning(f'Received SyntaxError for {self.clients[client]}: '
                                    f'{str(syntax_error)}')
                self.handle_client_exit(client, self.clients[client])
                break
            except IOError as io_error:
                self.logger.warning(f'Received IOError for {self.clients[client]}: {str(io_error)}')
                self.handle_client_exit(client, self.clients[client])
                break
            except ConnectionResetError as connection_reset_error:
                self.logger.warning(f'Received ConnectionResetError for {self.clients[client]}: '
                                    f'{str(connection_reset_error)}')
                self.handle_client_exit(client, self.clients[client])
                break

    def handle_client_exit(self, client: socket, user_handle: str, client_profile: Optional[str] = '') -> NoReturn:
        client.close()
        del self.clients[client]
        self.logger.info(f'{user_handle} has disconnected.')
        if client_profile and client_profile == 'user':
            message = package_data(self.APP_ID, self.APP_PROFILE, 'broadcast_exit',
                                   f'~ {user_handle} has left the chat at {message_time()} ~')
            self.broadcast(bytes(message, 'utf8'))

    def broadcast(self, message: bytes) -> NoReturn:
        for sock in self.clients:
            sock.send(message)

        package_dict: dict = ast.literal_eval(message.decode('utf8', errors='replace'))
        client_profile = package_dict['profile']
        if client_profile and client_profile == 'user':
            self.messageHistory.append(message.decode('utf-8'))
            if len(self.messageHistory) > 35:
                self.messageHistory.pop(0)

    def client_intro_message_history(self, client, message_history) -> NoReturn:
        if len(message_history) > 0:
            history_message_start = package_data(self.APP_ID, self.APP_PROFILE, 'message_history',
                                                 f'~~~ history start ~~~')
            history_message_end = package_data(self.APP_ID, self.APP_PROFILE, 'message_history', f'~~~ history end ~~~')
            client.send(bytes(history_message_start, 'utf8'))
            time.sleep(1.5)
            for historical_message in message_history:
                client.send(bytes(historical_message, 'utf8'))
                time.sleep(1.25)
            client.send(bytes(history_message_end, 'utf8'))


if __name__ == '__main__':
    HOME_PATH: str = ntpath.dirname(__file__)
    logging.config.fileConfig(fname=os.path.join(HOME_PATH, 'bin/logging.conf'), disable_existing_loggers=False)
    logger: Any = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    try:
        load_dotenv()
        SERVER_PORT: int = int(os.getenv('SERVER_PORT'))
        wh00t_server: Wh00tServer = Wh00tServer(logging, HOME_PATH, SERVER_PORT)
        wh00t_server.run()
    except TypeError as type_error:
        logger.error('Received TypeError: Check that the .env project file is configured correctly')
        sys.exit()
