# 사용자 응답을 GPT로 분류(예/아니오/모르겠음)
import openai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)

# 1. 규칙 기반 분류 함수
def rule_based_classify(user_response: str) -> str | None:
    lower = user_response.lower()

    # 예
    if any(kw in lower for kw in ["예", "있어요", "있습니다", "네", "맞아요", "있는 것 같아요", "그런 것 같아요", "맞는 것 같아요"]):
        return "예"
    
    # 아니오
    elif any(kw in lower for kw in ["없어요", "아니요", "아니오", "없습니다", "아닌 것 같아요", "해당 없음", "해당 안 돼요"]):
        return "아니요"
    
    # 모르겠음
    elif any(kw in lower for kw in ["잘 모르겠어", "모르겠어요", "판단이 어려워요"]):
        return "모르겠음"
    
    return None  # 해당 안 되면 GPT에게 넘긴다

# 2. GPT 기반 분류 함수
def gpt_classify_user_response(question: str, user_response: str) -> str:
    prompt = f"""
[질문]
{question}

[사용자 응답]
{user_response}

[분류 기준]
- 아래 분류는 증상이 '존재하는지 여부'를 기준으로 판단한다.
- 질문과 응답의 의미를 함께 고려하여 분류할 것
- 예: 증상이 있음이 확인된 경우 (예시: '의식을 잃었어요', '가슴 통증이 있어요')
- 아니요: 증상이 없음이 확인된 경우 (예시: '통증은 없어요', '아니요, 의식 있어요')
- 모르겠음: 증상 유무를 명확히 알 수 없는 경우 (예시: '잘 모르겠어요', '판단이 어려워요')

[추가 규칙]
- "있는 것 같아요", "있는거 같아", "그런 증상이 있는 듯해요" → 모두 **'예'로 간주**하라
- 즉, 확실하지 않더라도 **증상이 있다고 말한 경우는 '예'로 분류할 것**

반드시 아래 세 가지 중 하나로만 정확히 분류하라:
- 예
- 아니요
- 모르겠음

==> 분류 결과:
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        timeout=15
    )

    result = response.choices[0].message.content.strip().replace(".", "").replace(" ", "")
    
    if result not in ["예", "아니오", "모르겠음"]:
        return "INVALID"
    
    return result

# 3. 최종 혼합 분류 함수
def classify_user_response(question: str, user_response: str) -> str:
    rule_result = rule_based_classify(user_response)
    if rule_result is not None:
        return rule_result
    else:
        return gpt_classify_user_response(question, user_response)