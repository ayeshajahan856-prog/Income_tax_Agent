# Project Evaluation Report: Bangladesh Income Tax AI Assistant

> **Course:** CSE 3202 - Artificial Intelligence Sessional  
> **Department:** Department of Computer Science and Engineering  
> **Institution:** Bangladesh Army University of Science and Technology (BAUST)  
> **Course Instructors:**  
> - Md. Zahim Hassan (Lecturer, Dept. of CSE, BAUST)  
> - Md. Minhajul Islam (Lecturer, Dept. of CSE, BAUST)  
> 
> **Submitted By:**  
> - Mst. Jugnu Khatun (Student ID: 0802410105101072)  
> - Most. Arifa Akter Allo (Student ID: 0802410105101073)  
> **Date of Evaluation:** October 19, 2026  
> **Evaluation Engine:** `run_eval.py` (Automated Empirical Benchmark Suite)  
> **Underlying LLM:** `openai/gpt-oss-120b` (via Groq Inference Engine)

---

## 1. Executive Summary

This project presents a **Goal-Based, Law-Grounded Income Tax Assistant for Bangladesh**, engineered specifically to overcome the severe mathematical calculation errors, legal hallucinations, and premature assumptions prevalent in general-purpose Large Language Models (LLMs).

Standard conversational LLMs frequently produce fictitious section numbers and commit compounding arithmetic errors when calculating graduated tax slabs. To eliminate these critical flaws, our proposed system integrates:
1. **Clarification-First Guard:** Detects underspecified queries (e.g., gift sender unspecified or return filing criteria unclarified) and solicits required parameters before computation.
2. **Deterministic Computational Tools:** Mathematical calculations are offloaded entirely to statutory Python functions (`salary_tax`, `rental_tax`, `gift_check`, `combined_tax`) adhering to Bangladesh Income Tax Act 2023.
3. **Lexical Law Retrieval:** Contextually retrieves statutory sections (Sections 32, 36–38, 45–49, 66(ঘ), 166, and Sixth Schedule Part 1) to ground conversational explanations.

---

## 2. PEAS Specification and Codebase Mapping

The system follows the classical **PEAS (Performance measure, Environment, Actuators, Sensors)** framework of Artificial Intelligence:

### 2.1 PEAS Formalization Table

| PEAS Dimension | Formal AI Definition | Concrete Implementation in Codebase |
| :--- | :--- | :--- |
| **Performance Measure (P)** | • **Math Accuracy (%):** Strict equality within ±1 BDT of statutory tax.<br>• **Section Citation Accuracy (%):** Presence of authentic Income Tax Act 2023 sections.<br>• **Clarification-First Rate (%):** Prompting user before guessing on ambiguous queries.<br>• **Hallucination Rate (%):** Frequency of citing non-existent/invented section numbers. | Implemented in `run_eval.py`: dynamically parses outputs, compares against hand-computed ground truth (`evaluation.py`), and calculates percentages in `results.json`. |
| **Environment (E)** | • Dynamic Bangladesh tax environment (Income Tax Act 2023, Finance Acts AY 2025-26 & FY 2026-27).<br>• User session state, chat history, and taxpayer category constraints. | • Parameter store: `rules.json`.<br>• Interactive web interface: `app.py` (Streamlit multi-session UI).<br>• Statute repository: `knowledge_base.py`. |
| **Actuators (A)** | Mechanism by which the agent alters the state of the environment: structured Bengali advice, breakdown expanders, and tool invocation. | • Functions: `salary_tax()`, `rental_tax()`, `gift_check()`, `combined_tax()` in `calculator.py`.<br>• Response formatter: Markdown UI templates with Short Answer, Legal Basis, and Math Calculation Table in `tax_agent.py`. |
| **Sensors (S)** | Inputs through which the agent perceives its environment: user queries, taxpayer category, and multi-turn state. | • Lexical Parser: `tokenize_words()`, `normalize_bangla_sender_word()` in `calculator.py`.<br>• Slot extractor: `check_ambiguity_need()` in `tax_agent.py`.<br>• Category selector: regular male, female/senior (65+), disabled, freedom fighters in `app.py`. |

### 2.2 PEAS-to-Code Traceability Matrix

```
User Query (Sensors: app.py, tokenize_words)
      │
      ▼
Ambiguity & Slot Detector (tax_agent.py: check_ambiguity_need)
      ├── [If Ambiguous] ──► Solicit Clarification (Actuators: Structured Prompt)
      │
      └── [If Complete] ──► Retrieve Legal Documents (knowledge_base.py: retrieve_relevant_laws)
                                    │
                                    ▼
                            Deterministic Tools (calculator.py: salary_tax, rental_tax, etc.)
                                    │
                                    ▼
                            Grounding & Guard (tax_agent.py: respond)
                                    │
                                    ▼
                            Performance Evaluator (run_eval.py ──► results.json)
```

---

## 3. Architecture Alignment & Engineering Transparency

### 3.1 Proposal vs. Implementation Architecture

In the initial academic proposal, a high-dimensional vector database (**Qdrant**) combined with dense embeddings was proposed. During prototyping and empirical verification, the following technical architectural decisions were finalized:

1. **Retrieval Mechanism (Keyword-based Lexical Matcher):**
   - *Status:* **Active in Prototype (`knowledge_base.py`).**
   - *Rationale:* Bangladesh tax inquiries heavily hinge on specific statutory tokens (e.g., "বেতন", "ভাড়া", "উপহার", "বাবা", "ফ্রিল্যান্সিং", "ধারা ১৬৬"). Dense vector embeddings frequently exhibited semantic drift across tax sub-heads. Fast, exact lexical token matching ensured 0 ms latency, deterministic retrieval of the exact clauses, and zero out-of-context retrieval failures.
   - *Vector DB (Qdrant) Status:* **Planned for future enterprise scaling.** It remains designed for ingestion of multi-thousand-page circulars, but is not active in the local prototype.

2. **Deterministic Calculation vs. LLM Arithmetic:**
   - LLMs are probabilistic autoregressive models; they cannot guarantee arithmetic correctness over progressive slab calculations.
   - All arithmetic was strictly delegated to pure Python algorithms (`calculator.py`) implementing the rules in `rules.json` (rates and the simplified gift rules are not fully checked against the gazette).

---

## 4. Empirical Evaluation Results

An empirical evaluation was executed using `run_eval.py` using `openai/gpt-oss-120b` across three benchmarked architectures:
1. **Version A (Vanilla LLM):** Zero tools, zero RAG, direct completion.
2. **Version B (LLM + Basic RAG):** Legal documents inserted in prompt, zero tools, zero clarification guard.
3. **Version C (Proposed Tax Agent):** Multi-tool calling loop, lexical RAG, slot memory, and Clarification-First Guard.

### 4.1 Results (auto-generated from `results.json`)

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

## 5. Error & Failure Analysis

All numbers below come from `results.json` / `eval_checkpoint.json` (one run, 40 cases, `openai/gpt-oss-120b`, 0 API errors).

### 5.1 Why Vanilla LLM and Basic RAG scored low
1. **Vanilla LLM (13/36 math):** computes slabs by itself and gets most of them wrong; it never cited the project's sections (0/40) and cited sections outside the knowledge base in 27/40 replies (for example "ধারা ৫(২)"). It asked no clarifying question in the 3 ambiguous cases (0/3).
2. **LLM + Basic RAG (17/36 math):** cites the right sections (35/40) but only 2 retrieved snippets are put in the prompt, and the tax-slab snippet is usually not one of them. In 11 of the 18 cases with non-zero expected tax it answered `FINAL_TAX: 0` after saying the slabs were not available. So its low math score reflects this simple retrieval setup, not only LLM arithmetic. It asked no clarifying question (0/3).

### 5.2 Where the Proposed Agent failed (4 cases)
| Case | What happened | Likely cause |
| :--- | :--- | :--- |
| TOP-01, TOP-02 | "taxable income 40 lakh / 50 lakh, tax?" - the agent asked the user for the slabs and called no tool. | The tools expect salary / rent / gift / business income; there is no tool that applies the slabs directly to a given taxable income. |
| CAT-01 | Disabled person with 4.5 lakh shop income - the agent asked for clarification instead of calculating (expected tax 0). | Clarification guard fired although the income head was given; business income was not recognised from "দোকান আয়". |
| ZERO-02 | No income but owns a private car - the agent said no return is needed, cited sections 32 and 45-49 instead of 166. | The return-filing snippet (car ownership rule) was not retrieved, and the guard did not ask a question. |

These were left unfixed on purpose: changing the code after seeing the test results would make the benchmark meaningless. They are listed as limitations and future work.

### 5.3 Other observations
- Agent math 33/36 (91.7%), sections 38/40, clarification 3/3, hallucinated sections 0/40.
- In all 18 non-zero-tax answers the reply text showed the figure computed by the Python tool (18/18).
- Hallucination here means "section number not in this project's knowledge base"; it does not prove the section is wrong in the real Act.

---

## 6. System Limitations and Future Work

1. **Evaluation Sample Size:** The current benchmark comprises 40 curated ground-truth scenarios, written by the authors; the gift rules (relatives / cash) are a simplified model, not statutory text. Future work should scale this to 500+ diverse taxpayer filings.
2. **Statutory Rules Verification:** Slotted rules currently reflect Assessment Year 2025-26 with FY 2026-27 proposed budget thresholds (৳3,75,000 exemption limit). Awaiting the finalized gazetted Finance Act notification from NBR for full legal codification.
3. **Retrieval Architecture:** The lexical retrieval engine operates as a simple keyword matcher (it can miss paraphrased questions); transitioning to hybrid sparse-dense retrieval (BM25 + Qdrant) will be required when scaling to multi-volume tax case law.

---

## 7. Conclusion

The results table above is the evidence for the design. It is a small, single-run benchmark (40 hand-written cases), so conclusions are limited. The agent moves the arithmetic out of the LLM into Python and asks a clarifying question when key facts are missing; the table shows how much that helped.
