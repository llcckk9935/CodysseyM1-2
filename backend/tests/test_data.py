import os
from copy import deepcopy
from pathlib import Path
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.data import repository
from app.repository import Conflict, Missing
from app.services.summary import summarize
from import_csv import read_rows


class MemoryRepository:
    """Test double only; production always uses Firestore."""
    def __init__(self):
        self.rows = {}
    def list(self):
        return deepcopy(list(self.rows.values()))
    def create(self, p):
        if p['date'] in self.rows:
            raise Conflict()
        self.rows[p['date']] = {'id': p['date'], **p, 'source': 'user', 'is_modified': False}
        return self.rows[p['date']]
    def update(self, identifier, p):
        if identifier not in self.rows:
            raise Missing()
        if p['date'] != identifier:
            raise Conflict()
        self.rows[identifier].update(p)
        return self.rows[identifier]
    def delete(self, identifier):
        if identifier not in self.rows:
            raise Missing()
        del self.rows[identifier]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('ADMIN_API_TOKEN', 'test-token')
    repo = MemoryRepository()
    app.dependency_overrides[repository] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_crud_and_summary(client):
    headers = {'X-Admin-Token': 'test-token'}
    p = {'date': '2025-01-01', 'value': 1600, 'memo': 'test'}
    assert client.post('/api/data', json=p).status_code == 401
    assert client.post('/api/data', json=p, headers=headers).status_code == 201
    assert client.post('/api/data', json=p, headers=headers).status_code == 409
    assert len(client.get('/api/data').json()) == 1
    assert client.get('/api/data/summary').json()['metrics']['average'] == 1600
    p['value'] = 1700
    assert client.put('/api/data/2025-01-01', json=p, headers=headers).status_code == 200
    assert client.get('/api/data/summary').json()['metrics']['average'] == 1700
    p['date'] = '2025-01-02'
    assert client.put('/api/data/2025-01-01', json=p, headers=headers).status_code == 409
    assert client.delete('/api/data/2025-01-01', headers=headers).status_code == 204
    assert client.delete('/api/data/2025-01-01', headers=headers).status_code == 404
    assert client.get('/api/data/summary').json()['metrics'] is None


@pytest.mark.parametrize('p', [
    {'date': '2025-02-30', 'value': 1600}, {'date': '2025-01-01', 'value': 0},
    {'date': '2025-01-01', 'value': -1}, {'date': '2025-01-01', 'value': 1.234},
    {'date': '2025-01-01', 'value': 'NaN'}, {'date': '2025-01-01', 'value': 1600, 'source': 'fake'}])
def test_validation(client, p):
    assert client.post('/api/data', json=p, headers={'X-Admin-Token': 'test-token'}).status_code == 422


def test_real_csv_statistics():
    rows = read_rows(Path(__file__).resolve().parents[2] / 'data/opinet_2025_original.csv')
    result = summarize(rows)
    assert len(rows) == 365
    assert result['metrics'] == {'average': 1680.32, 'min': 1626.99, 'max': 1746.84,
                                'min_dates': ['2025-06-12'], 'max_dates': ['2025-12-01']}
    december = [Decimal(str(r['value'])) for r in rows if r['date'].startswith('2025-12')]
    assert result['monthly'][-1]['average'] == float(round(sum(december)/31, 2))
    missing = [r for r in rows if r['date'] != '2025-12-30']
    assert summarize(missing)['trend']['status'] == '자료 부족'


def test_trend_and_ties():
    rows = [{'date': f'2025-01-{i:02}', 'value': 100 if i <= 7 else 110} for i in range(1,15)]
    result = summarize(rows)
    assert result['trend']['change_pct'] == 10
    assert result['trend']['difference'] == 10
    assert result['trend']['status'] == '상승'
    assert len(result['metrics']['max_dates']) == 7
