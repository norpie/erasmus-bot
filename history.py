class History:
    def __init__(self):
        self.history = []

    def filter_history(self):
        filtered = [
            message
            for message in self.history
            if message["role"] == "assistant" or message["role"] == "user"
        ]
        return filtered

    def raw_history(self):
        return self.history

    def add_system_prompt(self):
        self.history.insert(
            0,
            {
                "role": "system",
                "content": "As an AI assistant of Erasmushogeschool Brussel, you can only answer questions related to the school.",
            },
        )

    def add_system_message(self, message):
        self.history.append(
            {
                "role": "system",
                "content": message,
            }
        )

    def add_user_message(self, message):
        self.history.append(
            {
                "role": "user",
                "content": message,
            }
        )

    def add_assistant_message(self, message):
        self.history.append(
            {
                "role": "assistant",
                "content": message,
            }
        )
