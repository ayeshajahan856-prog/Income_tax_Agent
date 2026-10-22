# 🇧🇩 Bangladesh Income Tax AI Agent (বাংলাদেশ আয়কর এআই সহকারী)

> **Course:** CSE 3202 - Artificial Intelligence Sessional  
> **Department:** Department of Computer Science and Engineering  
> **Institution:** Bangladesh Army University of Science and Technology (BAUST)  
> **Course Instructors:**  
> - Md. Zahim Hassan (Lecturer, Dept. of CSE, BAUST)  
> - Md. Minhajul Islam (Lecturer, Dept. of CSE, BAUST)  
> 
> **Project Team Members:**  
> - Mst. Jugnu Khatun (Student ID: 0802410105101072)  
> - Most. Arifa Akter Allo (Student ID: 0802410105101073)  
> 
> **Legal sources used:** Income Tax Act 2023 (section headings checked on bdtaxhelp.com / incometaxlawbd.com), PwC Bangladesh tax summary, Finance Act / budget news for AY 2025-26 and FY 2026-27. Tax rates and the project's simplified gift rules are **not** checked against the gazette.

---

## 🏛️ 1. Legal Basis Table (আইন ও ধারা সারণী)

ধারার শিরোনাম (section heading) অনলাইন আইনের পাঠ (bdtaxhelp.com, incometaxlawbd.com) থেকে মিলিয়ে দেখা হয়েছে। হার, সীমা ও আত্মীয়/নগদ উপহারের নিয়ম প্রজেক্টের সরলীকৃত মডেল; অফিশিয়াল গেজেটের সাথে পুরোপুরি যাচাই করা হয়নি।

| আয়ের খাত / বিষয় | বাংলাদেশ আয়কর আইন ২০২৩ এর সংশ্লিষ্ট ধারা | সংবিধিবদ্ধ কর নিয়ম ও অব্যাহতি (Statutory Rules) |
| :--- | :--- | :--- |
| **চাকরি বা বেতন হতে আয়** | **ধারা ৩২ + ষষ্ঠ তফসিল অংশ ১ ক্লজ ২৭** | মোট বেতনের ১/৩ অংশ অথবা ৪,৫০,০০০ টাকার মধ্যে যেটি কম, তা করমুক্ত। অবশিষ্ট অংশ করযোগ্য। |
| **গৃহ-সম্পত্তি হতে ভাড়া আয়** | **ধারা ৩৬, ৩৭ ও ৩৮** | সংবিধিবদ্ধ মেরামত খরচ: আবাসিক ভাড়ার ২৫% এবং বাণিজ্যিক ভাড়ার ৩০% স্বয়ংক্রিয় ছাড়। |
| **উপহার বা দান কর** | **ধারা ৬৬(ঘ) (উপহার = অন্যান্য উৎস থেকে আয়)** — আত্মীয়/নগদ নিয়ম সরলীকৃত মডেল | পিতা, মাতা, স্বামী, স্ত্রী, সন্তান, ভাই-বোনের উপহার ব্যাংকিং চ্যানেলে ১০০% করমুক্ত। বন্ধু বা অন্যদের থেকে উপহার করযোগ্য। |
| **ব্যবসা বা পেশা হতে আয়** | **ধারা ৪৫ হতে ধারা ৪৯** | মোট বিক্রয়/টার্নওভার থেকে সংগত ব্যবসায়িক ব্যয় বাদ দিয়ে নীট মুনাফা করযোগ্য আয়। |
| **রিটার্ন দাখিলের বাধ্যবাধকতা** | **ধারা ১৬৬ (Section 166)** | আয় শূন্য হলেও ধারা ১৬৬(২) মতে মোটরগাড়ি, ফ্ল্যাট, ট্রেড লাইসেন্স বা পূর্ববর্তী কর নির্ধারণ থাকলে রিটার্ন দাখিল বাধ্যতামূলক। |
| **আইটি ফ্রিল্যান্সিং সেবা** | **ষষ্ঠ তফসিল অংশ ১ ক্লজ ২১ (১ জুলাই ২০২৪–৩০ জুন ২০২৭)** | সরকার অনুমোদিত আইটি সেবা থেকে বৈধ ব্যাংকিং রেমিট্যান্স চ্যানেলে বৈদেশিক মুদ্রা অর্জিত হলে কর অব্যাহতি। |

---

## 🏗️ 2. Architecture & Implementation Alignment (Qdrant & Hybrid RAG)

প্রজেক্ট প্রপোজালে Qdrant ভেক্টর ডাটাবেস ব্যবহারের প্রাথমিক ধারণা প্রস্তাব করা হয়েছিল। তবে বর্তমান লোকাল প্রোটোটাইপে সরলতা ও দ্রুত রেসপন্সের জন্য **টোকেনাইজড লেক্সিকাল ম্যাচিং** বাস্তবায়ন করা হয়েছে (Qdrant ভেক্টর লেয়ারটি ভবিষ্যৎ স্কেলিংয়ের জন্য পরিকল্পিত, বর্তমান প্রোটোটাইপে সক্রিয় নয়):

```
                      [User Query: Bangla / English / Banglish]
                                          │
                                          ▼
                         [Tokenized Intent & Slot Extractor]
                                          │
                       ┌──────────────────┴──────────────────┐
                       ▼                                     ▼
           [Lexical Retrieval Engine]             [Deterministic Python Tools]
           (Legal clauses, simplified)              (Statutory Slabs & Minimum Tax)
                       │                                     │
                       └──────────────────┬──────────────────┘
                                          ▼
                       [Goal-Based Reasoning & Verification Guard]
                                          │
                                          ▼
                 [Strict Template Output: Short Answer ➔ Legal Basis ➔ Math Table]
```

- **Retrieval Engine (`HybridTaxRetriever`):** সুনির্দিষ্ট ধারার সঠিক রেফারেন্সিংয়ের জন্য প্রোটোটাইপে দ্রুত টোকেনাইজড ম্যাচিং কার্যকর রয়েছে। Qdrant ভেক্টর ডাটাবেস লেয়ারটি নকশায় অন্তর্ভুক্ত থাকলেও বর্তমান লোকাল রান-টাইমে সক্রিয় করা হয়নি।
- **Deterministic Python Tools:** এআই-এর নিজস্ব মনগড়া হিসাব রোধ করতে `salary_tax()`, `rental_tax()`, `gift_check()`, `combined_tax()` ফাংশনের মাধ্যমে সংবিধিবদ্ধ স্ল্যাব অনুযায়ী গাণিতিক হিসাব সম্পন্ন করে।

---

## 📋 3. PEAS Specification to Code Mapping

| PEAS Dimension | Real Code Implementation |
| :--- | :--- |
| **Performance Measure (P)** | `run_eval.py`: স্বয়ংক্রিয়ভাবে Math Accuracy, Section Citation Accuracy, এবং Clarification-First Success রেট পরিমাপ করে (`results.json`)। |
| **Environment (E)** | `app.py` (Streamlit UI with ChatGPT-style multi-chat sessions), `rules.json` (Central dynamic tax parameters)। |
| **Actuators (A)** | Structured Bengali Markdown Responses, Legal Snippet Expanders (`st.expander`), Python Tool Execution (`salary_tax`, `rental_tax`, `gift_check`, `combined_tax`)। |
| **Sensors (S)** | User text input tokenization (`tokenize_words`), Taxpayer category selector, Multi-turn Slot Memory (`slots` dictionary)। |

---

## 🧪 4. Real Empirical Evaluation Results (খাঁটি বাস্তব ফলাফল)

<!-- RESULTS:START -->
_Auto-generated from `results.json` (run: 2026-10-21 11:12:07, model: `openai/gpt-oss-120b`, 40 test cases, 3 ambiguous). Do not edit by hand._

| Architecture | API errors | Math (numeric cases) | Section citation | Clarification (ambiguous) | Hallucinated section |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Vanilla LLM | 0 | 13/36 (36.1%) | 0/40 (0.0%) | 0/3 (0.0%) | 27/40 (67.5%) |
| LLM + Basic RAG | 0 | 17/36 (47.2%) | 35/40 (87.5%) | 0/3 (0.0%) | 1/40 (2.5%) |
| Proposed Tax Agent (RAG + Tools + Guard) | 0 | 33/36 (91.7%) | 38/40 (95.0%) | 3/3 (100.0%) | 0/40 (0.0%) |

Agent reply text shows the tool's tax figure in 18/18 non-zero cases.

Notes: API errors / rate-limit failures are excluded from every denominator, never counted as wrong answers. Ground truth is hand-written in `evaluation.py` and depends on the rules in `rules.json`, which have not been checked against the official gazette. Hallucination = a cited section number that is not in this project's knowledge base (it does not prove the section is wrong in the real Act). Small sample (40 cases), single run.
<!-- RESULTS:END -->

---

## 🚀 5. How to Run in VS Code (Windows)

### Step 1 — Install the tools
1. Install **Python 3.10 or newer** from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Install **Visual Studio Code** from https://code.visualstudio.com/.
3. In VS Code, install the Microsoft **Python** extension.

### Step 2 — Extract and open the project
1. Extract `Income_tax_Agent.zip` to a normal folder (do not run it from inside the ZIP).
2. Open VS Code → **File → Open Folder** → select the extracted `Income_tax_Agent` folder.
3. Open **Terminal → New Terminal**.

### Step 3 — Create and activate a virtual environment
Run these commands in the VS Code terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt as the VS Code terminal and run:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

### Step 4 — Install the packages

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 5 — Configure the API key
1. In the VS Code Explorer, copy `.env.example` and name the copy `.env`.
2. Open `.env` and replace `your_groq_api_key_here` with your own Groq API key from https://console.groq.com.
3. Save the file. **Never share or upload your `.env` file**; it contains a private key.

### Step 6 — Start the web app

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal, usually `http://localhost:8501`. To stop the app, click the terminal and press **Ctrl+C**.

### Optional — Run the command-line version

```bash
python main.py
```

### Optional — Run the evaluation suite
This calls the configured LLM API and may consume API quota. It can take time.

```bash
python run_eval.py
```

To rebuild the report from an existing evaluation checkpoint without API calls:

```bash
python run_eval.py --rebuild
```

### Troubleshooting
- **`python` or `py` not found:** reinstall Python and enable “Add Python to PATH”, then restart VS Code.
- **`ModuleNotFoundError`:** confirm `.venv` is activated and rerun `python -m pip install -r requirements.txt`.
- **API key / authentication error:** check the spelling of `GROQ_API_KEY` in `.env`; do not include extra spaces.
- **Quota / rate-limit error:** check the API provider's usage limits and try again later.
- **Port 8501 is busy:** run `python -m streamlit run app.py --server.port 8502`.

## ⚠️ 6. System Limitations & Academic Disclaimer

- **জ্ঞানভান্ডারের পরিধি:** শুধু বেতন, ভাড়া, উপহার, ব্যবসা, ফ্রিল্যান্সিং, রিটার্ন ও করের স্ল্যাব। অন্য বিষয় (রেয়াত, সঞ্চয়পত্র, গাড়ি, সারচার্জ ইত্যাদি) যাচাই না হওয়ায় `knowledge_base.py`-তে `UNVERIFIED_DOCS`-এ রাখা আছে, উত্তরে ব্যবহার হয় না।
- **শিক্ষামূলক প্রোটোটাইপ:** এটি কোনো সার্টিফাইড আয়কর আইনজীবী বা NBR-এর আনুষ্ঠানিক আইনি সনদের বিকল্প নয়।
- **আওতাভুক্ত খাতসমূহ:** বেতন (ধারা ৩২), গৃহ সম্পত্তি (ধারা ৩৬), উপহার (ধারা ৬৬(ঘ)), ব্যবসা (ধারা ৪৫), আইটি ফ্রিল্যান্সিং (ষষ্ঠ তফসিল অংশ ১) এবং রিটার্ন দাখিল (ধারা ১৬৬)।
- **করবর্ষ:** বর্তমান সক্রিয় করবর্ষ ২০২৫-২০২৬ (AY 2025-26) এবং ২০২৬-২০২৭ এর বাজেট প্রস্তাবনা অন্তর্ভুক্ত।
