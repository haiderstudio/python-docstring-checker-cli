"""Example module with three undocumented public functions."""


def greet(name):
    """Say hello to one person."""
    return "Hello, %s" % name


def add(a, b):
    return a + b


class Counter:
    """A small counter."""

    def __init__(self):
        self.value = 0

    def bump(self):
        self.value += 1

    def read(self):
        """Return the current count."""
        return self.value


def blank():
    """"""
    return None
