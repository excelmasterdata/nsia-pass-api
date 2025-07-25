import requests

url = "https://proxy.momoapi.mtn.com/collection/token/"

payload = {}
headers = {
  'Authorization': 'Basic NTMwODdiMDctODcyOS00MGM1LWFhNDYtODAzNjcyMmFlZTNkOjBiZjI3MzJmMmQwNTQyMDliNDUzZTBjNjIwNDlhMmU4',
  'Ocp-Apim-Subscription-Key': 'ac9063d40c5a488886f9b63dcfe72298',
  'Content-Length': '0'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)