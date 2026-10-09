from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.services.summary import summarize


class SummaryArguments(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    start_date: date | None = None
    end_date: date | None = None
    reason: str = Field(min_length=1, max_length=300)

    @model_validator(mode='after')
    def period_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date must not be after end_date')
        return self


class HistoryArguments(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=300)


def period_summary(rows, start_date=None, end_date=None):
    selected = [r for r in rows
                if (not start_date or r['date'] >= start_date.isoformat())
                and (not end_date or r['date'] <= end_date.isoformat())]
    result = summarize(selected)
    result['requested_period'] = {'start_date': str(start_date) if start_date else None,
                                  'end_date': str(end_date) if end_date else None}
    return result


TOOLS = [
    {'type': 'function', 'function': {
        'name': 'get_data_summary', 'strict': True,
        'description': '저장된 전국 보통휘발유 가격 통계를 조회한다. 특정 기간 질문에는 날짜 범위를 지정한다. 최신 가격이나 예측은 제공하지 않는다.',
        'parameters': {'type': 'object', 'properties': {
            'start_date': {'type': ['string', 'null'], 'description': 'YYYY-MM-DD, 전체 시작이면 null'},
            'end_date': {'type': ['string', 'null'], 'description': 'YYYY-MM-DD, 전체 종료이면 null'},
            'reason': {'type': 'string', 'description': '질문의 어떤 정보 요구 때문에 이 도구를 선택했는지 짧게 설명'}},
            'required': ['start_date', 'end_date', 'reason'], 'additionalProperties': False}}},
    {'type': 'function', 'function': {
        'name': 'get_conversation_history', 'strict': True,
        'description': '현재 사용자의 현재 대화에서 이전 메시지 최대 12개를 조회한다. 다른 대화나 다른 사용자 기록에 접근하지 않는다.',
        'parameters': {'type': 'object', 'properties': {
            'reason': {'type': 'string', 'description': '이전 대화가 필요한 질문의 근거를 짧게 설명'}},
            'required': ['reason'], 'additionalProperties': False}}}
]


def execute_tool(name, arguments, rows, history):
    if name == 'get_data_summary':
        args = SummaryArguments.model_validate(arguments)
        return period_summary(rows, args.start_date, args.end_date), args.model_dump(mode='json')
    if name == 'get_conversation_history':
        args = HistoryArguments.model_validate(arguments)
        return {'messages': history[-12:], 'scope': 'current_conversation'}, args.model_dump()
    raise ValueError('Tool is not allowed')
