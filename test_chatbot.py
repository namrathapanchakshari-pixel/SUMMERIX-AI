from chatbot_ai import ask_chatbot


messages = [
    {
        "role": "user",
        "content": "Hello! Introduce yourself in two sentences."
    }
]


print("Testing SUMMARIX AI chatbot...")


response = ask_chatbot(messages)


print("\n" + "=" * 60)

print("SUCCESS!")

print("=" * 60)

print(response)