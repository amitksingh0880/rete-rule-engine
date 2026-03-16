import requests
import json

def test_ai(prompt):
    print(f"\nPrompt: {prompt}")
    resp = requests.post("http://localhost:8000/ai/generate", json={"prompt": prompt})
    if resp.status_code == 200:
        print("Generated DSL:")
        print(resp.json()["dsl"])
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)

prompts = [
    "Create a loan approval rule for people with credit score above 750",
    "Reject transactions over 5000",
    "Flag claims with amount exactly 1337 for fraud review",
    "Insurance policy for customers with age below 25",
    "Low income check: annual income under 30000"
]

for p in prompts:
    test_ai(p)
