# 응급처치 AI 에이전트 실행 가이드

# 환경 준비
1. Python 3.8 이상 설치 확인  

2. 가상환경 생성 및 활성화 (권장)
    ```bash
    python -m venv venv
    
    # Windows PowerShell:
    .\venv\Scripts\Activate.ps1    
    # Windows CMD:
    .\venv\Scripts\activate.bat    
    # macOS/Linux:
    source venv/bin/activate
    ```

3. 의존 라이브러리 설치
    ```bash
    pip install -r requirements.txt
    ```

4. .env 파일 생성 및 OpenAI API 키 설정, 프로젝트 루트에 .env 파일 생성 후 아래 내용 추가
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    ```

# 실행 방법
1. run.py 실행
    ```bash
    python run.py
    ```

2. 터미널에 출력되는 에이전트 메시지를 확인하고
    - 사용자 질문에 맞춰 증상 등을 입력하여 대화를 진행하세요.

3. 프로그램 종료
    - 대화 중 'exit', '종료', 'quit' 입력 시 종료됩니다.
    - 응급 상황 발생 시 119 신고를 안내합니다.

# 파일 구성
- emergency_agent.py: AI 응급처치 에이전트의 핵심 진단 로직 구현
- run.py: 실행 진입점 스크립트 (여기서 run_diagnosis_session() 호출)
- 기타 유틸리티 및 데이터 파일 포함

# 참고
- 본 프로그램은 CLI 기반 대화형 인터페이스로 설계되었습니다.
- 추후 FastAPI 등 백엔드 연동도 계획되어 있습니다.