# 빌드와 검증

## Windows x64

README의 전용 Desktop `StableCaptions-Workspace/Project_Public` 위치에 클론합니다. 기존 `App`, `Project`, `Project_JP-VN`, `Deliverables`, `Archive`가 있으면 보존합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1 -Variant all
```

Python 3.12 x64와 Git이 필요합니다. `requirements-build.txt`의 직접 의존성과 빌드 도구 버전은 고정되어 있습니다. 전이 의존성의 실제 버전은 각 ZIP의 `build-manifest.json`에 기록합니다. 바이트 단위로 동일한 EXE를 보장하는 잠금 빌드는 아닙니다.

`-Variant en_ko` 또는 `-Variant jp_vn`으로 하나만 패키징할 수 있습니다. 테스트는 항상 두 앱 모두 실행합니다. 기존 `.venv`가 다른 Python으로 만들어졌다면 삭제 전 내용을 확인하고 새 Python 3.12 환경으로 다시 만드세요.

## macOS 개발

Python 3.12와 Git을 준비한 뒤 저장소에서:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/check.py
.venv/bin/python apps/en_ko/app.py --right-screen
# 첫 앱을 종료한 후:
.venv/bin/python apps/jp_vn/app.py --right-screen
```

Mac 네이티브 패키징은 `.venv/bin/python scripts/build.py --variant all`입니다. `dist`에 Mac 실행파일/ZIP이 생깁니다. 배포 서명/공증은 이 저장소가 자동으로 하지 않습니다. 생성되는 Mac ZIP은 개발용 실행파일이며, 설치형 서명 .app을 제공한다고 보장하지 않습니다. PyInstaller가 만드는 별도 .app 번들은 dist 내에 생길 수 있으나 현재 ZIP은 실행파일을 포함합니다.

macOS에서 변경과 검증을 먼저 하고 Windows 빌드를 진행합니다. 검증용 창은 오른쪽 끝 모니터만 사용합니다. 모니터가 하나뿐이면 사용자의 다른 작업을 방해하지 않는 시점에 시각 검증하세요. GUI 없는 CI는 `QT_QPA_PLATFORM=offscreen`을 사용합니다.

## 검증 수준

1. `scripts/check.py`: 앱 로직과 사용자 설정 단위 테스트. AZURE 환경변수를 제거하고 빈 임시 설정 경로를 사용하므로 클라우드에 연결하지 않습니다.
2. `scripts/build.py`: 위 테스트 후 네이티브 패키징. 생성 EXE 자체로 `--verify-layout`을 실행하여 자막 배치, 언어별 줄, 투명도, 지우기, 기본 행사 데이터 부재를 확인합니다. JSON의 `pass`와 `packaged`를 모두 확인합니다.
3. 실제 발표 전: 자신의 설정으로 마이크·양 언어·화면 분석을 시험합니다. 이 단계는 API 사용량이 발생합니다. [빠른 시작](QUICKSTART.md)의 발화 예시를 사용하세요.

Windows GitHub Actions의 Qt 검증은 offscreen 방식입니다. **실제 Windows 데스크톱에서 마이크와 항상 위 표시까지 검증한 것은 아닙니다.** 로컬 Windows에서는 별도로 EXE를 실행해 확인하세요. `reports/` 화면 캡처는 로컬에만 남기며 릴리스에 포함하지 않습니다.

Windows 영어/한국어 출력 빌드는 추가로 EXE의 10초 대기/재개/중지 UI 검사를 실행하고 manifest의 `ui_validation`에 기록합니다. 이 검사는 가짜 연결 상태를 사용하며 클라우드에 연결하지 않습니다.

소스에 남아 있는 `--verify-generic`, `--verify-korean`, `--verify-preconnect`, `--verify-release` 등의 과거 통합 검증 명령은 실제 Azure 또는 외부 WAV/이미지를 요구할 수 있습니다. 공개 빌드는 이 명령을 사용하지 않으며, 개인 녹음·슬라이드는 제공하지 않습니다.

## 릴리스

- `python scripts/scan_public.py`와 `git diff --cached`를 검사합니다.
- API 키·설정 파일·개인 발표 자료·과거 개인용 EXE가 들어 있으면 중단합니다.
- main/PR에서 `Windows EXE` Actions가 두 앱을 빌드합니다.
- 유지관리자가 `v*` 태그를 push하면 성공한 ZIP만 GitHub Release에 게시합니다.
- ZIP의 manifest에 EXE SHA-256, Git commit, Python/의존성 버전, 검증 결과가 기록됩니다.
- 의존성 업그레이드는 테스트 및 새 Windows 빌드로 확인한 후 반영합니다.

## 2026-10-16 작업 및 검증 기록

이번 소스 반영은 영어/한국어 출력 앱만 대상으로 합니다. STT 전용 인식과 사전 연결 재사용, 선택적 맥락 교정, 영어 문장 연결/대소문자, 이미지 동음이의어 지침, 설정창을 열어 둔 화면 분석, 진단/사용량 기록, 10초 무음 대기 표시를 옮겼습니다. 공개판의 개인 설정 로더·저장 UI와 선택적 Vision 동작을 보존했습니다.

개발 순서는 Mac 수정/검사 → Mac 개인용 패키지 검증 → Windows 전용 작업 폴더에서 빌드/검증 → 공개판 설정 분리 및 오프라인 회귀검사입니다. 개인용 계정 정보, 실행파일, 녹음·강의 자료·사진·화면 캡처는 저장소에 포함하지 않습니다. 공개 소스에서 새로 빌드한 결과만 배포할 수 있습니다.

| 확인 항목 | 결과와 범위 |
|---|---|
| 설정창 제외 캡처 | Mac 네이티브 캡처와 Windows 창 제외 API에서, 설정창이 보이는 상태로 뒤쪽 시험 색상을 캡처하는 검사 통과 |
| 대기/자막 UI | 10초 무음 표시, 발화 재개/중지 시 해제, 레이아웃 및 언어 유지 검사 통과. 연결 상태를 제어한 오프라인 검사이며 실제 마이크 시험과 다름 |
| Windows 개인용 빌드 | EXE 자체 캡처·UI·레이아웃 검사, x64 PE 형식과 SHA-256 및 전송 후 소스 해시 확인. 해당 바이너리는 공개 릴리스에 사용하지 않음 |
| 사진/강의 클라우드 시험 | 일부 시험을 수행했으나 화면 캡처 불일치와 시간 초과/생략이 관찰됨. 사용자 확인 후 다음 단계로 진행했으며, 10분 전체 측정은 중단됨 |
| 제한 | 강의 부분 로그에 요청 실패 22건과 자막 생략 이벤트 2건이 기록됨. 실패 요청 수는 누락 자막 수와 같지 않음. 시험 재생 종료에서 QThread 정리 오류가 있어 장시간/강제 종료 안정성 완료로 보지 않음 |

이 표는 개발 과정의 범위를 기록한 것이며, 공개판의 새 Windows CI 결과나 실제 마이크·클라우드 완전 성공을 대신하지 않습니다. 2시간 강의 비용은 확정하지 않았습니다.

### 추가 검증 명령

- `--verify-windows-smoke OUTPUT`: 연결 상태를 제어한 오프라인 10초 대기/자막 UI 검사. 마이크·Azure 요청 없음.
- `--verify-native-capture OUTPUT`: 실제 데스크톱을 사용하는 로컬 창 제외 캡처 검사. 캡처 권한과 사용 가능한 표시 화면이 필요하며, GUI 없는 CI에서는 실행하지 않습니다.
- `--verify-diagnostics OUTPUT`, `--verify-first-caption OUTPUT`, `--verify-correction OUTPUT`, `--verify-live OUTPUT`: **유료 Azure 호출 또는 사용자 제공 시험 자료가 필요한 개발 명령**입니다. 명시적으로 승인된 시험에만 사용합니다. 일반 CI에는 넣지 않습니다. `--verify-live`의 plan.json·WAV·시험 이미지/강의 프레임은 개인 자료이므로 별도로 준비하고 커밋하지 않습니다.

영어/한국어 출력 앱의 Mac 캡처 의존성은 Cocoa, Quartz, CoreMedia, ScreenCaptureKit 및 pyobjc-core 11.1입니다. Quartz의 CGImage 타입/소유권 연결을 초기화하고 콜백 안에서 이미지 데이터를 복사하여 수명을 보장합니다. Windows 캡처는 Win32 API로 앱 창을 캡처 순간에만 제외하고 finally에서 원래 상태로 복원합니다.
