import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["sk-AJy-g5xdTiBPGoM7pIq3bA"])

print("=== MY AI ===")

while True:
    message = input("Bạn: ")

    if message.lower() == "exit":
        break

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=message
    )

    print("AI:", response.output_text)
