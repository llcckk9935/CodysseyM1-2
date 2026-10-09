# 미션 요구사항 재점검 — 2026-10-09

판정 기준: 구현 코드, 18개 자동 테스트, 실제 배포 API, 실제 웹 동작과 제출 증거를 구분했다.
현재 판정: 필수 기능, 인사이트·UX 선택 과제, GPT Actions 외부 호출 검증을 완료했다. 아래 범위와 한계에 근거해 판정했으며, 모바일 자동 UI 테스트는 실행하지 않았다.

## 필수 요구사항

| 요구사항 | 판정 | 근거 |
| --- | --- | --- |
| Python 3.10 이상·venv·필수 패키지 | 충족 | Render Python 3.12.10, 로컬 가상환경, requirements.txt |
| Firebase·OpenAI·Render·Vercel 준비 | 충족 | 실제 Firestore 및 두 배포 서비스, Codyssey 호환 GPT 호출 성공 |
| 관심 시계열 100개 이상 | 충족 | 오피넷 전국 보통휘발유 2025년 일별 기록 365개 |
| 기간·개수·평균·최대·최소·추세 요약 | 충족 | /api/data/summary HTTP 200, 평균 1680.32, 최소 1626.99, 최대 1746.84 |
| FastAPI 초기화·CORS·Swagger | 충족 | app/main.py, 실제 /docs 및 /openapi.json, Vercel 도메인 허용 |
| Firestore data·conversations 저장·키 환경 변수 | 충족 | 원본 가져오기 및 실제 대화 자동 저장·불러오기, Render 비밀 환경 변수 |
| 데이터 POST·GET·PUT·DELETE·summary | 충족 | 실제 임시 기록 추가 1700→수정 1701→삭제, 원본 365개 복구; 자동 테스트 |
| 대화 POST·GET·DELETE·개별 GET | 충족 | 실제 저장 201, 목록/개별 200, 검증 대화 삭제 204; 웹 불러오기 |
| /api/chat 요약 주입·GPT·자동 저장 | 충족 | 실제 평균 질문과 답변 통계 일치, 자동 저장·불러오기 |
| Render 배포·무료 첫 요청 안내 | 충족 | Free 서비스, 콜드스타트·연결 지연 화면 안내 |
| HTML/CSS/JS, 프레임워크 금지 | 충족 | vanilla frontend, SVG 그래프 |
| 메시지 입력·대화 표시·로딩 | 충족 | 실제 대화, 생성 중 상태·입력 비활성화 확인 |
| 데이터 추가·목록·수정 또는 삭제 UI | 충족 | 추가·수정·삭제 실제 UI 검증, data-crud-success.jpg |
| 이전 대화 목록·불러오기 | 충족 | conversation-load.jpg의 복원 메시지와 불러오기 성공 안내 |
| 현재 요약 정보 표시 | 충족 | 상단 카드·기간·추세, 채팅에 답변 당시 요약 표시 보완 |
| Vercel 배포·API_BASE_URL 환경 변수 | 충족 | 실제 Production URL, frontend/build.mjs로 빌드 설정 반영 |
| README 소개·스택·URL·로컬·환경 변수 | 충족 | README 해당 절 |
| 요약과 질문·답변이 함께 보이는 캡처 | 충족 | 보완된 conversation-load.jpg |
| CRUD 동작 및 대화 불러오기 캡처 | 충족 | data-crud-success.jpg, conversation-load.jpg |
| 입력 검증·최소 예외 처리·키 보호 | 충족 | Pydantic 422, 인증·404·409·503 처리, 서버 환경 변수 |
| GPT 요청·토큰 한도 | 충족 | 요청당 최대 3회 호출, 호출당 2000 토큰, 세션/전체 요청 한도 |

## 선택 요구사항

| 요구사항 | 판정 | 근거 |
| --- | --- | --- |
| Function Calling 스키마·도구 연결 | 충족 | get_data_summary, get_conversation_history; 허용 목록·인자 검증 |
| 실제 도구 선택 근거·호출 흐름 문서 | 충족 | 2월 질문→기간 요약 도구→28개·1728.26원/L→최종 답변; README·스크린샷 |
| GPT Actions 외부 채널 연결 및 실제 호출 검증 | 충족 | 커스텀 GPT에 스키마·Bearer API 키를 연결. Actions 전체 기간 테스트 365개·평균 1680.32원/L, 실제 GPT 대화의 2025-02-01~28 호출 28개·평균 1728.26원/L를 확인. README의 gpt-actions-live-verified.jpg |
| 추가 지표 1개 이상 | 충족 | 월평균, 기간 변화율, 최근/직전 7일 변화율 |
| 그래프 1개 | 충족 | 실제 일별 SVG 추세 그래프 |
| CSV 또는 JSON 다운로드 | 충족 | 실제 CSV 다운로드·365개 파싱 확인 |
| 다크 모드 | 충족 | 실제 전환 및 라이트 복원 확인 |

## 학습 목표 설명 근거

데이터 수집→Firestore 저장→Decimal 통계→시스템 프롬프트 주입→GPT 답변→대화 저장의 흐름은 README의 분석·구조·채팅 절에 설명했다.
라우터는 HTTP·검증·인증, 서비스는 통계와 AI, 저장소는 Firestore 접근으로 역할을 분리한다.
Pydantic은 부정확한 날짜·가격·과도한 메시지·예상하지 않은 필드를 DB 저장 전에 거부한다.
CORS 허용 도메인과 공개 API 서버 URL은 비밀 API 키와 구분한다. 키는 서버 환경 변수로만 관리한다.

## 실제 재검증

- pytest 18 passed, JavaScript 문법 검사 및 Vercel 환경 변수 기반 빌드 성공.
- 배포 /health·/api/data/summary·/openapi.json HTTP 200.
- 2월 평균 1728.26, 기록 28개를 실제 GPT 답변과 배포 요약 월평균으로 대조.
- GPT 편집기 새로고침 1회 후에도 빈 화면. Actions 전용 키·공개 주소 설정 및 배포 완료.
- Python HTTP 클라이언트로 스키마 200, 전체/2월/범위 밖 조회 200, 키 누락/오류 401, 날짜 역전 422 확인. actions-api-verification.json에 비밀 값 없이 결과 저장.
- ChatGPT GPT Actions 인증 설정 후 편집기 테스트에서 전체 기간 365건·평균 1680.32원/L 조회 성공. 저장된 비공개 GPT의 실제 대화에서 2025-02-01~28 28건·평균 1728.26원/L 조회 및 응답을 확인하고 화면을 증거로 추가했다.
- 모바일 자동 테스트는 미실행. 필수 과제에는 모바일 자동 테스트가 지정되어 있지 않다.

## GPT Actions 완료 조건

1. 완료: ACTIONS_PUBLIC_BASE_URL 및 별도 읽기 전용 ACTIONS_API_KEY를 Render에 설정하고 실제 HTTP 응답 검증.
2. 완료: GPT 편집기에서 스키마를 불러오고 Bearer 인증을 연결.
3. 완료: 편집기 전체 기간 테스트와 실제 GPT 2월 대화에서 Action 호출 결과를 확인하고 스크린샷으로 기록.
4. 완료: README·Actions 설정 문서·점검표를 검증 증거에 맞게 갱신.
