# GPT Actions 설정 및 검증

현재 상태 (2026-10-09): 백엔드 배포와 실제 Firestore 요약, 웹 Function Calling, ChatGPT GPT Actions 호출 검증 완료.
/actions/openapi.json은 HTTP 200이며 읽기 API 하나와 Bearer 인증 스키마만 제공한다.
테스트 대역 성공과 실제 GPT Actions 호출은 분리해 기록한다.

## 준비
1. 백엔드를 Render HTTPS 주소에 배포하고 Firestore 원본 데이터를 가져온다.
2. Render 환경 변수 ACTIONS_PUBLIC_BASE_URL에 그 백엔드 주소를 지정한다.
3. ACTIONS_API_KEY에 무작위 비밀 값을 지정한다. 관리자 편집 토큰과 별도 값 사용.
4. OPENAI_API_KEY나 Firebase 키를 Actions 인증 키로 사용하지 않는다.

## 연결
1. 배포 서버의 /actions/openapi.json 주소에서 스키마를 가져온다.
   로컬 파일을 원하면 backend에서 `python export_actions.py`를 실행한다.
   실제 HTTPS 주소 설정이 없으면 스키마를 생성하지 않는다.
2. 사용자 GPT 편집 화면에서 Action을 추가하고 해당 스키마를 가져온다.
3. 인증은 API Key / Bearer 방식으로 선택하고 ACTIONS_API_KEY를 입력한다.
   키는 스키마나 GPT 지침·README에 쓰지 않는다.
4. 다음 지침을 적용한다.

> 전국 보통휘발유 과거 가격 통계 질문에는 getFuelPriceSummary를 호출한다.
> 특정 기간이면 start_date/end_date를 YYYY-MM-DD로 전달하고, 전체 기간이면 생략한다.
> 도구 결과 수치와 날짜만 사용한다. 최근은 as_of 기준이며 오늘 가격으로 설명하지 않는다.
> 데이터가 없거나 API 오류가 발생하면 자료 부족 또는 연결 실패로 설명한다.
> 현재 가격·미래 가격·변동 원인·개별 주유소 가격은 이 도구로 확인할 수 없다.
> 수정되거나 사용자 추가된 기록이 있으면 공식 원본과 다를 수 있음을 안내한다.
> 출처: 한국석유공사 오피넷 사용자 제공 CSV.

## 검증 절차
- 전체 기간 평균 질문 → getFuelPriceSummary → 365개 원본 기록 상태라면 1680.32원/리터.
- 2025년 2월 평균 질문 → 2025-02-01~2025-02-28 필터 → /api/data/summary의 2월 평균과 대조.
- 저장 범위 밖 질문 → count=0 → 데이터 부족 설명.
- 인증 키 누락·잘못된 키 → 401; Actions 키 미설정 → 503.
- Render 로그에서 조회 날짜·개수 확인. 키·세션 토큰을 로그나 스크린샷에 노출하지 않는다.
- 실제 Action 요청 화면, 응답 통계, 최종 답변을 캡처하고 날짜·배포 주소를 기록한다.

실제 서버 검증 (Python HTTP 클라이언트): 전체 365개·1680.32, 2월 28개·1728.26, 범위 밖 0개는 HTTP 200. 키 누락·오류 401, 날짜 역전 422.
결과: ../actions-api-verification.json. 공개 스키마 사본: actions-openapi.json. 키 값은 포함하지 않는다.
2026-10-09 ChatGPT GPT Actions 실제 검증: 편집기에서 전체 기간을 호출해 365개·평균 1680.32원/L를 반환했다. 저장된 비공개 GPT와의 대화에서 2025-02-01~2025-02-28을 질문해 Action이 28개 기록의 평균 1728.26원/L, 조회 기간·최저·최고와 기준일을 포함한 답변을 반환하는 것을 확인했다. 제출용 화면은 `../gpt-actions-live-verified.jpg`이다. 별도 Function Calling 검증과 구분한다.
대화 기록·데이터 편집 API는 외부 Actions 스키마에 노출하지 않는다.
같은 가격 요약 계산 서비스가 웹 채팅의 get_data_summary와 외부 getFuelPriceSummary에 사용된다.

공식 참고:
https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts
https://developers.openai.com/api/docs/actions/introduction
https://developers.openai.com/api/docs/guides/function-calling
