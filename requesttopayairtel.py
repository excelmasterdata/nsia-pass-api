import requests
from base64 import b64encode
import uuid

# === Configuration ===
client_id = "44acdec1-c08f-4ec6-b95b-602842d20864"
client_secret = "6496a519-483a-46ce-b926-af5ac179fb4f"
auth_url = "https://openapi.airtel.africa/auth/oauth2/token"
payment_url = "https://openapi.airtel.africa/merchant/v1/payments/"


headers_base = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Country": "CG",
    "X-Currency": "XAF"
}

# === 1. Obtenir le token d'accès ===
def get_token():
    credentials = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    response = requests.post(auth_url, json=credentials, headers=headers_base)
    if response.status_code == 200:
        token = response.json()['access_token']
        print("Token obtenu avec succès.")
        return token
    else:
        print("Échec lors de l'obtention du token :", response.text)
        return None

# === 2. Initier un paiement Airtel Money ===
def make_payment(token, phone_number, amount, transaction_id):
    headers = headers_base.copy()
    headers["Authorization"] = f"Bearer {token}"

    payload = {
        "reference": transaction_id,   
        "subscriber": {
            "country": "CG",
            "currency": "XAF",
            "msisdn": phone_number      
        },
        "transaction": {
            "amount": str(amount),
            "country": "CG",
            "currency": "XAF",
            "id": transaction_id
        }
    }

    response = requests.post(payment_url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Paiement initié avec succès :", response.json())
    else:
        print("Échec du paiement :", response.status_code, response.text)


if __name__ == "__main__":
    token = get_token()
    print(token)
    if token:
        make_payment(
            token=token,
            phone_number="055852359",  
            amount=300,                  
            transaction_id=uuid.uuid4().hex[:16]
        )
  