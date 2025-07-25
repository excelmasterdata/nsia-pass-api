import requests
import json
import uuid

url = "https://proxy.momoapi.mtn.com/collection/v1_0/requesttopay"

payload = json.dumps({
  "amount": "100",
  "currency": "XAF",
  "externalId": str(uuid.uuid4()),
  "payer": {
    "partyIdType": "MSISDN",
    "partyId": "242066607624"
  },
  "payerMessage": "Test payment",
  "payeeNote": "Subscription"
})
headers = {
  'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSMjU2In0.eyJjbGllbnRJZCI6IjUzMDg3YjA3LTg3MjktNDBjNS1hYTQ2LTgwMzY3MjJhZWUzZCIsImV4cGlyZXMiOiIyMDI1LTA3LTE3VDEyOjQ3OjU1LjM1NiIsInNlc3Npb25JZCI6IjE2YzVkZWU4LTY1YzctNDJlMi1iNjg1LThiZDkwM2ZhMjc1OCJ9.QD72uFb-C5Mygd_Wai_25lbi9lzuLTBNToP0Y1rHXJrva_o5S8wPCinI-wUyIiYijGDeHz1triT9c9rEXUkUV8EYP0OUJg5ady4QYz2eBFLlystfRHgt4gXn37mqKHWmcrhr8qyWcjMWTHtb1FXp0Fjn0wv1amuAZvbFZn9J8ab-g0Yp366bZb3CHYDo5SqMod3BwPHnC6pHmJyFBHoDrkHiHWKJszc9v0ps1Y64bDoiZzhBfQiUefNnjpK9vrvTvamS7PCqgYx9JZ_FX2XbS4u2x3E7UGIjIM5w_jGuPPFiQTypWdTW2o7U-se99e1BAbhCBEJ-uXJTHpdqL_d-fQ',
  'X-Callback-Url': 'https://165.232.40.247/ussd/callback_handler/',
  'X-Reference-Id': str(uuid.uuid4()),
  'X-Target-Environment': 'mtncongo',
  'Ocp-Apim-Subscription-Key': 'ac9063d40c5a488886f9b63dcfe72298',
  'Content-Type': 'application/json',
  'Cache-Control': 'no-cache'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
print("HELLO")