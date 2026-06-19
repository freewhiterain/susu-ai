from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IMEvent:
    platform: str
    sender_id: str
    sender_nick: str
    conversation_id: str
    conversation_type: str   # "1"=私聊 "2"=群聊
    text: str
    raw: dict


class IMAdapter(ABC):
    @abstractmethod
    def verify_request(self, timestamp: str, sign: str) -> bool: ...

    @abstractmethod
    def parse_event(self, body: dict) -> IMEvent: ...

    @abstractmethod
    async def send_message(self, event: IMEvent, content: str, references: list[dict]) -> None: ...
