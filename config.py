import os
from pathlib import Path

def get_env_variable(key: str, default: str = "") -> str:
    # 1. Direct environment variable
    val = os.environ.get(key)
    if val:
        return val

    # 2. Parse local .env file manually if python-dotenv is not installed
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key:
                        return v.strip().strip('"').strip("'")

    # 3. Streamlit secrets
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    return default

GROQ_API_KEY = get_env_variable("GROQ_API_KEY")
