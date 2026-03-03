import asyncio
import aiohttp
import base64
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_qwen_call():
    api_key = os.getenv("QWEN_API_KEY")
    api_base = os.getenv("QWEN_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("QWEN_FLASH_MODEL", "qwen-vl-max-latest")

    print(f"Testing Qwen API...")
    print(f"Base URL: {api_base}")
    print(f"Model: {model}")
    
    # Create a small 1x1 black pixel as dummy image
    dummy_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    
    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in one word."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{dummy_image_base64}"}}
                ]
            }
        ],
        "max_tokens": 10
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                status = response.status
                text = await response.text()
                print(f"Response Status: {status}")
                if status == 200:
                    data = json.loads(text)
                    print(f"Response Content: {data['choices'][0]['message']['content']}")
                    print("SUCCESS: Real API call verified!")
                else:
                    print(f"FAILURE: {text}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_qwen_call())
