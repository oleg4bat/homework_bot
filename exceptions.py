class BaseError(Exception):
    """Ошибка статуса 200."""

    def __init__(self, text, code):
        self.txt = text
        self.code = code

class OkStatusError(BaseError):
    pass