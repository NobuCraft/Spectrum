import requests

def ask_duck(message):
    url = "https://duckduckgo.com/duckchat/v1/chat"
    headers = {"User-Agent": "Mozilla/5.0"}
    data = {
        "messages": [{"role": "user", "content": message}],
        "model": "gpt-4o-mini"
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()['message']

# Тест
print("🤖", ask_duck("Привет! Как дела?"))
