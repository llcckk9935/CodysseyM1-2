import logging
import os
import secrets
from datetime import date
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.routers.data import repository, operation
from app.services.tools import period_summary

router = APIRouter(tags=['actions'])
bearer = HTTPBearer(auto_error=False)


def authorize_actions(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    expected = os.getenv('ACTIONS_API_KEY', '')
    if not expected:
        raise HTTPException(503, 'Actions 인증이 설정되지 않았습니다.')
    if not credentials or credentials.scheme.lower() != 'bearer' or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(401, 'Actions 인증이 필요합니다.')


@router.get('/api/actions/summary', operation_id='getFuelPriceSummary', dependencies=[Depends(authorize_actions)])
def action_summary(start_date: date | None = None, end_date: date | None = None,
                   repo=Depends(repository)):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, '시작일은 종료일보다 늦을 수 없습니다.')
    result = period_summary(operation(repo.list), start_date, end_date)
    logging.info('GPT Actions summary queried start=%s end=%s records=%s', start_date, end_date, result['count'])
    return result


def actions_schema(base_url):
    parsed = urlparse(base_url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('A public HTTPS backend URL is required')
    return {
        'openapi': '3.1.0', 'info': {'title': 'Fuel Price Summary Action', 'version': '1.0.0'},
        'servers': [{'url': base_url.rstrip('/')}],
        'paths': {'/api/actions/summary': {'get': {
            'operationId': 'getFuelPriceSummary',
            'summary': '조회 기간의 전국 보통휘발유 저장 가격 통계',
            'description': '저장된 과거 기록만 조회. 최근은 as_of 기준. 실시간 가격·예측·변동 원인은 제공하지 않는다.',
            'security': [{'bearerAuth': []}],
            'parameters': [{'name': n, 'in': 'query', 'required': False,
                            'schema': {'type': 'string', 'format': 'date'}} for n in ['start_date', 'end_date']],
            'responses': {'200': {'description': 'Price summary', 'content': {'application/json': {
                'schema': {'type': 'object', 'properties': {
                    'count': {'type': 'integer'}, 'as_of': {'type': ['string', 'null']},
                    'unit': {'type': 'string'}, 'metrics': {'type': ['object', 'null'], 'additionalProperties': True},
                    'trend': {'type': 'object', 'additionalProperties': True},
                    'monthly': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}},
                    'additionalProperties': True}}}},
                '401': {'description': 'Invalid action key'}, '422': {'description': 'Invalid period'},
                '503': {'description': 'Configuration or storage unavailable'}}}}},
        'components': {'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme': 'bearer'}}}}


@router.get('/actions/openapi.json', include_in_schema=False)
def schema():
    try:
        return actions_schema(os.getenv('ACTIONS_PUBLIC_BASE_URL', ''))
    except ValueError:
        raise HTTPException(503, 'ACTIONS_PUBLIC_BASE_URL에 배포된 HTTPS 백엔드 주소를 설정하세요.')
