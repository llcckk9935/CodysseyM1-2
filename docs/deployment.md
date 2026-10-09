# 실제 연결·배포 준비

## 확인 상태
2026-10-09: 연결된 GitHub 계정 llcckk9935.
제출 저장소 https://github.com/llcckk9935/CodysseyM1-2 에 대한 pull/push/admin 권한을 API로 확인했다.
기본 브랜치는 main. 현재 README 내용은 `# CodysseyM1-2`다.
최초 업로드 전에 main의 전체 파일을 확인했다. 기존 파일은 제목만 담긴 README.md 하나다.
프로젝트 이름 CodysseyM1-2를 유지하면서 실행 방법과 구현 상태를 README에 보강한다.
현재 작업 환경에는 Firebase 서비스 계정, OpenAI 키/모델, Render/Vercel 인증 정보가 없다.
이는 사용자가 해당 계정을 보유하지 않았다는 뜻이 아니다.

## 배포 설정
| 서비스 | 설정 |
| --- | --- |
| Firebase | 프로젝트, Firestore Database, 서버 전용 서비스 계정 |
| Render | Root Directory: backend, Build: pip install -r requirements.txt, Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT |
| Vercel | Root Directory: frontend, Build: node build.mjs, Output: dist, API_BASE_URL: Render HTTPS 주소 |
| GPT Actions | Render /actions/openapi.json, API Key Bearer 인증 |

render.yaml은 준비한 배포 설정이며 실제 생성된 서비스가 아니다. autoDeploy는 꺼두었다.
서비스 생성 및 환경 변수 입력은 실제 연결 단계에서 수행한다.

## 진행 순서
1. 기존 저장소 전체 파일 확인 후 코드 업로드.
2. Firebase 프로젝트·Firestore 준비 및 서버 인증 정보 설정.
3. OpenAI 키와 계정에서 사용할 수 있는 GPT 모델 ID 설정.
4. Render 백엔드 배포 및 /docs 확인.
5. import_csv.py로 원본 가져오기: 365개 기록과 통계 확인.
6. Vercel 화면 배포, Render ALLOWED_ORIGINS에 해당 프론트 주소 설정.
7. 실제 채팅·CRUD·대화 불러오기·도구 호출·그래프·다운로드·테마·모바일 화면 확인.
8. GPT Actions 설정 및 실제 외부 호출 확인.
9. 실제 접속 URL과 제출 스크린샷, 검증 결과를 README에 추가.

키는 GitHub·프론트 설정·대화 메시지에 붙이지 않고 서비스의 비밀 환경 변수에 설정한다.
CSV 가져오기는 서비스 계정이 설정된 로컬 환경에서도 실행할 수 있다.
Render 무료 서비스에서 셸 사용 가능 여부를 전제하지 않는다.
/health는 프로세스 상태만 확인하며 DB 연결을 보장하지 않는다.

## 공식 참고
- https://render.com/docs/deploy-fastapi
- https://vercel.com/docs/builds/configure-a-build
- https://firebase.google.com/docs/admin/setup
- https://firebase.google.com/docs/firestore/quickstart-server
