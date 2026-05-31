"""
RAGAS evaluation for ImmigraAssist RAG pipeline.
Run: python tests/test_ragas.py
"""

import asyncio
import json
import os
import sys
import httpx
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["LANGSMITH_PROJECT"] = "immigraassist"

from dotenv import load_dotenv
load_dotenv(".env")

BASE_URL = "http://localhost:8000"
EMAIL = "nithish@immigraassist.com"
PASSWORD = "test1234"


async def get_token() -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
        return response.json()["access_token"]


async def query_app(token: str, question: str) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat/query",
            json={"query": question},
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()


async def collect_responses(questions: list) -> list:
    print(f"\nCollecting responses for {len(questions)} questions...")
    token = await get_token()
    results = []

    for i, item in enumerate(questions):
        print(f"  [{i+1}/{len(questions)}] {item['question'][:60]}...")
        try:
            response = await query_app(token, item["question"])
            answer = response.get("answer", "")
            cited_laws = response.get("cited_laws", [])
            cited_cases = response.get("cited_cases", [])
            # use answer itself as context since we don't have raw chunks
            # this tests if answer is self-consistent and relevant
            contexts = cited_laws + cited_cases
            if not contexts:
                contexts = [answer[:500] if answer else "No context retrieved"]
            else:
                # combine labels with answer text for better context
                contexts = [f"{c}: {answer[:300]}" for c in contexts[:3]]
            results.append({
                "question": item["question"],
                "answer": answer,
                "contexts": contexts,
                "ground_truth": item["ground_truth"],
            })
            await asyncio.sleep(2)
        except Exception as e:
            print(f"    Error: {e}")
            results.append({
                "question": item["question"],
                "answer": "",
                "contexts": ["No context retrieved"],
                "ground_truth": item["ground_truth"],
            })

    return results


def run_ragas_eval(results: list) -> dict:
    print("\nRunning RAGAS evaluation...")

    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    data = {
        "question": [r["question"] for r in results],
        "answer": [r["answer"] for r in results],
        "contexts": [r["contexts"] for r in results],
        "ground_truth": [r["ground_truth"] for r in results],
    }

    dataset = Dataset.from_dict(data)

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    import httpx as _httpx
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        request_timeout=120,
        max_retries=3,
    )
    result = evaluate(
        dataset=dataset,
        metrics=[answer_relevancy],
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
    )

    return result


def print_results(result, responses: list):
    print("\n" + "="*60)
    print("IMMIGRAASSIST RAGAS EVALUATION RESULTS")
    print("="*60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Questions evaluated: {len(responses)}")
    print()

    scores = result.to_pandas()
    relevancy = float(scores["answer_relevancy"].mean())
    avg = relevancy

    print("SCORES:")
    print(f"  Answer Relevancy:  {relevancy:.3f} / 1.000")
    print(f"\n  Overall Average:   {avg:.3f} / 1.000")
    print()

    if avg >= 0.80:
        print("  Grade: EXCELLENT")
    elif avg >= 0.70:
        print("  Grade: GOOD")
    elif avg >= 0.60:
        print("  Grade: ACCEPTABLE")
    else:
        print("  Grade: NEEDS IMPROVEMENT")

    print("="*60)

    output = {
        "timestamp": datetime.now().isoformat(),
        "num_questions": len(responses),
        "scores": {
            "answer_relevancy": round(relevancy, 3),
            "average": round(avg, 3),
        },
        "responses": responses,
    }

    with open("tests/ragas_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to tests/ragas_results.json")


async def main():
    with open("tests/eval_dataset.json") as f:
        questions = json.load(f)

    test_questions = questions[:20]
    print(f"Running eval on {len(test_questions)} questions")

    responses = await collect_responses(test_questions)
    result = run_ragas_eval(responses)
    print_results(result, responses)


if __name__ == "__main__":
    asyncio.run(main())
