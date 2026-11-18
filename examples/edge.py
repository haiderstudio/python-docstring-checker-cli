"""Example module showing what is NOT flagged."""


def _helper():
    return 1


def outer():
    """A public function with a nested function inside."""
    def inner():
        return 2
    return inner()


async def fetch(url):
    """Fetch one URL."""
    return url


class Widget:
    """A small widget."""

    def __init__(self):
        self.size = 0

    def _reset(self):
        self.size = 0

    def render(self):
        """Draw the widget."""
        return "widget"


class Outer:
    """An outer class."""

    class Inner:
        """An inner class."""

        def show(self):
            """Show the inner class."""
            return "inner"
