import json
import re

stop_words = [
    "<|im_end|>",
    "[End]",
    "[end]",
    "\nReferences:\n",
    "\nSources:\n",
    "End.",
]

handler_max_concurrency=16 

def extract_all_json(mixed_text):

    mixed_text=mixed_text.replace("'","")
    mixed_text=re.sub(r"(?<=[a-zA-Z])'(?=s\s)", r"\\\'", mixed_text).replace("\n", "")
    mixed_text=mixed_text.replace("```json", "")
    mixed_text=mixed_text.replace("```", "")
    
    # Regular expression pattern to match the JSON structure
    json_pattern = re.compile(r'({.*})')

    # Search for the JSON structure within the mixed text
    match = json_pattern.search(mixed_text)
    if match:
        json_str = match.group(1)  # Extract the matched JSON string
        try:
            # Parse the JSON string
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
    else:
        print("No JSON structure found in the provided text.")
        return None