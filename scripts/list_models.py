from groq import Groq

from regulaai.config import settings

client = Groq(api_key=settings.groq_api_key)
for m in sorted(client.models.list().data, key=lambda m: m.id):
    print(m.id)