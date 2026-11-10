import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY", "")

models = sys.argv[1:] or [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]

for model in models:
    start = time.time()
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [{"text": "Reply with the single word: ok"}]}]},
            timeout=60,
        )
        print(f"{model}: HTTP {r.status_code} in {time.time() - start:.1f}s")
        if r.status_code != 200:
            print("   ", r.text[:150].replace("\n", " "))
    except httpx.HTTPError as exc:
        print(f"{model}: {type(exc).__name__} after {time.time() - start:.1f}s")
