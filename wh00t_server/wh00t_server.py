#!/usr/bin/env python3
# wh00t chat server

import ntpath
import os
import sys
import random
import logging.config
import time
from typing import List, Any, Tuple, Optional
from __init__ import __version__
from dotenv import load_dotenv
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from bin.handles import handles
from wh00t_core.library.network_utils import NetworkUtils


class Wh00tServer:
    SERVER_VERSION: str = __version__
    HOST: str = ''
    BUFFER_SIZE: int = NetworkUtils.BUFFER_SIZE
    EXIT_STRING: str = '/exit'
    APP_ID: str = 'wh00t_server'
    APP_PROFILE: str = 'app'

    clients: dict = {}
    addresses: dict = {}
    messageHistory: List[str] = []

    def __init__(self, logging_object: Any, home_path: str, port: int):
        self.home_path: str = home_path
        self.logger: logging.Logger = logging_object.getLogger(type(self).__name__)
        self.logger.setLevel(logging.INFO)

        self.server: Optional[socket] = None
        self.address: Tuple[str, int] = (self.HOST, port)
        self.handleOptions: List[str] = handles()

    def run(self) -> None:
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

    def accept_incoming_connections(self) -> None:
        while True:
            user_handle: str = random.choice(self.handleOptions)
            client: Optional[socket] = None
            try:
                client, client_address = self.server.accept()
                self.addresses[client]: Any = client_address
                self.logger.info(f'{client_address[0]}:{client_address[1]} has connected as {user_handle}.')
                self.broadcast(NetworkUtils.package_data(self.APP_ID, self.APP_PROFILE, 'broadcast_intro',
                                                         f'~ {self.addresses[client]} has connected'
                                                         f' at {NetworkUtils.message_time()} ~'))
                Thread(target=self.handle_client, args=(client, user_handle)).start()
            except IOError as io_error:
                self.logger.warning(f'Received IOError: {str(io_error)}')
                self.handle_client_exit(client, user_handle)
                break
            except ConnectionResetError as connection_reset_error:
                self.logger.warning(f'Received ConnectionResetError: {str(connection_reset_error)}')
                self.handle_client_exit(client, user_handle)
                break

    def handle_client(self, client: socket, user_handle: str) -> None:
        self.clients[client]: str = user_handle

        while True:
            try:
                package: str = NetworkUtils.unpack_byte(client.recv(self.BUFFER_SIZE))
                if len(package) == 0:
                    self.handle_client_exit(client, self.clients[client])
                    break
                else:
                    package_dict_list: List[dict] = NetworkUtils.unpack_data(package)

                    for package_dict in package_dict_list:
                        if package_dict['message'] == '':
                            self.clients[client]: str = package_dict['id']
                            self.logger.info(f'{self.addresses[client]}:{user_handle} is now {self.clients[client]}.')
                            client.send(NetworkUtils.byte_package(self.APP_ID, 'app', 'client_intro',
                                                                  f'~ You are connected to wh00t server '
                                                                  f'v{self.SERVER_VERSION}... '
                                                                  f'as {self.clients[client]} ~'))
                            if package_dict['profile'] != 'app':
                                self.client_intro_message_history(client, self.messageHistory)
                        elif package_dict['message'] == self.EXIT_STRING:
                            client.send(NetworkUtils.byte_package(self.APP_ID, self.APP_PROFILE, 'client_exit',
                                                                  self.EXIT_STRING))
                            self.handle_client_exit(client, self.clients[client], package_dict['profile'])
                            return
                        else:
                            self.broadcast(NetworkUtils.package_dict(package_dict))
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

    def handle_client_exit(self, client: socket, user_handle: str, client_profile: Optional[str] = '') -> None:
        client.close()
        del self.clients[client]
        self.logger.info(f'{user_handle} has disconnected.')
        if client_profile and client_profile == 'user':
            self.broadcast(NetworkUtils.package_data(self.APP_ID, self.APP_PROFILE, 'broadcast_exit',
                                                     f'~ {user_handle} has left the chat at '
                                                     f'{NetworkUtils.message_time()} ~'))

    def broadcast(self, message_package: str) -> None:
        for sock in self.clients:
            sock.send(NetworkUtils.utf8_bytes(message_package))
        self.add_to_history(NetworkUtils.unpack_data(message_package)[0])

    def add_to_history(self, package_dict: dict) -> None:
        client_profile: str = package_dict['profile']
        if client_profile and client_profile == 'user':
            self.messageHistory.append(NetworkUtils.package_dict(package_dict))
            if len(self.messageHistory) > 35:
                self.messageHistory.pop(0)

    def client_intro_message_history(self, client: socket, message_history: List[str]) -> None:
        if len(message_history) > 0:
            counter: int = 1
            client.send(NetworkUtils.byte_package(self.APP_ID, self.APP_PROFILE, 'message_history',
                                                  f'~~~ history start ~~~'))
            for historical_message in message_history:
                if counter % 5 == 0:
                    time.sleep(.9)
                client.send(NetworkUtils.utf8_bytes(historical_message))
                counter += 1
                time.sleep(.1)
            client.send(NetworkUtils.byte_package(self.APP_ID, self.APP_PROFILE, 'message_history',
                                                  f'~~~ history end ~~~'))


if __name__ == '__main__':
    HOME_PATH: str = ntpath.dirname(__file__)
    logging.config.fileConfig(fname=os.path.join(HOME_PATH, 'bin/logging.conf'), disable_existing_loggers=False)
    logger: logging.Logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    try:
        load_dotenv()
        SERVER_PORT: int = int(os.getenv('SERVER_PORT'))
        wh00t_server: Wh00tServer = Wh00tServer(logging, HOME_PATH, SERVER_PORT)
        wh00t_server.run()
    except TypeError as type_error:
        logger.error('Received TypeError: Check that the .env project file is configured correctly')
        sys.exit()
