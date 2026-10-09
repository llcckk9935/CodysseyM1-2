import logging
import secrets
import os
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from app.models import DataInput, serialize_input
from app.repository import Conflict, Missing, get_repository
from app.services.summary import summarize

router = APIRouter(prefix='/api/data', tags=['data'])


def repository():
    try:
        return get_repository()
    except Exception:
        logging.exception('Firestore initialization failed')
        raise HTTPException(503, '데이터베이스 연결 설정을 확인하세요.')


def authorize(x_admin_token: str = Header(default='')):
    expected = os.getenv('ADMIN_API_TOKEN', '')
    if not expected:
        raise HTTPException(503, '데이터 편집 인증이 설정되지 않았습니다.')
    if not secrets.compare_digest(expected, x_admin_token):
        raise HTTPException(401, '데이터 편집 권한이 필요합니다.')


def operation(call):
    try:
        return call()
    except Conflict:
        raise HTTPException(409, '날짜 중복 또는 날짜 변경입니다. 날짜 변경은 삭제 후 추가하세요.')
    except Missing:
        raise HTTPException(404, '기록을 찾을 수 없습니다.')
    except Exception:
        logging.exception('Firestore operation failed')
        raise HTTPException(503, '데이터 저장소 요청에 실패했습니다.')


@router.get('/summary')
def summary(repo=Depends(repository)):
    return summarize(operation(repo.list))


@router.get('')
def listing(repo=Depends(repository)):
    return operation(repo.list)


@router.post('', status_code=201, dependencies=[Depends(authorize)])
def create(payload: DataInput, repo=Depends(repository)):
    return operation(lambda: repo.create(serialize_input(payload)))


@router.put('/{identifier}', dependencies=[Depends(authorize)])
def update(identifier: str, payload: DataInput, repo=Depends(repository)):
    if '/' in identifier or len(identifier) != 10:
        raise HTTPException(400, '잘못된 데이터 ID입니다.')
    return operation(lambda: repo.update(identifier, serialize_input(payload)))


@router.delete('/{identifier}', status_code=204, dependencies=[Depends(authorize)])
def delete(identifier: str, repo=Depends(repository)):
    if '/' in identifier or len(identifier) != 10:
        raise HTTPException(400, '잘못된 데이터 ID입니다.')
    operation(lambda: repo.delete(identifier))
    return Response(status_code=204)
