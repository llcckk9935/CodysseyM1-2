from copy import deepcopy
from uuid import uuid4
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repository import Missing, Conflict
from app.conversations import RateLimited
from app.routers.data import repository
from app.routers.conversations import conversations
from app.routers.chat import chat_service
from app.services.chat import ChatService, ChatUnavailable


class Conversations:
    def __init__(self):
        self.rows = {}
        self.blocked = False
        self.fail_save = False
    def create(self, owner, title, messages, **extra):
        if self.fail_save:
            raise RuntimeError()
        i = str(uuid4())
        self.rows[i] = {'id': i, 'owner': owner, 'title': title,
                        'messages': deepcopy(messages), 'revision': 1, **extra}
        return deepcopy(self.rows[i])
    def get(self, owner, identifier):
        if identifier not in self.rows or self.rows[identifier]['owner'] != owner:
            raise Missing()
        return deepcopy(self.rows[identifier])
    def list(self, owner):
        return [{'id': i, 'title': r['title'], 'message_count': len(r['messages'])}
                for i, r in self.rows.items() if r['owner'] == owner]
    def append(self, owner, identifier, revision, messages, **extra):
        r = self.get(owner, identifier)
        if self.fail_save or r['revision'] != revision:
            raise Conflict()
        r.update(messages=r['messages'] + messages, revision=revision+1, **extra)
        self.rows[identifier] = r
        return deepcopy(r)
    def delete(self, owner, identifier):
        self.get(owner, identifier)
        del self.rows[identifier]
    def reserve_chat(self, owner, per_minute, daily_max):
        if self.blocked:
            raise RateLimited()


class FakeAI:
    def __init__(self):
        self.calls = []
        self.fail = False
    def answer(self, q, summary, history, rows=None):
        self.calls.append((q, summary, history))
        if self.fail:
            raise RuntimeError()
        return {'answer': '저장된 기간의 평균은 1600원/리터입니다.', 'tool_trace': []}


@pytest.fixture
def setup():
    repo, ai = Conversations(), FakeAI()
    app.dependency_overrides[conversations] = lambda: repo
    app.dependency_overrides[chat_service] = lambda: ai
    app.dependency_overrides[repository] = lambda: SimpleNamespace(list=lambda: [
        {'date': '2025-01-01', 'value': 1600}])
    with TestClient(app) as client:
        yield client, repo, ai
    app.dependency_overrides.clear()


A = {'X-Session-Token': 'a'*40}
B = {'X-Session-Token': 'b'*40}


def test_chat_auto_save_and_continue(setup):
    c, repo, ai = setup
    result = c.post('/api/chat', headers=A, json={'message': '평균은?'}).json()
    assert result['saved'] is True
    identifier = result['conversation_id']
    loaded = c.get('/api/conversations/'+identifier, headers=A).json()
    assert 'owner' not in loaded
    assert len(loaded['messages']) == 2
    assert loaded['latest_summary']['metrics']['average'] == 1600
    assert ai.calls[0][1]['as_of'] == '2025-01-01'
    c.post('/api/chat', headers=A, json={'message': '최고는?', 'conversation_id': identifier})
    assert len(ai.calls[1][2]) == 2
    assert c.get('/api/conversations', headers=A).json()[0]['message_count'] == 4
    assert c.get('/api/conversations', headers=B).json() == []
    assert c.get('/api/conversations/'+identifier, headers=B).status_code == 404
    assert c.delete('/api/conversations/'+identifier, headers=B).status_code == 404
    assert c.delete('/api/conversations/'+identifier, headers=A).status_code == 204
    assert c.get('/api/conversations/'+identifier, headers=A).status_code == 404


def test_manual_save_and_validation(setup):
    c, _, _ = setup
    result = c.post('/api/conversations', headers=A, json={
        'title': '저장', 'messages': [{'role': 'user', 'content': '질문'}]})
    assert result.status_code == 201
    assert result.json()['origin'] == 'manual'
    assert c.post('/api/chat', json={'message': '질문'}).status_code == 401
    assert c.post('/api/chat', headers=A, json={'message': '  '}).status_code == 422
    assert c.post('/api/chat', headers=A, json={'message': '질문', 'conversation_id': 'bad'}).status_code == 422
    assert c.post('/api/conversations', headers=A, json={
        'messages': [{'role': 'system', 'content': '지시'}]}).status_code == 422


def test_limits_errors_and_failed_save(setup):
    c, repo, ai = setup
    repo.blocked = True
    assert c.post('/api/chat', headers=A, json={'message': '질문'}).status_code == 429
    assert len(ai.calls) == 0
    repo.blocked = False
    ai.fail = True
    assert c.post('/api/chat', headers=A, json={'message': '질문'}).status_code == 502
    assert repo.rows == {}
    ai.fail = False
    repo.fail_save = True
    result = c.post('/api/chat', headers=A, json={'message': '질문'}).json()
    assert result['saved'] is False
    assert result['answer']
    assert 'warning' in result


def test_sdk_context_and_tokens():
    captured = {}
    def completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',
                                  message=SimpleNamespace(content='응답'))])
    service = ChatService.__new__(ChatService)
    service.model, service.max_tokens = 'configured-model', 800
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion)))
    assert service.answer('질문', {'count': 365}, [])['answer'] == '응답'
    assert '"count": 365' in captured['messages'][0]['content']
    assert captured['max_completion_tokens'] == 800
    assert captured['store'] is False
    assert captured['messages'][-1] == {'role': 'user', 'content': '질문'}


def test_missing_openai_config(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    with pytest.raises(ChatUnavailable):
        ChatService()
