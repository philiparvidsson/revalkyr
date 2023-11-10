import openai
import time

from textwrap import dedent


class ThreadMsg:
    def __init__(self, created_at, role, content):
        self.created_at = int(created_at)
        self.role = role
        self.content = content

    def __repr__(self):
        return f"{self.role}: '{self.content}'"


class Thread:
    def __init__(self, assistant_id):
        self.assistant_id = assistant_id
        self.thread_id = openai.beta.threads.create().id
        self.run_id = None

    def add_message(self, content: str):
        openai.beta.threads.messages.create(
            thread_id=self.thread_id, role="user", content=dedent(content)
        )

    def add_source_code(self, source_code: str, language: str = "rescript"):
        source_code = f"```{language}\n{dedent(source_code.strip())}\n```"
        self.add_message(source_code)

    def run(self, instructions: str = None):
        if self.run_id is not None:
            raise RuntimeError("Can only run thread_once")

        run = openai.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            instructions=instructions,
        )

        self.run_id = run.id

    def is_ready(self):
        if self.run_id is None:
            return False

        run = openai.beta.threads.runs.retrieve(
            thread_id=self.thread_id, run_id=self.run_id
        )
        return run.status == "completed"

    def get_last_message(self):
        messages = self.get_messages()
        return messages[-1]

    def get_messages(self):
        if self.run_id is None:
            self.run()

        self.wait_until_ready()

        messages = openai.beta.threads.messages.list(thread_id=self.thread_id)

        m = []

        for message in messages:
            created_at = message.created_at
            role = message.role
            content = message.content[0].text.value
            m.append(ThreadMsg(created_at, role, content))

        return sorted(m, key=lambda msg: msg.created_at)

    def wait_until_ready(self):
        if self.run_id is None:
            raise RuntimeError("You must run the thread_first")

        while not self.is_ready():
            time.sleep(1)


class OpenAI:
    def __init__(self):
        pass

    def create_assistant_thread(self) -> Thread:
        return Thread("asst_3MpzZ2qz0xPimu4UvjyGVD8P")

    def get_chat_completion(
        self, system: str, user: str, model: str = "gpt-4-1106-preview"
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        attempts = 3
        while attempts > 0:
            attempts -= 1

            try:
                response = openai.ChatCompletion.create(model=model, messages=messages)
                return response.choices[0].message.content
            except openai.error.OpenAIError:
                if attempts == 0:
                    raise
