from regulaai.llm.client import LLMClient

print(LLMClient().complete("You are concise.", "Say hello in five words."))