# 응급처치 AI 에이전트

GPT API를 활용해 사용자의 증상을 기반으로 병명을 추론하고, 긴급도에 따라 응급처치를 안내하거나 119 신고를 권유하는 CLI 기반 대화형 AI 에이전트입니다.

---

## 실행 환경 준비

### 1. Python 3.8 이상 설치 확인

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
```

운영체제별로 아래 명령어 중 하나를 사용해 활성화하세요:

- **Windows PowerShell**
  ```bash
  .\venv\Scripts\Activate.ps1
  ```

- **Windows CMD**
  ```cmd
  .\venv\Scripts\activate.bat
  ```

- **macOS/Linux**
  ```bash
  source venv/bin/activate
  ```

### 3. 필요 라이브러리 설치
```bash
pip install openai python-dotenv
```

### 4. `.env` 파일 확인
`.env` 파일은 프로젝트 루트에 포함되어 있으며, 다음과 같은 형식으로 OpenAI API 키를 직접 입력해야 합니다:
```
OPENAI_API_KEY=your_openai_api_key_here
```

이 파일은 `python-dotenv` 라이브러리를 통해 자동으로 로드되며,
API 키가 코드에 노출되지 않도록 관리하기 위한 용도로 사용됩니다.

---

## 실행 방법
```bash
python run.py
```

프로그램을 실행하면 아래와 같은 절차로 작동합니다:

1. 에이전트가 사용자에게 증상을 묻습니다.  
2. 사용자의 자연어 입력을 기반으로 GPT가 증상을 분석합니다.
3. 분석된 증상을 바탕으로 병명을 추론하고, 추가 질문을 통해 병명을 확정합니다.  
4. 병명 확정 후, 긴급도에 따라:
   - 119 신고 권유 또는
   - 맞춤형 응급처치 방법을 안내합니다.
5. 사용자는 "종료", "quit" 등의 명령으로 대화를 종료할 수 있습니다.

---

## 포함 파일 설명

| 파일 | 설명 |
|------|------|
| `run.py` | 실행 진입점. `run_diagnosis_session()` 호출 |
| `emergency_agent.py` | 사용자 입력 수집부터 병명 확정, 후속 조치까지 전체 흐름을 담당하는 에이전트 모듈 (데모 발표를 위한 임시적인 구조 포함) |
| `first_aid_guide.py` | 병명 확정 후, 응급처치 방법을 안내하는 로직 구현 (데모 발표를 위한 임시 파일) |
| `persona.py` | GPT의 역할과 대화 방향을 정의하는 system prompt 설정 |
| `disease_symptom.json` | 병명과 관련 증상 간의 매핑 정보 데이터 |
| `골절.json` | '골절'에 대한 상세 응급처치 내용이 담긴 JSON 파일 (데모 발표를 위한 임시 파일) |
| `followup_utils.py` | 병명 후보에 따라 GPT가 묻는 추가 질문을 생성하고, 진행 흐름을 관리하는 모듈 |
| `gpt_prompt_utils.py` | 질병-증상 데이터를 GPT 프롬프트 형태로 구성하는 유틸리티 모듈 |
| `classify_response.py` | 사용자 응답을 '예/아니오/모르겠음'으로 분류하는 기능 담당 |
| `analyze_prompt.py` | 사용자 초기 입력을 기반으로 증상을 추출하고 병명 후보를 구성하는 초기 분석 모듈 |

---

## 개인정보

- `.env` 파일에 포함된 API 키는 실제 배포 시 절대 공개되지 않도록 주의해야 하며,
- 이 레포지토리에는 키가 포함되지 않은 placeholder 형태만 제공됩니다.

---

## 개발자
- 한밭대학교 컴퓨터공학과 20191732 박준후
- 캡스톤 디자인 프로젝트: "응급처치 AI 에이전트 시스템"
