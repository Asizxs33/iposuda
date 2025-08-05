import json
with open("credentials.json", "r") as file:
    data = json.load(file)
    print(json.dumps(data))
