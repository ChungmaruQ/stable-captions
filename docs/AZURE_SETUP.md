# 내 Azure 계정으로 처음 설정하기

공개 앱은 개발자의 구독과 연결되지 않습니다. **본인의 구독에서 만든 리소스의 설정**을 입력해야 합니다. Microsoft 계정 로그인, 구독 신청/결제 동의, 조직 승인 등은 사용자가 직접 진행합니다. 교육용 계정 자체가 서비스 사용 권한·무료 사용량·모델 할당량을 보장하지는 않습니다.

## 필요한 서비스

| 구성 | 용도 | 필요 여부 |
|---|---|---|
| Azure AI Speech | 한국어/영어 인식 및 기본 음성 번역 | 필수 |
| Azure OpenAI 리소스 + 모델 배포 | 문맥·이미지를 참고한 번역, JP/VN 번역 | 전체 기능 사용 시 필수, 권장 구성 |
| Azure AI Vision / Computer Vision | 슬라이드의 문자 힌트 | 선택, 없어도 전체 이미지는 모델에 전달 |

별도의 Azure Translator 리소스는 필요하지 않습니다. 각 리소스 지역이 달라도 되지만 Speech의 지역 입력은 **Speech 리소스의 실제 지역**과 일치해야 합니다. 모델의 제공 지역·쿼터·버전은 구독마다 달라지므로 포털에서 확인하세요.

## 1. 구독과 비용 확인

1. [Azure Portal](https://portal.azure.com)에 본인의 계정으로 로그인합니다.
2. `Subscriptions / 구독`에서 사용 가능한 구독과 남은 크레딧·지출 한도를 확인합니다.
3. `Cost Management / 비용 관리`에서 예산과 알림을 설정합니다. **예산 알림은 자동 사용 중지 장치가 아닙니다.**
4. 이 앱만 위한 리소스 그룹(예: `stable-captions-rg`)을 정해 두면 나중에 비용 확인·정리가 쉽습니다.

이 안내에 고정 가격이나 무료 시간을 적지 않은 이유는 Speech의 인식/번역 미터, 모델, 지역, 배포 유형 및 무료 제공 조건이 다르기 때문입니다. 생성 전 포털의 SKU/가격과 [Speech 요금](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/), [Azure OpenAI 요금](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/), [Vision 요금](https://azure.microsoft.com/pricing/details/cognitive-services/computer-vision/)을 확인하세요.

## 2. Speech 리소스 생성

1. Azure Portal에서 `Speech`를 검색하고 Microsoft의 Speech 리소스 생성 화면을 엽니다.
2. 본인 구독, 위 리소스 그룹, 가까운 제공 지역, 고유한 리소스 이름을 선택합니다.
3. 가격 계층은 작은 테스트에 F0가 제공되는지 확인하세요. F0가 없거나 한도를 초과하면 S0 비용을 확인한 뒤 선택합니다. 기존 F0 리소스 보유·구독 조건에 따라 생성이 제한될 수 있습니다.
4. `검토 + 만들기`에서 설정과 요금을 확인하고 본인이 생성합니다.
5. 생성된 리소스 → `Keys and Endpoint / 키 및 엔드포인트`에서 Key 1과 Location/Region 코드를 확인합니다.
6. 앱 메인 창의 `Azure 키`와 `지역`에 입력합니다. 지역은 `Korea Central` 같은 표시 이름이 아닌 `koreacentral` 같은 코드입니다.

키를 채팅에 붙여 넣거나 스크린샷으로 공유하지 마세요. 앱의 마스킹된 입력란에 직접 붙여 넣으면 됩니다. Microsoft [Speech Translation 시작 문서](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-speech-translation)도 참고하세요.

## 3. 모델 리소스와 배포 생성

1. Azure Portal에서 Azure OpenAI 리소스를 생성합니다. 본인 구독, 그룹, **원하는 모델 배포가 가능한 지역**을 선택합니다. 모델이 보이지 않으면 다른 지원 지역이나 구독 쿼터를 확인하세요.
2. 해당 리소스에서 Microsoft Foundry 포털을 열어 모델 배포 화면으로 이동합니다. 포털 메뉴 이름은 업데이트될 수 있습니다.
3. 공개 앱의 기준 모델은 **gpt-5-mini**입니다. 이 모델의 사용 가능 여부, 모델 버전, 배포 유형, 할당량을 확인하고 배포합니다. 자동으로 더 비싼 모델로 바꾸지 마세요.
4. 초보자 권장 배포 이름은 **`gpt-5-mini`**입니다. 리소스 이름과 배포 이름은 서로 다른 항목입니다.
5. Azure OpenAI 리소스의 키와 **리소스 기본 엔드포인트**를 가져옵니다. 예: `https://YOUR-RESOURCE.openai.azure.com`.
6. 앱의 **슬라이드 화면 분석 · 맥락 번역 설정**에서 모델 엔드포인트, 모델 키, 배포 이름을 입력합니다. 엔드포인트 뒤에 `/openai/...`를 붙이지 않습니다.
7. 메인 창으로 돌아가 **내 Azure 설정 저장**을 누릅니다. 키와 배포를 입력해 저장하면 맥락 번역이 활성화됩니다.

### 모델 호환성

현재 요청은 `/openai/v1/chat/completions`를 사용합니다. GPT-5 계열은 **배포 이름이 `gpt-5`로 시작할 때** `reasoning_effort=minimal`과 `max_completion_tokens`를 전송합니다. 다른 이름은 비추론 모델용 `temperature=0`/`max_tokens`를 사용합니다. GPT-5-mini 배포를 임의의 별명으로 지으면 요청이 실패할 수 있습니다.

임의의 최신 모델을 이름만 바꿔 사용하면 안 됩니다. 특히 `minimal`을 지원하지 않는 모델, Chat Completions 또는 이미지 입력을 지원하지 않는 모델은 코드와 테스트를 수정해야 합니다. 화면 분석에는 이미지 입력이 가능한 배포가 필요합니다. gpt-5-mini가 없는 구독에서는 AI에게 지원 모델 목록과 요청 호환성을 확인하도록 요청하세요. 저장소를 만드는 AI의 모델 이름과 앱에서 호출하는 Azure 모델은 별개입니다.

## 4. Vision OCR 추가 (선택)

1. 포털에서 `Computer Vision / Azure AI Vision` 리소스를 생성합니다. 제공되는 가격 계층과 지역을 확인합니다.
2. 키 및 엔드포인트에서 기본 엔드포인트와 키를 복사합니다.
3. 앱의 맥락 설정에 Vision 엔드포인트/키를 입력하고 메인 창에서 저장합니다.
4. Vision을 생략하려면 두 칸을 모두 비워 두세요. **이미지 분석 기능 자체는 번역 모델이 수행**하며, Vision은 추가 문자 힌트용입니다.

## 5. 이미 만든 Azure 리소스에서 설정 가져오기 (선택)

앱에서 직접 입력하면 이 단계가 필요 없습니다. [Microsoft Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows)를 설치한 사용자는 `az login`을 본인이 진행한 뒤 다음 스크립트를 사용할 수 있습니다. 이 스크립트는 **리소스를 생성하지 않고**, 지정한 구독의 기존 리소스와 키를 읽어 개인 설정 파일에 저장합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/import-azure-settings.ps1 `
  -SubscriptionId YOUR-SUBSCRIPTION-ID `
  -SpeechResourceGroup YOUR-GROUP -SpeechName YOUR-SPEECH-NAME `
  -ModelResourceGroup YOUR-GROUP -ModelName YOUR-OPENAI-RESOURCE `
  -Deployment gpt-5-mini
```

필요하면 `-VisionResourceGroup YOUR-GROUP -VisionName YOUR-VISION-NAME`도 추가하세요. 파일 경로와 덮어쓰기 안내 후 `SAVE`를 입력해야 저장합니다. 키는 터미널에 출력하지 않습니다. 스크립트 실행 뒤 앱을 다시 시작하세요. 키를 읽는 Azure 권한이 없으면 구독 관리자에게 권한을 요청하거나 앱에 직접 입력하세요.

CLI 참고: [리소스 명령](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account?view=azure-cli-latest), [배포 명령](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest).

## 6. 설정 저장 위치와 우선순위

- Windows: `%LOCALAPPDATA%\StableCaptions\config.json`
- macOS: `~/Library/Application Support/StableCaptions/config.json`
- 두 앱이 같은 파일을 공유합니다.
- `STABLE_CAPTIONS_CONFIG` 환경변수로 별도 파일을 지정할 수 있습니다. 지정한 파일만 읽고 그 경로에 저장합니다.
- 키를 EXE 옆이나 저장소 폴더에 복사할 필요가 없습니다. 파일은 사용자 PC에 **평문**으로 저장되며, macOS에서는 소유자 읽기/쓰기 권한(0600)을 적용합니다. Windows는 사용자 프로필의 파일 권한을 상속합니다.

고급 사용자는 아래 환경변수로 파일 값을 덮어쓸 수 있습니다. 환경변수가 설정되어 있으면 앱에서 저장한 값보다 우선하므로, 설정을 바꿔도 이전 키가 보인다면 환경변수를 확인하세요.

```
AZURE_SPEECH_KEY
AZURE_SPEECH_REGION
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_DEPLOYMENT
AZURE_VISION_ENDPOINT
AZURE_VISION_KEY
```

실제로 서비스가 연결되는지는 앱의 준비 표시와 짧은 발화 테스트로 확인하세요. 설정 저장 성공은 Azure 인증 성공과 다릅니다.
