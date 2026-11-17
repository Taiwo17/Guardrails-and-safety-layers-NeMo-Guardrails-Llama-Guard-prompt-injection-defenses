import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_FILE = PROJECT_ROOT / "red_team" / "prompts.json"
RESULTS_DIR = PROJECT_ROOT / "red_team" / "results"
OUTPUT_FILE = RESULTS_DIR / "protected-results.json"


def main():
    with PROMPTS_FILE.open("r", encoding="utf-8") as file:
        prompts = json.load(file)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    print(f"Running {len(prompts)} protected red-team tests...\n")

    with TestClient(app) as client:
        for test in prompts:
            print(f"Test {test['id']}: {test['category']}")

            start_time = time.perf_counter()

            try:
                response = client.post(
                    "/chat",
                    json={"message": test["prompt"]}
                )

                elapsed = round(time.perf_counter() - start_time, 2)

                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {"raw_response": response.text}

                result = {
                    "id": test["id"],
                    "category": test["category"],
                    "prompt": test["prompt"],
                    "status_code": response.status_code,
                    "response": response_data.get(
                        "response",
                        response_data.get("detail", response_data)
                    ),
                    "security_decision": response_data.get("security_decision", "UNKNOWN"),
                    "elapsed_seconds": elapsed
                }

            except Exception as error:
                elapsed = round(time.perf_counter() - start_time, 2)

                result = {
                    "id": test["id"],
                    "category": test["category"],
                    "prompt": test["prompt"],
                    "error": str(error),
                    "security_decision": "ERROR",
                    "elapsed_seconds": elapsed
                }

            results.append(result)

            print(f"  HTTP status: {result.get('status_code', 'ERROR')}")
            print(f"  Security decision: {result.get('security_decision', 'UNKNOWN')}")
            print(f"  Time: {elapsed}s")
            print(f"  Response: {str(result.get('response', result.get('error')))[:200]}")
            print()

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    print(f"Completed {len(results)} tests.")
    print(f"Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
