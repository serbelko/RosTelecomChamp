import requests
import json

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": "Bearer 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",
  },
  data=json.dumps({
    "model": "deepseek/deepseek-r1-0528-qwen3-8b:free", # Optional
    "messages": [
      {
        "role": "user",
        "content": "What is the meaning of life?"
      }
    ]
  })
    
)
