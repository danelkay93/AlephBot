import http.client
import json

def get_nikud(text: str) -> str:
    """
    Sends Hebrew text to the Nakdan API and returns it with niqqud.
    """
    try:
        connection = http.client.HTTPSConnection("nakdan-5-1.loadbalancer.dicta.org.il")
        payload = json.dumps({
            "data": text,
            "genre": "modern"  # Options: 'modern', 'poetry', etc.
        })
        headers = {
            'Content-Type': 'application/json'
        }
        connection.request("POST", "/api", payload, headers)
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        connection.close()

        # Extract the vowelized text from the response
        words = map(lambda w: w['options'][0] if len(w['options']) > 0 else w['word'], data)
        return "".join(words)

    except Exception as e:
        print(f"Error interacting with Nakdan API: {e}")
        return "An error occurred while processing the text."
