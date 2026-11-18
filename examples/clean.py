"""Example module where every public function is documented."""


def greet(name):
    """Say hello to one person."""
    return "Hello, %s" % name


class Counter:
    """A small counter."""

    def __init__(self):
        self.value = 0

    def bump(self):
        """Add one to the count."""
        self.value += 1

    def read(self):
        """Return the current count."""
        return self.value
