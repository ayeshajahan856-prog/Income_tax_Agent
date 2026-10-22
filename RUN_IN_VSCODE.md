# Run in VS Code (quick guide)

1. Install Python 3.10+ and the VS Code Python extension.
2. Extract this folder and open it in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:
   - Windows PowerShell: `py -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
   - Windows CMD: `py -m venv .venv` then `.venv\Scripts\activate.bat`
5. Install dependencies: `python -m pip install -r requirements.txt`
6. Copy `.env.example` to `.env`; put your own Groq API key after `GROQ_API_KEY=`.
7. Start the UI: `python -m streamlit run app.py`
8. Open `http://localhost:8501` if the browser does not open automatically.
9. Stop with `Ctrl+C`.

CLI alternative: `python main.py`

Evaluation (uses API quota): `python run_eval.py`

**Security:** Do not upload/share `.env`. The project is an educational prototype, not official tax advice.
**Legal-data caveat:** The README identifies tax rates and simplified gift rules as not fully verified against the official gazette. Validate the legal rules before relying on any calculated tax.
