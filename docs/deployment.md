# 배포 구성 및 검증 기록

## 확인 상태
2026-10-09 기준 배포와 실제 사용 검증을 완료했다.

| 서비스 | 배포 주소 | 확인 |
| --- | --- | --- |
| GitHub | https://github.com/llcckk9935/CodysseyM1-2 | `main` 브랜치에 프로젝트 파일과 문서 저장 |
| Render API | https://codysseym1-2-k5mi.onrender.com | `/health`, `/api/data/summary`, `/docs` 응답 확인 |
| Vercel 프론트엔드 | https://codysseym1-2-frontend-psi.vercel.app/ | 웹 화면 및 실제 휴대전화 브라우저 확인 |
| GPT Actions | Render `/actions/openapi.json` | Bearer 인증과 GPT 대화의 기간별 호출 확인 |

배포 URL과 환경 변수 값은 현재 서비스 설정을 기준으로 기록한다. 비밀 키와 서비스 계정 정보는 이 문서나 저장소에 기록하지 않는다.

## 배포 설정
| 서비스 | 설정 |
| --- | --- |
| Firebase | 프로젝트, Firestore Database, 서버 전용 서비스 계정 |
| Render | Root Directory: backend, Build: pip install -r requirements.txt, Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT |
| Vercel | Root Directory: frontend, Build: node build.mjs, Output: dist, API_BASE_URL: Render HTTPS 주소 |
| GPT Actions | Render /actions/openapi.json, API Key Bearer 인증 |

`render.yaml`은 Render 서비스의 배포 설정을 선언한다. `autoDeploy`는 꺼져 있으므로 변경 사항 푸시는 자동 배포를 뜻하지 않으며, 필요한 경우 Render에서 수동 배포한다.
실제 Firebase 서비스 계정, OpenAI 호환 API 키·모델, CORS 허용 주소, 관리자 토큰과 Actions 키는 각 서비스의 비밀 환경 변수로 관리한다.

## 완료한 배포 및 기능 검증
1. Firebase Firestore에 원본 데이터 365개를 가져오고 날짜별 통계를 확인했다.
2. Render 백엔드와 Vercel 프론트엔드를 배포하고 브라우저 CORS 연결을 구성했다.
3. Render의 `/health`, `/api/data/summary`, `/docs`와 Vercel 사이트가 정상 응답하는 것을 확인했다. `/health`는 프로세스 상태만 확인하며 DB 연결 상태를 보증하지 않는다.
4. 채팅 응답 및 자동 저장, 대화 목록·불러오기, 데이터 추가·수정·삭제, CSV 다운로드를 확인했다.
5. Function Calling의 기간 요약 도구 선택과 GPT Actions의 실제 기간별 호출을 확인했다.
6. 데스크톱 UI와 390×844 모바일 뷰포트 자동 검사, 실제 휴대전화 브라우저를 확인했다.
7. 프로젝트 소개·실행 방법·환경 변수·배포 URL·검증 결과와 제출 스크린샷을 README에 기록했다.

키는 GitHub·프론트 설정·대화 메시지에 붙이지 않고 서비스의 비밀 환경 변수에 설정한다.
CSV 가져오기는 서비스 계정이 설정된 로컬 환경에서 `backend` 디렉터리를 기준으로 실행할 수 있다. 기존 날짜는 덮어쓰지 않는다.
Render 무료 서비스의 셸 사용 가능 여부에 의존하지 않는다.

## 공식 참고
- https://render.com/docs/deploy-fastapi
- https://vercel.com/docs/builds/configure-a-build
- https://firebase.google.com/docs/admin/setup
- https://firebase.google.com/docs/firestore/quickstart-server
