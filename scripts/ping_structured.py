from regulaai.llm.client import LLMClient
from regulaai.models.regulatory import Obligation

text = "3.2 Banks shall conduct a vulnerability assessment at least once every six months."

result = LLMClient().complete_structured(
    system="Extract the single obligation from the text. Use id 'OBL-001'.",
    user=text,
    schema=Obligation,
)
print(result)