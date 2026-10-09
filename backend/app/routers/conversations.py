import hashlib
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from app.conversations import get_conversations
from app.models import ConversationInput
from app.routers.data import operation

router = APIRouter(prefix='/api/conversations', tags=['conversations'])


def session_owner(x_session_token: str = Header(default='')):
    if len(x_session_token) < 32 or len(x_session_token) > 200:
        raise HTTPException(401, '대화 세션 토큰이 필요합니다.')
    return hashlib.sha256(x_session_token.encode()).hexdigest()


def conversations():
    try:
        return get_conversations()
    except Exception:
        logging.exception('Conversation storage initialization failed')
        raise HTTPException(503, '대화 저장소 연결 설정을 확인하세요.')


def public(record):
    return {k: v for k, v in record.items() if k != 'owner'}


@router.post('', status_code=201)
def save(payload: ConversationInput, owner=Depends(session_owner), repo=Depends(conversations)):
    messages = [m.model_dump() for m in payload.messages]
    return public(operation(lambda: repo.create(owner, payload.title, messages, origin='manual')))


@router.get('')
def listing(owner=Depends(session_owner), repo=Depends(conversations)):
    return operation(lambda: repo.list(owner))


@router.get('/{identifier}')
def get(identifier: UUID, owner=Depends(session_owner), repo=Depends(conversations)):
    return public(operation(lambda: repo.get(owner, str(identifier))))


@router.delete('/{identifier}', status_code=204)
def delete(identifier: UUID, owner=Depends(session_owner), repo=Depends(conversations)):
    operation(lambda: repo.delete(owner, str(identifier)))
    return Response(status_code=204)
