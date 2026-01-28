from pathlib import Path
import requests
import json
import os

BASEDIR = Path(__file__).parent
broker = "http://localhost:1026"
objects = BASEDIR.joinpath("items.json")

url = broker + "/ngsi-ld/v1/entities/"

headers = {
  'Content-Type': 'application/ld+json'
}

with open(objects, 'r') as file:
    objects = json.load(file)

print("NGSI-LD Post at " + broker)
for payload in objects["items"]:
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    print(response.text)