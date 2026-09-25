"""Pytest-only network guard. MockTransport/ASGI tests remain usable."""
import socket


def pytest_configure(config):
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex
    def connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError('OFFLINE_ONLY: real network connection forbidden')
        return original(self, address)
    def connect_ex(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError('OFFLINE_ONLY: real network connection forbidden')
        return original_ex(self, address)
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
