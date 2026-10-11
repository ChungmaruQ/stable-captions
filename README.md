# Stable Captions

한국어·영어 발표를 읽기 쉬운 자막으로 표시하는 Windows/macOS 앱입니다. 이미 표시한 문구를 반복 수정하지 않고, 안정된 의미 단위부터 보여 줍니다.

**개발자의 Azure 키는 포함되어 있지 않습니다. 각 사용자의 Azure 계정·리소스·키로 동작합니다. 아무것도 준비되지 않았다면 아래 AI 요청문으로 계정 준비부터 에이전트에게 맡길 수 있습니다.** 소스 빌드와 오프라인 검증에는 Azure 계정이 필요하지 않습니다. 실제 음성 인식·번역·화면 분석은 사용자 계정으로 과금됩니다.

| 앱 | 입력 | 출력 |
|---|---|---|
| `StableCaptions` | 한국어 / 영어 자동 감지 | 영어 또는 한국어 선택 |
| `StableCaptions_JP-VN` | 한국어 / 영어 자동 감지 | 일본어 한 줄 + 베트남어 한 줄 |

자막 위치(위/가운데/아래), 표시 화면, 최대 두 줄/롤업, 배경 투명도를 선택할 수 있습니다. 말이 끝난 뒤 남은 자막은 자동으로 지워집니다. 화면 분석은 선택한 모니터 전체 이미지를 번역 모델에 전달하며, Vision OCR을 추가하면 문자 힌트도 이용합니다. 발화가 화면 내용보다 우선합니다.

## 처음 사용하는 분

1. [Releases](https://github.com/ChungmaruQ/stable-captions/releases)에서 필요한 Windows ZIP을 받아 압축을 풉니다.
2. Azure가 처음이면 아래 **AI에게 처음부터 맡기기** 요청문을 사용하세요. 에이전트가 계정 준비부터 승인된 서비스 생성·연결까지 진행합니다. 직접 설정하려면 [Azure 안내](docs/AZURE_SETUP.md)를 참고하세요.
3. EXE를 실행하여 본인 설정을 입력하고 **내 Azure 설정 저장**을 누릅니다.
4. [실행 순서와 문제 해결](docs/QUICKSTART.md)을 따라 짧은 한국어·영어 발화로 확인합니다.

EXE는 Windows x64용이며 코드 서명은 되어 있지 않습니다. Mac에서 Windows EXE를 직접 빌드할 수는 없습니다. Mac 사용자는 GitHub Actions로 Windows 빌드를 실행하거나 Windows PC에서 아래 명령을 사용하세요.

## AI에게 처음부터 맡기기

Claude/Opus, GPT Astra/Sol 등 코딩 에이전트에 아래 문장을 붙여 넣으세요. 특정 모델에만 의존하는 도구나 숨겨진 개인 파일은 필요하지 않습니다.

> https://github.com/ChungmaruQ/stable-captions 를 클론하고 AGENTS.md, docs/AZURE_AGENT_RUNBOOK.md, docs/AZURE_SETUP.md, docs/BUILD_AND_TEST.md를 읽어 주세요. 나는 초보자이며 Azure 계정·구독·서비스가 하나도 준비되어 있지 않을 수 있습니다. 환경 확인부터 계정/구독 준비 안내, 사용 가능한 지역·모델·쿼터와 비용 확인, 필요한 Azure 리소스 생성, 개인 설정 저장, 두 Windows EXE 빌드, 실제 자막 시험까지 A부터 Z까지 맡아 주세요. 설명이나 문서 링크만 주고 끝내지 말고, 가능한 작업은 CLI/API/내가 허용한 브라우저로 직접 수행하세요. 로그인·MFA·결제 동의 등 내가 해야 하는 순간에는 지금 할 행동 한 가지를 알려 주고, 내가 마치면 다음 단계부터 계속하세요. 유료 작업은 실제 리소스/SKU/지역/모델·요금과 짧은 연결 시험 계획을 제시해 내 확인을 받은 뒤 진행하고, 같은 승인 범위는 반복해서 묻지 마세요. 키는 채팅·코드·Git·EXE에 넣지 말고 내 PC의 개인 설정 파일로 연결하세요. Windows 작업은 바탕화면 StableCaptions-Workspace/Project_Public에서 하고 기존 자료를 보존하세요. Windows가 없으면 내 GitHub Fork의 Actions로 빌드하세요. 마지막에는 서비스 생성·인증·마이크 자막·화면 분석의 검증 결과, EXE 위치와 남은 내 행동을 구분해 알려 주세요.

에이전트는 [A부터 Z까지 실행 절차](docs/AZURE_AGENT_RUNBOOK.md)를 따릅니다. 로그인·MFA·결제 동의는 사용자가 직접 처리하고, 승인된 리소스 생성과 앱 연결은 가능한 도구로 에이전트가 수행합니다.

## Windows에서 직접 빌드

Git 및 **Python 3.12 x64**(Python Launcher 포함)를 설치한 뒤 PowerShell에서:

```powershell
$workspace = Join-Path ([Environment]::GetFolderPath('Desktop')) 'StableCaptions-Workspace'
New-Item -ItemType Directory -Force $workspace | Out-Null
Set-Location $workspace
git clone https://github.com/ChungmaruQ/stable-captions.git Project_Public
Set-Location Project_Public
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

기존 `Project_Public`이 있으면 덮어쓰지 말고 그 폴더에서 변경 사항을 확인한 뒤 업데이트하세요. 출력은 `dist/en_ko/StableCaptions.exe`, `dist/jp_vn/StableCaptions_JP-VN.exe` 및 `dist/*-Windows.zip`입니다. 두 앱은 같은 사용자 Azure 설정을 읽습니다.

빌드는 테스트 → PyInstaller 패키징 → 패키지 자체의 오프라인 레이아웃 검증 → SHA-256 기록 순서로 진행합니다. **실제 마이크/클라우드 품질까지 통과했다는 의미는 아닙니다.** [검증 안내](docs/BUILD_AND_TEST.md)를 확인하세요.

## GitHub에서 Windows 빌드

이 저장소를 Fork → Actions → **Windows EXE** → Run workflow. 완료된 실행의 `StableCaptions-Windows` artifact를 다운로드하세요. Azure secrets 등록 없이 빌드됩니다. main 변경/PR에도 실행되며, 유지관리자가 `v*` 태그를 푸시하면 검증된 ZIP이 Release에 올라갑니다.

## 문서

- [에이전트의 Azure 전체 설정 절차](docs/AZURE_AGENT_RUNBOOK.md)
- [Azure 서비스 생성·연결](docs/AZURE_SETUP.md)
- [실행 및 문제 해결](docs/QUICKSTART.md)
- [빌드·테스트·Mac 실행](docs/BUILD_AND_TEST.md)
- [AI 작업 지침](AGENTS.md), [초보자 AI 프롬프트](docs/AI_BOOTSTRAP.md)
- [개인정보·비용·보안](docs/PRIVACY_AND_COST.md)

MIT 라이선스. PySide6/Qt, Azure SDK 등 의존성의 별도 라이선스도 적용됩니다. 과거 개인용 배포본과 달리 공개판에는 개인 키·행사 초록·연설문·녹음·슬라이드가 없습니다.
