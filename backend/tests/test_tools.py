import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.data import repository
from app.routers.actions import actions_schema
from app.services.chat import ChatService, ChatUnavailable
from app.services.tools import execute_tool


ROWS = [{'date': '2025-01-01', 'value': 1600},
        {'date': '2025-02-01', 'value': 1700}]


def choice(content=None, name=None, arguments=None):
    calls = [SimpleNamespace(id='call_test', function=SimpleNamespace(name=name, arguments=arguments))] if name else []
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='tool_calls' if calls else 'stop',
        message=SimpleNamespace(content=content, tool_calls=calls))])


def mock_service(responses):
    captured = []
    def create(**kwargs):
        captured.append({**kwargs, 'messages': list(kwargs['messages'])})
        return responses.pop(0)
    ai = ChatService.__new__(ChatService)
    ai.model, ai.max_tokens = 'test-model', 800
    ai.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return ai, captured


def test_period_tool_loop_and_trace():
    ai, calls = mock_service([
        choice(name='get_data_summary', arguments=json.dumps({
            'start_date': '2025-02-01', 'end_date': '2025-02-28', 'reason': '2월 평균을 질문했기 때문'})),
        choice(content='2월 저장 기록 평균은 1700원/리터입니다.')])
    result = ai.answer('2월 평균은?', {'count': 2}, [], ROWS)
    assert result['tool_trace'][0]['result_count'] == 1
    assert result['tool_trace'][0]['arguments']['reason'] == '2월 평균을 질문했기 때문'
    assert json.loads(calls[1]['messages'][-1]['content'])['metrics']['average'] == 1700
    assert calls[0]['tool_choice'] == 'auto'
    assert calls[0]['parallel_tool_calls'] is False
    assert len(calls) == 2


def test_history_tool_scope_and_rejected_tools():
    result, args = execute_tool('get_conversation_history', {'reason': '이전 질문 확인'}, ROWS,
                               [{'role': 'user', 'content': '이전 질문'}])
    assert result['scope'] == 'current_conversation'
    assert len(result['messages']) == 1
    with pytest.raises(ValueError):
        execute_tool('delete_data', {}, ROWS, [])
    with pytest.raises(ValueError):
        execute_tool('get_data_summary', {'start_date': '2025-02-01', 'end_date': '2025-01-01', 'reason': '비교'}, ROWS, [])
    ai, calls = mock_service([choice(name='delete_data', arguments='{}'), choice(content='삭제할 수 없습니다.')])
    response = ai.answer('삭제해', {}, [], ROWS)
    assert response['tool_trace'][0]['status'] == 'error'
    assert 'error' in json.loads(calls[1]['messages'][-1]['content'])


def test_tool_round_limit():
    args = json.dumps({'reason': '이전 대화 확인'})
    ai, calls = mock_service([choice(name='get_conversation_history', arguments=args),
                             choice(name='get_conversation_history', arguments=args),
                             choice(content='완료')])
    result = ai.answer('이전 대화?', {}, [], ROWS)
    assert len(calls) == 3
    assert calls[-1]['tool_choice'] == 'none'
    assert len(result['tool_trace']) == 2


def test_actions_auth_period_and_schema(monkeypatch):
    monkeypatch.setenv('ACTIONS_API_KEY', 'actions-test-key')
    monkeypatch.setenv('ACTIONS_PUBLIC_BASE_URL', 'https://backend.example.test')
    app.dependency_overrides[repository] = lambda: SimpleNamespace(list=lambda: ROWS)
    try:
        with TestClient(app) as c:
            assert c.get('/api/actions/summary').status_code == 401
            assert c.get('/api/actions/summary', headers={'Authorization': 'Bearer wrong'}).status_code == 401
            headers = {'Authorization': 'Bearer actions-test-key'}
            result = c.get('/api/actions/summary?start_date=2025-02-01&end_date=2025-02-28', headers=headers)
            assert result.status_code == 200
            assert result.json()['metrics']['average'] == 1700
            assert result.json()['count'] == 1
            assert c.get('/api/actions/summary?start_date=2025-03-01&end_date=2025-01-01', headers=headers).status_code == 422
            schema = c.get('/actions/openapi.json').json()
            assert set(schema['paths']) == {'/api/actions/summary'}
            assert 'actions-test-key' not in json.dumps(schema)
            assert schema['servers'][0]['url'] == 'https://backend.example.test'
            assert schema['paths']['/api/actions/summary']['get']['operationId'] == 'getFuelPriceSummary'
            monkeypatch.delenv('ACTIONS_PUBLIC_BASE_URL')
            assert c.get('/actions/openapi.json').status_code == 503
    finally:
        app.dependency_overrides.clear()
    with pytest.raises(ValueError):
        actions_schema('http://localhost:8000')
