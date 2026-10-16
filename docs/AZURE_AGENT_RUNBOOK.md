# 에이전트용: Azure가 없는 사용자도 A부터 Z까지 사용 준비하기

이 문서는 코딩 에이전트의 실행 절차입니다. **사용자가 Azure를 이미 준비했다고 가정하지 마세요.** 사용자가 설치·사용 준비를 맡겼다면, 문서 링크를 건네거나 EXE를 만든 시점에서 끝내지 말고 아래 단계를 직접 진행하세요. 가능한 작업은 CLI/API/사용자가 허용한 브라우저로 수행하고, 직접 조작할 수 없는 단계만 사용자를 한 단계씩 안내하세요.

문서 수정이나 오프라인 빌드만 요청한 경우에는 그 범위를 지킵니다. 이 지시문 자체는 특정 구독에서 유료 리소스를 생성하라는 승인이 아닙니다.

## 0. 시작할 때

- README, AGENTS.md, [사용자용 Azure 안내](AZURE_SETUP.md), [빌드·검증](BUILD_AND_TEST.md)을 읽습니다.
- 먼저 OS, 저장소 위치, Git/Python/Azure CLI 설치 여부, 현재 Azure 로그인·구독 상태를 확인합니다. 키·토큰은 출력하지 않습니다.
- 사용자가 Azure 용어를 안다고 가정하지 않습니다. 확인할 수 없는 항목만 간단히 묻습니다. 예: “Azure 계정이나 구독이 있으신가요? 없어도 함께 만들 수 있습니다.” “월 예산이나 크레딧 한도가 있나요?”
- 사용자가 “모르겠다”고 하면 기본 방향을 설명하고 확인을 도와주세요. 지역·SKU·배포 이름·쿼터를 사용자가 먼저 알아오도록 요구하지 마세요.
- `계정/구독 → 사용 가능 지역·모델 → 비용 확인 → 서비스 생성 → 개인 설정 저장 → EXE → 실제 발화/화면 시험` 순서를 짧게 알립니다.
- 로컬 `reports/azure-setup.local.md`에 비밀정보 없이 진행 상태를 기록하면 중단 후 재개하기 쉽습니다. 완료/대기/미검증을 구분하고 해당 파일은 Git에 올리지 않습니다.

## 1. 계정이 없는 경우부터 안내하기

1. [Azure Portal](https://portal.azure.com)을 사용자가 허용한 브라우저에서 엽니다. 기존 로그인 계정이 맞는지도 확인합니다.
2. 계정이 없으면 Microsoft 계정 생성·Azure 가입 경로를 안내합니다. 교육용 혜택은 현재 자격과 조건을 확인하며 무료라고 단정하지 않습니다.
3. 비밀번호, MFA, CAPTCHA, 본인 인증, 카드 정보, 결제·구독 약관 동의는 사용자가 직접 처리하도록 해당 화면과 필요한 행동을 정확히 알려 줍니다. 비밀번호·인증 코드를 채팅으로 받지 않습니다.
4. 로그인 완료 후 에이전트가 다시 이어서 구독의 활성 상태와 사용 가능한 권한을 확인합니다. 구독이 여러 개면 대상 구독을 확정하고 이후 명령마다 명시합니다.
5. 조직 구독의 생성 권한이 없다면 부족한 권한/정책과 관리자에게 요청할 내용을 정리합니다. 다른 계정이나 더 높은 역할로 임의 우회하지 않습니다. 이때도 앱의 오프라인 빌드는 계속할 수 있습니다.

사용자의 직접 처리가 필요한 순간에는 “Azure 세팅을 끝내고 오세요”라고 하지 마세요. **지금 눌러야 할 항목 하나와 완료 확인 방법**을 안내하고, 답을 받으면 에이전트가 다음 단계부터 계속합니다.

## 2. CLI 준비와 읽기 전용 조사

CLI가 없다면 [Microsoft 설치 안내](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)를 따라 OS에 맞게 설치합니다. CLI 사용이 제한되면 같은 작업을 Azure Portal에서 진행합니다. 브라우저 조작 도구도 없으면 메뉴·입력값·성공 표시를 단계별로 설명합니다.

다음은 **PowerShell 명령 예시**입니다. Bash에서는 해당 셸 문법으로 바꾸세요. `az login`의 사용자 인증은 직접 진행하도록 하고 반환된 토큰을 출력하지 않습니다.

```powershell
az version
az login --output none
az account list --query "[].{name:name,id:id,state:state,isDefault:isDefault}" --output table
```

대상 구독을 정한 뒤 변수에 실제 값을 넣고 조회합니다. 지역은 가까운 후보를 조사하며 제공 여부와 데이터 처리 지역을 함께 확인합니다.

```powershell
$CaptionSubscription = '사용자가 확인한 구독 ID'
$CaptionSpeechRegion = '조사할 Speech 지역 코드'
$CaptionModelRegion = '조사할 모델 지역 코드'
az cognitiveservices account list --subscription $CaptionSubscription --output table
az cognitiveservices account list-skus --kind SpeechServices --location $CaptionSpeechRegion --subscription $CaptionSubscription --output json
az cognitiveservices model list --location $CaptionModelRegion --subscription $CaptionSubscription --output json
```

현재 모델 카탈로그, 배포 가능한 버전/SKU, 구독의 사용량·쿼터를 포털과 CLI에서 확인합니다. **카탈로그에 나온다는 것만으로 배포 가능한 쿼터가 있다고 판단하지 않습니다.** OpenAI 리소스가 이미 있으면 `account list-models`, `account list-usage`, `account deployment list`도 확인합니다. 기존 서비스는 소유·용도·지역·권한을 확인해 재사용을 제안하며 임의로 변경하지 않습니다.

공식 명령 참조: [리소스 조회/생성](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account?view=azure-cli-latest), [지역별 모델](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/model?view=azure-cli-latest).

## 3. 실제 생성 계획과 비용을 함께 제시하기

조회한 결과로 다음 표를 **실제 값**으로 채운 뒤 확인받습니다. 확인 전에 비용 확인과 명령 준비까지 끝내세요. 사용자에게 SKU 목록만 던져서 선택하게 하지 말고 목적·예산에 맞는 안을 추천하세요.

| 항목 | 에이전트가 정리할 값 |
|---|---|
| 대상 | 구독, 신규/기존 리소스 그룹, 각 리소스 이름 |
| Speech | 지역, 제공되는 F0 또는 S0, 인식/번역 사용 한도와 과금 항목 |
| 모델 | 리소스 지역, 모델/버전, 배포 이름, 지원 배포 유형/SKU·용량, 입력/출력·이미지 요금 |
| Vision | 기본 생략 또는 사용 목적·지역·SKU·요금 |
| 운영 비용 | 사용자가 정한 예산, 예산 알림·크레딧 확인, 알림이 자동 차단인지 여부 |
| 연결 시험 | 짧은 시험의 범위·시간·최대 호출 수와 비용 발생 여부 |

기준 모델은 gpt-5-mini이며 제공되지 않으면 지역/쿼터를 먼저 확인합니다. 이름만 보고 대체 모델을 자동 배포하지 않습니다. 다른 모델/SKU/지역이 필요하면 호환성·요금·데이터 처리 범위의 차이를 설명하고 변경분을 확인받습니다. GPT-5-mini의 배포 이름은 `gpt-5`로 시작하게 합니다. 영어/한국어 출력 앱에서 Luna를 선택한 경우에는 `gpt-6-luna` 또는 `gpt-6-luna-…` 이름과 `none` 요청 호환성을 확인합니다. JP/VN 앱의 모델 계약은 별도이며 [모델 호환성](AZURE_SETUP.md#모델-호환성)을 따릅니다.

승인 예시: “이 구독에 위 두 리소스와 모델을 만들고, Vision은 생략하며, 생성 후 2분 이내의 발화 및 화면 시험을 진행해도 될까요? 사용량은 본인 구독에 청구됩니다.” 구체적 가격은 현재 포털/공식 요금을 확인해 제시하고 모르는 금액을 만들지 않습니다. 승인된 범위 안에서는 클릭마다 다시 묻지 말고 연결 시험까지 계속합니다. 비용이나 권한 범위가 달라지는 경우에만 변경을 확인합니다.

## 4. 승인 후 에이전트가 리소스를 생성하기

CLI 또는 포털을 **에이전트가 직접 조작**하여 그룹, Speech, Azure OpenAI 리소스, 모델 배포를 생성합니다. 로그인·결제 동의를 제외한 리소스 생성까지 전부 사용자에게 떠넘기지 마세요. Vision은 승인한 경우에만 추가합니다.

아래는 승인된 계획을 명령으로 옮기는 틀입니다. **그대로 실행하는 설치 스크립트가 아닙니다.** 모든 변수는 에이전트가 실제 조회 결과와 승인 내용으로 채웁니다. 모델 버전과 배포 SKU/용량을 추측하거나 예제 숫자를 그대로 쓰지 않습니다.

```powershell
# $CaptionGroup, $CaptionGroupRegion, $CaptionSpeechName, $CaptionSpeechSku,
# $CaptionModelName, $CaptionModel, $CaptionModelVersion,
# $CaptionDeployment, $CaptionDeploymentSku, $CaptionCapacity도 먼저 확정해야 합니다.
az group create --name $CaptionGroup --location $CaptionGroupRegion --subscription $CaptionSubscription --output none
az cognitiveservices account create --name $CaptionSpeechName --resource-group $CaptionGroup --kind SpeechServices --sku $CaptionSpeechSku --location $CaptionSpeechRegion --subscription $CaptionSubscription --output none
az cognitiveservices account create --name $CaptionModelName --resource-group $CaptionGroup --kind OpenAI --sku S0 --location $CaptionModelRegion --custom-domain $CaptionModelName --subscription $CaptionSubscription --output none
az cognitiveservices account deployment create --name $CaptionModelName --resource-group $CaptionGroup --deployment-name $CaptionDeployment --model-name $CaptionModel --model-version $CaptionModelVersion --model-format OpenAI --sku-name $CaptionDeploymentSku --sku-capacity $CaptionCapacity --subscription $CaptionSubscription --output none
```

**한 명령씩 실행하고 종료 코드와 생성 상태를 확인한 뒤 다음 단계로 진행합니다.** 재시도 전에 동일 이름의 리소스를 조회해서 실제로 생성되었는지 확인하세요. 기존 리소스에 create를 무조건 다시 실행하거나 설정을 덮어쓰지 않습니다. 이름 충돌, 리소스 공급자 미등록, 지역 제한, 쿼터 부족은 원인을 확인한 뒤 승인 범위 안에서 해결합니다. 공급자 등록도 필요한 권한과 구독 변경 범위를 확인하고 진행합니다.

모델 생성 명령: [Microsoft 배포 CLI 문서](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest). 인증/정책상 포털 작업이 필요하면 같은 승인 내용으로 포털에서 이어갑니다. 자동화할 수 없는 동의 화면이 나오면 사용자에게 그 단계만 요청합니다.

부분 실패 시 이미 만든 리소스와 남은 단계를 기록합니다. 실패했다고 리소스 그룹을 자동 삭제하지 마세요. 정리가 필요하면 이번 작업으로 만든 정확한 리소스와 영향 범위를 제시하고 요청받은 범위에서만 정리합니다.

## 5. 키를 안전하게 개인 설정으로 연결하기

- 키를 채팅·터미널 출력·작업 로그·스크린샷에 표시하지 않습니다. `az ... keys list`를 출력하는 명령을 그대로 호출하지 마세요.
- Windows에서는 `scripts/import-azure-settings.ps1`에 확정한 구독/그룹/리소스/배포 이름을 전달해 키를 개인 파일로 가져옵니다. 명령 사용법은 [Azure 설정 안내](AZURE_SETUP.md)의 5절에 있습니다. 이 스크립트는 **생성 후 가져오기용**이며 리소스 생성 기능은 없습니다.
- 스크립트의 `SAVE`는 기존 개인 설정 덮어쓰기 확인입니다. 에이전트는 저장 경로·교체할 설정을 설명하고 기존 승인 범위인지 확인해 처리합니다. 이미 승인받은 동일 작업의 승인을 불필요하게 반복하지 않습니다.
- macOS에서는 CLI 출력을 프로세스 내부 변수로만 받아 `runtime_config.save_settings()`로 개인 설정에 저장하거나, 사용자가 앱의 마스킹된 필드에 직접 입력하도록 안내합니다. 키 값을 셸 명령 인자나 생성한 소스에 넣지 않습니다.
- 저장 위치는 OS별 개인 설정 경로입니다. 평문 파일이라는 점을 알리고, 저장소/EXE/공유 폴더에 넣지 않습니다. 키 없는 설정 예제를 실제 키로 덮어쓰지 마세요.
- 설정 파일의 필수 필드가 비어 있지 않은지와 지역·엔드포인트·배포 이름의 대응 관계만 검사합니다. 결과에는 키 값을 표시하지 않습니다.

## 6. EXE부터 실제 자막까지 확인하기

구독 가입이나 권한 승인을 기다리는 동안 Git/Python 준비, 클론, 오프라인 테스트와 Windows 빌드를 진행할 수 있습니다. 준비가 끝나면 계정 설정 단계로 돌아와 계속합니다.

1. [빌드 절차](BUILD_AND_TEST.md)대로 두 앱을 검증합니다. Windows가 없으면 사용자 권한이 있는 GitHub Fork의 Actions를 이용하고 결과를 다운로드합니다.
2. 개인 설정을 읽어 앱을 실행하고 사전 연결 준비 상태를 확인합니다. **설정이 있는 앱 실행 자체에 모델 준비 요청이 생길 수 있으므로** 3단계의 시험 승인 범위에 포함합니다.
3. 기본 마이크, 마이크 권한, 캡처 대상 모니터를 확인합니다. Mac에서는 화면 기록 권한도 안내합니다. 녹음/화면이 Azure로 전달된다는 점을 설명합니다.
4. 사용자에게 한국어 한 문장과 영어 한 문장을 읽도록 요청합니다. 테스트 자료와 화면은 사용자가 허용한 것으로만 사용하며, [빠른 시작의 예문](QUICKSTART.md)을 활용할 수 있습니다.
5. 영어/한국어 선택 및 JP-VN 양쪽 출력, 숫자·부정·언어 유지, 마지막 자막 지우기를 확인합니다. 화면 분석은 따로 켜고 이미지 미리보기와 실제 번역 반영을 확인합니다. Vision을 생략한 경우 문자 힌트가 없는 것은 정상입니다.
6. 시험이 끝나면 분석/음성 처리를 중지하고 앱을 종료합니다. 승인된 시험 시간을 무한 재시도로 초과하지 않습니다.
7. Azure 사용량/비용 화면 확인 방법, 다음 실행 순서, 설정 위치, 사용을 멈추는 방법까지 설명합니다. 비용 반영 지연과 크레딧의 실제 잔액을 구분합니다.

오프라인 테스트, 실제 인증, 마이크 입력, 번역 출력, 화면 이미지 반영은 서로 다른 검증입니다. 한 단계의 성공을 전체 성공으로 보고하지 않습니다. 실제 발화를 할 수 없으면 그 항목을 미검증으로 남기고 사용자가 해야 할 한 단계만 제시합니다.

## 7. 막혔을 때도 다음 행동을 안내하기

| 상황 | 에이전트의 다음 행동 |
|---|---|
| 계정·구독 없음 | 가입 화면과 사용자 직접 입력 부분 안내 → 완료 후 활성 구독 확인 |
| MFA/결제/약관 | 정확한 화면과 필요한 행동을 안내하고 사용자 처리를 기다림 → 자동 재개 |
| 권한/조직 정책 차단 | 오류 범위와 관리자에게 요청할 내용을 정리, 독립적인 빌드 계속 |
| F0 불가/모델 쿼터 없음 | 기존 리소스·허용 지역·할당량 조사, 비용/지역 변경은 확인 후 적용 |
| 모델 400/404 | 기본 엔드포인트, 실제 배포 이름, 모델 요청 매개변수 호환성 확인 |
| 401/403 | 키와 서비스의 대응, 지역, 접근 권한/네트워크 정책 확인; 키를 출력하지 않음 |
| 429/시간 초과 | 쿼터·동시 호출·네트워크 확인, 제한된 재시도; 고가 모델로 자동 전환 금지 |
| 에이전트에 도구 없음 | 그 단계를 실행할 한 가지 방법과 성공 표시를 안내, 결과를 받아 다음 단계 진행 |

최종 보고에는 **리소스 생성 여부, 연결 여부, 실제 자막 시험 결과, EXE 위치, 남은 사용자 행동**을 구분하세요. 완료하지 못한 단계가 있으면 “A부터 Z까지 완료”라고 쓰지 않습니다. 일반적인 설치 요청의 완료 목표는 사용자가 자기 계정으로 실제 자막을 사용할 수 있는 상태입니다.
