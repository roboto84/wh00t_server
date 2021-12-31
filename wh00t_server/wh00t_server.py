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
from wh00t_core.library.network_commons import NetworkCommons


class Wh00tServer:
    _SERVER_VERSION: str = __version__
    _HOST: str = ''

    _network_utils: NetworkUtils = NetworkUtils()
    _network_commons: NetworkCommons = NetworkCommons()
    _clients: dict = {}
    _messageHistory: List[str] = []

    def __init__(self, logging_object: Any, port: int):
        self._logger: logging.Logger = logging_object.getLogger(type(self).__name__)
        self._logger.setLevel(logging.INFO)

        self._server: Optional[socket] = None
        self._address: Tuple[str, int] = (self._HOST, port)
        self._handleOptions: List[str] = handles()

    def run(self) -> None:
        try:
            self._server: socket = socket(AF_INET, SOCK_STREAM)
            self._server.bind(self._address)
            self._server.listen(5)
            self._logger.info(f'Server v{self._SERVER_VERSION} Waiting for connection...')
            accept_thread: Thread = Thread(target=self._accept_incoming_connections)
            accept_thread.start()
            accept_thread.join()
            self._server.close()
        except OSError as os_error:
            self._logger.error(f'Received an OSError: {(str(os_error))}')
            self._server.close()
            sys.exit()
        except KeyboardInterrupt:
            self._logger.warning('Received a KeyboardInterrupt... now exiting')
            self._server.close()
            os._exit(1)

    def _accept_incoming_connections(self) -> None:
        while True:
            client: Optional[socket] = None
            init_client_info: dict = {
                'handle': random.choice(self._handleOptions),
                'profile': 'init:user',
                'ip_address': '0.0.0.0'
            }
            try:
                client, init_client_info['ip_address'] = self._server.accept()
                self._logger.info(f'{init_client_info["ip_address"]} has connected as {init_client_info["handle"]}.')
                self._broadcast(self._server_package('debug:broadcast_intro',
                                                     f'~ {init_client_info["ip_address"]} has connected'
                                                     f' at {NetworkUtils.message_time()} ~'))
                Thread(target=self._handle_client, args=(client, init_client_info)).start()
            except IOError as io_error:
                self._logger.warning(f'Received IOError: {str(io_error)}')
                self._handle_client_exit(client, init_client_info)
                break
            except ConnectionResetError as connection_reset_error:
                self._logger.warning(f'Received ConnectionResetError: {str(connection_reset_error)}')
                self._handle_client_exit(client, init_client_info)
                break

    def _handle_client(self, client: socket, init_client_info: dict) -> None:
        while True:
            try:
                package: str = self._network_utils.unpack_byte(client.recv(self._network_commons.get_buffer_size()))
                if len(package) == 0:
                    self._handle_client_exit(client, self._clients[client])
                    break
                else:
                    package_dict_list: List[dict] = NetworkUtils.unpack_data(package)
                    for package_dict in package_dict_list:
                        if package_dict['message'] == '':
                            new_client_handle: str = package_dict['username']
                            new_client_profile: str = package_dict['profile']
                            message_category: str = 'broadcast_intro'
                            client_is_app: bool = new_client_profile == self._network_commons.get_app_profile()
                            if client_is_app:
                                message_category: str = f'debug:{message_category}'
                            self._broadcast(self._server_package(message_category,
                                                                 f'~ {new_client_handle} has connected'
                                                                 f' at {NetworkUtils.message_time()} ~'))
                            self._clients[client]: dict = {
                                'handle': new_client_handle,
                                'profile': new_client_profile,
                                'ip_address': init_client_info['ip_address']
                            }
                            self._logger.info(
                                f'{init_client_info["ip_address"]}:{init_client_info["handle"]} '
                                f'is now {self._clients[client]["handle"]}.')
                            client.send(self._network_utils.utf8_bytes(
                                self._server_package('client_intro',
                                                     f'~ You are connected to wh00t server '
                                                     f'v{self._SERVER_VERSION}... '
                                                     f'as {self._clients[client]["handle"]} ~')))
                            if not client_is_app:
                                self._client_intro_message_history(client, self._messageHistory)
                        elif package_dict['message'] == self._network_commons.get_exit_command():
                            client.send(self._network_utils.utf8_bytes(
                                self._server_package('client_exit', self._network_commons.get_exit_command())))
                            self._handle_client_exit(client, self._clients[client])
                            return
                        else:
                            self._broadcast(NetworkUtils.package_dict(package_dict))
            except SyntaxError as syntax_error:
                self._logger.warning(f'Received SyntaxError for {self._clients[client]["handle"]}: '
                                     f'{str(syntax_error)}')
                self._handle_client_exit(client, self._clients[client])
                break
            except IOError as io_error:
                self._logger.warning(f'Received IOError for {self._clients[client]["handle"]}: {str(io_error)}')
                self._handle_client_exit(client, self._clients[client])
                break
            except ConnectionResetError as connection_reset_error:
                self._logger.warning(f'Received ConnectionResetError for {self._clients[client]["handle"]}: '
                                     f'{str(connection_reset_error)}')
                self._handle_client_exit(client, self._clients[client])
                break

    def _handle_client_exit(self, client: socket, client_info: dict) -> None:
        client.close()
        del self._clients[client]
        self._logger.info(f'{client_info["handle"]} has disconnected.')
        if client_info['profile'] and client_info['profile'] == self._network_commons.get_user_profile():
            self._broadcast(self._server_package('broadcast_exit',
                                                 f'~ {client_info["handle"]} has left the chat at '
                                                 f'{NetworkUtils.message_time()} ~'))

    def _broadcast(self, message_package: str) -> None:
        unpacked_package: dict = self._network_utils.unpack_data(message_package)[0]
        secret_message: bool = self._secret_message(unpacked_package['profile'], unpacked_package['message'])
        for sock in self._clients:
            if not secret_message or (secret_message and
                                      self._clients[sock]['profile'] == self._network_commons.get_user_profile()):
                sock.send(self._network_utils.utf8_bytes(message_package))
        if not secret_message and unpacked_package['profile'] == self._network_commons.get_user_profile():
            self._add_to_history(self._network_utils.unpack_data(message_package)[0])

    def _add_to_history(self, package_dict: dict) -> None:
        max_message_history: int = 35
        self._messageHistory.append(NetworkUtils.package_dict(package_dict))
        if len(self._messageHistory) > max_message_history:
            self._messageHistory.pop(0)

    def _client_intro_message_history(self, client: socket, message_history: List[str]) -> None:
        if len(message_history) > 0:
            counter: int = 1
            message_category: str = 'message_history'
            client.send(self._network_utils.utf8_bytes(self._server_package(message_category, f'~ history start ~')))
            for historical_message in message_history:
                if counter % 5 == 0:
                    time.sleep(.9)
                client.send(self._network_utils.utf8_bytes(historical_message))
                counter += 1
                time.sleep(.1)
            client.send(self._network_utils.utf8_bytes(self._server_package(message_category, f'~ history end ~')))

    def _server_package(self, message_category: str, message: str) -> str:
        return self._network_utils.package_data(self._network_commons.get_server_id(),
                                                self._network_commons.get_app_profile(),
                                                message_category,
                                                message)

    def _secret_message(self, client_profile: str, message: str) -> bool:
        return client_profile == self._network_commons.get_user_profile() and \
               self._network_commons.get_destruct_command() in message


if __name__ == '__main__':
    HOME_PATH: str = ntpath.dirname(__file__)
    logging.config.fileConfig(fname=os.path.join(HOME_PATH, 'bin/logging.conf'), disable_existing_loggers=False)
    logger: logging.Logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    try:
        load_dotenv()
        SERVER_PORT: int = int(os.getenv('SERVER_PORT'))
        wh00t_server: Wh00tServer = Wh00tServer(logging, SERVER_PORT)
        wh00t_server.run()
    except TypeError as type_error:
        logger.error('Received TypeError: Check that the .env project file is configured correctly')
        sys.exit()
