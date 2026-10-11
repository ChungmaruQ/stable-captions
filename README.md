# Stable Captions

한국어·영어 발표를 읽기 쉬운 자막으로 표시하는 Windows/macOS 앱입니다. 이미 표시한 문구를 반복 수정하지 않고, 안정된 의미 단위부터 보여 줍니다.

**개발자의 Azure 키는 포함되어 있지 않습니다. 각 사용자가 자신의 Azure 계정·리소스·키를 준비해야 합니다.** 소스 빌드와 오프라인 검증에는 Azure 계정이 필요하지 않습니다. 실제 음성 인식·번역·화면 분석은 사용자 계정으로 과금됩니다.

| 앱 | 입력 | 출력 |
|---|---|---|
| `StableCaptions` | 한국어 / 영어 자동 감지 | 영어 또는 한국어 선택 |
| `StableCaptions_JP-VN` | 한국어 / 영어 자동 감지 | 일본어 한 줄 + 베트남어 한 줄 |

자막 위치(위/가운데/아래), 표시 화면, 최대 두 줄/롤업, 배경 투명도를 선택할 수 있습니다. 말이 끝난 뒤 남은 자막은 자동으로 지워집니다. 화면 분석은 선택한 모니터 전체 이미지를 번역 모델에 전달하며, Vision OCR을 추가하면 문자 힌트도 이용합니다. 발화가 화면 내용보다 우선합니다.

## 처음 사용하는 분

1. [Releases](https://github.com/ChungmaruQ/stable-captions/releases)에서 필요한 Windows ZIP을 받아 압축을 풉니다.
2. [Azure 직접 설정 안내](docs/AZURE_SETUP.md)에 따라 본인 계정으로 Speech와 모델 배포를 준비합니다. Vision은 선택 사항입니다.
3. EXE를 실행하여 본인 설정을 입력하고 **내 Azure 설정 저장**을 누릅니다.
4. [실행 순서와 문제 해결](docs/QUICKSTART.md)을 따라 짧은 한국어·영어 발화로 확인합니다.

EXE는 Windows x64용이며 코드 서명은 되어 있지 않습니다. Mac에서 Windows EXE를 직접 빌드할 수는 없습니다. Mac 사용자는 GitHub Actions로 Windows 빌드를 실행하거나 Windows PC에서 아래 명령을 사용하세요.

## AI에게 처음부터 맡기기

Claude/Opus, GPT Astra/Sol 등 코딩 에이전트에 아래 문장을 붙여 넣으세요. 특정 모델에만 의존하는 도구나 숨겨진 개인 파일은 필요하지 않습니다.

> https://github.com/ChungmaruQ/stable-captions 를 클론하고 AGENTS.md와 docs/AI_BOOTSTRAP.md를 읽어 주세요. 내 환경을 확인하고 Windows용 두 EXE를 빌드·오프라인 검증해 주세요. Azure가 처음이므로 docs/AZURE_SETUP.md를 따라 내 구독에서 필요한 리소스와 모델 배포를 준비하도록 안내해 주세요. 유료 리소스 생성은 비용과 설정을 먼저 설명하고 내 확인을 받으세요. API 키를 채팅, 코드, Git, 실행파일에 넣지 말고 내 PC의 별도 설정으로 저장해 주세요. 실제 실행에 필요한 내 작업과 검증 결과를 구분해서 알려 주세요.

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

- [Azure 서비스 생성·연결](docs/AZURE_SETUP.md)
- [실행 및 문제 해결](docs/QUICKSTART.md)
- [빌드·테스트·Mac 실행](docs/BUILD_AND_TEST.md)
- [AI 작업 지침](AGENTS.md), [초보자 AI 프롬프트](docs/AI_BOOTSTRAP.md)
- [개인정보·비용·보안](docs/PRIVACY_AND_COST.md)

MIT 라이선스. PySide6/Qt, Azure SDK 등 의존성의 별도 라이선스도 적용됩니다. 과거 개인용 배포본과 달리 공개판에는 개인 키·행사 초록·연설문·녹음·슬라이드가 없습니다.
