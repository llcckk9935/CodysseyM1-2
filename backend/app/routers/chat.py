import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from app.conversations import RateLimited
from app.models import ChatInput
from app.routers.conversations import conversations, session_owner
from app.routers.data import operation, repository
from app.services.chat import get_chat_service
from app.services.summary import summarize

router = APIRouter(tags=['chat'])


def chat_service():
    try:
        return get_chat_service()
    except Exception:
        logging.exception('Chat initialization failed')
        raise HTTPException(503, 'OpenAI API 키와 모델 설정을 확인하세요.')


@router.post('/api/chat')
def chat(payload: ChatInput, owner=Depends(session_owner), data=Depends(repository),
         repo=Depends(conversations), ai=Depends(chat_service)):
    previous = None
    if payload.conversation_id:
        previous = operation(lambda: repo.get(owner, str(payload.conversation_id)))
        if len(previous['messages']) > 98:
            raise HTTPException(409, '대화가 길어졌습니다. 새 대화를 시작하세요.')
    rows = operation(data.list)
    summary = summarize(rows)
    try:
        per_minute = min(10, max(1, int(os.getenv('CHAT_REQUESTS_PER_MINUTE', '5'))))
        daily_max = min(1000, max(1, int(os.getenv('CHAT_DAILY_REQUEST_LIMIT', '100'))))
        repo.reserve_chat(owner, per_minute, daily_max)
    except RateLimited:
        raise HTTPException(429, '요청 한도에 도달했습니다. 잠시 후 또는 다음 UTC 날짜에 다시 시도하세요.')
    except Exception:
        logging.exception('Chat limit check failed')
        raise HTTPException(503, '요청 한도를 확인할 수 없습니다.')
    try:
        result = ai.answer(payload.message, summary, previous['messages'] if previous else [], rows)
        answer, tool_trace = result['answer'], result['tool_trace']
    except Exception:
        logging.exception('OpenAI request failed')
        raise HTTPException(502, 'AI 응답을 완료하지 못했습니다. 잠시 후 다시 시도하세요.')
    messages = [{'role': 'user', 'content': payload.message}, {'role': 'assistant', 'content': answer}]
    try:
        if previous:
            saved = repo.append(owner, previous['id'], previous['revision'], messages,
                                latest_summary=summary, latest_tool_trace=tool_trace, origin='chat')
        else:
            saved = repo.create(owner, payload.message[:60], messages,
                                latest_summary=summary, latest_tool_trace=tool_trace, origin='chat')
        return {'answer': answer, 'conversation_id': saved['id'], 'saved': True, 'summary': summary,
                'tool_trace': tool_trace}
    except Exception:
        logging.exception('Answer generated but conversation save failed')
        return {'answer': answer, 'conversation_id': previous['id'] if previous else None,
                'saved': False, 'summary': summary, 'tool_trace': tool_trace,
                'warning': '답변은 생성됐지만 저장에 실패했습니다. 동시 요청 또는 저장소 오류일 수 있습니다.'}
