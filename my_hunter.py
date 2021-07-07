import requests as requests

API_KEY = '0d8bf2585df04ccbb1ccd2334236db9725c84022'


def email_verification(email):
    url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={API_KEY}"
    response = requests.get(url)

    if response.status_code == 200 and response.json()['data']['status'] == 'valid':
        return True
    return False
