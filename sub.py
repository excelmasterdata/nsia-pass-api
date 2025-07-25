import requests

headers = {
    "Ocp-Apim-Subscription-Key": "ac9063d40c5a488886f9b63dcfe72298"
}

# Test sur l'API MTN info
response = requests.get(
    "https://sandbox.momodeveloper.mtn.com/collection/v1_0/accountholder/msisdn/242061234567/active",
    headers=headers
)

print(f"Test clé: {response.status_code} - {response.text}")