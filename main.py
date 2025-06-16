import os
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
from typing import Tuple
from pydantic import BaseModel, field_validator

# Load environment variables from .env file
load_dotenv()

# Initialize API clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MAX_ROUNDS = 5

# Define the data model for agent responses
class AgentResponse(BaseModel):
    answer: int 
    explanation: str 

    
    @field_validator("answer", mode="before")
    def parse_answer(cls, v):
        if isinstance(v, int):
            return v
        try:
            return int(''.join(filter(str.isdigit, v.strip().split()[0])))
        except Exception:
            raise ValueError("Invalid integer format for answer.")

def ask_gpt(prompt: str) -> AgentResponse:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content.strip()
    return parse_structured_response(content)

def ask_gemini(prompt: str) -> AgentResponse:
    response = gemini_client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    content = response.text.strip()
    return parse_structured_response(content)

def parse_structured_response(response: str) -> AgentResponse:
    answer = None
    explanation = []
    for line in response.splitlines():
        if line.lower().startswith("answer:"):
            answer = line.split(":", 1)[-1].strip()
        elif line.lower().startswith("explanation:"):
            explanation.append(line.split(":", 1)[-1].strip())
        else:
            explanation.append(line.strip())
    if answer is None:
        raise ValueError("Answer not found in response.")
    return AgentResponse(answer=answer, explanation=' '.join(explanation))

def create_reconsideration_prompt(your_response: AgentResponse, peer_response: AgentResponse) -> str:
    return f"""
You previously answered:
Answer: {your_response.answer}
Explanation: {your_response.explanation}

Another agent answered:
Answer: {peer_response.answer}
Explanation: {peer_response.explanation}

Would you like to reconsider your answer or explanation?

Please respond in this exact format:
Answer: <your new or reaffirmed integer answer>
Explanation: <your explanation or updated reasoning>
"""

def debate_agents(question: str) -> None:

    print("\n--- Round 1 ---")
    gpt_response = ask_gpt(f"Answer the following question. Please respond in the format:\nAnswer: <integer>\nExplanation: <your explanation>\n\nQuestion: {question}")
    gemini_response = ask_gemini(f"Answer the following question. Please respond in the format:\nAnswer: <integer>\nExplanation: <your explanation>\n\nQuestion: {question}")

    print(f"GPT Answer: {gpt_response.answer}")
    print(f"Gemini Answer: {gemini_response.answer}")

    if gpt_response.answer == gemini_response.answer:
        print("\n✅ Consensus Reached on Round 1!")
        return

    for round in range(2, MAX_ROUNDS + 1):
        print(f"\n--- Round {round} ---")

        gpt_prompt = create_reconsideration_prompt(gpt_response, gemini_response)
        gemini_prompt = create_reconsideration_prompt(gemini_response, gpt_response)

        gpt_response = ask_gpt(gpt_prompt)
        gemini_response = ask_gemini(gemini_prompt)

        print(f"GPT Answer: {gpt_response.answer}")
        print(f"Gemini Answer: {gemini_response.answer}")

        if gpt_response.answer == gemini_response.answer:
            print("\n✅ Consensus Reached!")
            return

    print("\n❌ Max rounds reached. No consensus.")
    print(f"\nGPT Final Answer: {gpt_response.answer}\nExplanation: {gpt_response.explanation}")
    print(f"\nGemini Final Answer: {gemini_response.answer}\nExplanation: {gemini_response.explanation}")

if __name__ == "__main__":
    question_input = input("🗣️ Enter a question: ")
    debate_agents(question_input)
