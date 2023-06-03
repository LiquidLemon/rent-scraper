import abc
from typing import Optional

import requests


class NotificationHandler(abc.ABC):
    @abc.abstractmethod
    def __init__(self, key: str):
        ...

    @staticmethod
    def get_handler(handler_type: str, key: str) -> "NotificationHandler":
        return HANDLERS[handler_type](key)

    @abc.abstractmethod
    def send(self, message: str, title: str, url: Optional[str] = None):
        ...


class PushbulletHandler(NotificationHandler):
    token: str

    def send(self, message: str, title: str, url: Optional[str] = None):
        payload = {
            "type": "link",
            "title": title,
            "body": message,
            "url": url,
        }

        headers = {"Access-Token": self.token}

        response = requests.post(
            "https://api.pushbullet.com/v2/pushes", json=payload, headers=headers
        )
        assert response.ok

    def __init__(self, key: str):
        self.token = key


HANDLERS = {"pushbullet": PushbulletHandler}
