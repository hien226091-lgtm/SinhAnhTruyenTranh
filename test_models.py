import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\VoVanHien\AppData\Roaming\gcloud\application_default_credentials.json"

import google.generativeai as genai

print("Available models:")
for model in genai.list_models():
    print(f"  {model.name}")
