from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from uuid import UUID


class DataInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date: date
    value: Decimal = Field(gt=0, max_digits=10, decimal_places=2, allow_inf_nan=False)
    memo: str = Field(default='', max_length=1000)


def serialize_input(payload: DataInput):
    return {'date': payload.date.isoformat(), 'value': float(payload.value), 'memo': payload.memo}


class MessageInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class ConversationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(default='새 대화', min_length=1, max_length=100)
    messages: list[MessageInput] = Field(min_length=1, max_length=100)


class ChatInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
