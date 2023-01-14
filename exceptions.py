class OkStatusError(Exception):
    """Ошибка статуса 200."""

    def __init__(self, text):
        self.txt = text
