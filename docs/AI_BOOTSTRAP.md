# AI에게 맡기는 순서

저장소 주소: https://github.com/ChungmaruQ/stable-captions

Claude/Opus, GPT Astra/Sol 등 파일·터미널 작업이 가능한 코딩 AI에서 사용할 수 있습니다. 모델 이름이나 버전이 달라도 README와 AGENTS.md의 절차는 같습니다.

## 복사해서 요청하기

> 이 저장소를 처음부터 설치해 Windows 실행파일을 만들어 주세요: https://github.com/ChungmaruQ/stable-captions . AGENTS.md, README.md, docs/AZURE_SETUP.md, docs/BUILD_AND_TEST.md를 먼저 읽으세요. Windows에서는 바탕화면의 StableCaptions-Workspace/Project_Public에 클론하고 기존 자료를 보존하세요. Python 3.12 x64와 Git을 확인하고 두 앱의 오프라인 테스트와 실제 EXE 패키징 검증까지 완료해 주세요. Mac만 사용할 수 있으면 Mac에서 검증 후 내 GitHub Fork의 Windows Actions로 빌드해 주세요. 나는 Azure 초보자이니 내 구독에서 Speech, 이미지 입력을 지원하는 gpt-5-mini 배포, 선택적 Vision을 직접 준비하도록 안내해 주세요. 유료 생성은 설정과 비용을 설명하고 내 확인을 받으세요. 내 키를 채팅이나 코드에 넣지 말고 앱의 개인 설정 파일로 저장하도록 해 주세요. 마지막에는 EXE 위치, 검증 결과, 내가 직접 해야 하는 로그인/실제 발화 테스트를 구분해 알려 주세요.

## AI가 확인할 완료 조건

- 깨끗한 클론에서 숨겨진 로컬 파일 없이 설치됨.
- 개발자 키가 없으며, 빈 설정으로 앱을 실행하면 본인 설정 안내가 표시됨.
- 설정 저장/불러오기 테스트와 양쪽 앱 회귀 테스트 통과.
- Windows에서 생성된 두 EXE가 --verify-layout을 통과하고 manifest에 해시가 기록됨.
- 신규 사용자가 Azure 리소스 이름, Speech 지역, 모델 엔드포인트와 배포 이름을 구분할 수 있음.
- 실제 사용자 서비스 연결 테스트는 오프라인 검증과 따로 보고됨.

AI에게 맡겨도 사용자가 직접 해야 하는 것은 Microsoft/GitHub 로그인, 구독/결제 동의, 필요한 권한 승인, 실제 마이크 발화입니다. 저장소를 클론하는 것만으로 Azure 서비스가 자동 생성되지는 않습니다.
