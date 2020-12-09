#!/usr/bin/env python3
# wh00t chat server

import os
import random
import time
from datetime import datetime
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
from bin.Data import handles


class Wh00tServer:
    SERVER_VERSION = '2.0.0'
    HOST = ''
    BUFFER_SIZE = 1024
    EXIT_STRING = '/exit'

    server = None
    address = None
    clients = {}
    addresses = {}
    handleOptions = handles()
    messageHistory = []

    def __init__(self, port):
        self.address = (self.HOST, port)

    def run(self):
        try:
            self.server = socket(AF_INET, SOCK_STREAM)
            self.server.bind(self.address)
            self.server.listen(5)
            print('Server v{} Waiting for connection...'.format(self.SERVER_VERSION))
            accept_thread = Thread(target=self.accept_incoming_connections)
            accept_thread.start()
            accept_thread.join()
            self.server.close()
        except OSError as e:
            print('Received an OSError', e)
            self.server.close()
            os._exit(1)
        except KeyboardInterrupt:
            print('Received a KeyboardInterrupt... now exiting')
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
                connected_text = '~ You are connected to server v{}... as {} ~'.format(self.SERVER_VERSION, user_handle)
                intro_help_message = '\n~ Type \'{}\' or press ESC key to exit ~'.format(self.EXIT_STRING)
                print('{}:{} has connected as {}.'.format(client_address[0], client_address[1], user_handle))
                client.send(bytes(connected_text, 'utf8'))
                client.send(bytes(intro_help_message, 'utf8'))

                for historical_message in self.messageHistory:
                    client.send(bytes(historical_message, 'utf8'))

                self.addresses[client] = client_address
                Thread(target=self.handle_client, args=(client, user_handle)).start()
            except IOError as io_error:
                print("Received IOError for {}: ".format(user_handle), io_error)
                self.handle_client_exit(client, user_handle)
                break
            except ConnectionResetError as connection_reset_error:
                print("Received ConnectionResetError for {}: ".format(user_handle), connection_reset_error)
                self.handle_client_exit(client, user_handle)
                break

    def handle_client(self, client, user_handle):
        self.broadcast(bytes('\n~ {} has connected at {} ~'.format(user_handle, self.message_time()), 'utf8'))
        self.clients[client] = user_handle

        while True:
            try:
                message = client.recv(self.BUFFER_SIZE)
                if message != bytes(self.EXIT_STRING, 'utf8'):
                    self.broadcast(message, '\n| {} ({}) | '.format(user_handle, self.message_time()))
                    time.sleep(.025)
                else:
                    client.send(bytes(self.EXIT_STRING, 'utf8'))
                    self.handle_client_exit(client, user_handle)
                    break
            except IOError as io_error:
                print("Received IOError for {}: ".format(user_handle), io_error)
                self.handle_client_exit(client, user_handle)
                break
            except ConnectionResetError as connection_reset_error:
                print("Received ConnectionResetError for {}: ".format(user_handle), connection_reset_error)
                self.handle_client_exit(client, user_handle)
                break

    def handle_client_exit(self, client, user_handle):
        client.close()
        del self.clients[client]
        print('%s has disconnected.' % user_handle)
        self.broadcast(bytes('\n~ {} has left the chat at {} ~'.format(user_handle, self.message_time()), 'utf8'))

    def broadcast(self, message, prefix=''):
        for sock in self.clients:
            sock.send(bytes(prefix, 'utf8') + message)
        self.messageHistory.append(prefix + message.decode('utf-8'))
        if len(self.messageHistory) > 30:
            self.messageHistory.pop(0)


if __name__ == '__main__':
    wh00t_server = Wh00tServer(3001)
    wh00t_server.run()
