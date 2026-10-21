"""
Automated Empirical Evaluation Suite
====================================
Benchmarks 3 architectures on the hand-written ground-truth dataset (evaluation.py):

  A. Vanilla LLM        - Groq completion only (no tools, no RAG)
  B. LLM + Basic RAG    - law snippet in the prompt (no tools, no clarification logic)
  C. Proposed Tax Agent - RAG + deterministic Python tools + clarification-first guard

All three use the SAME model (MODEL below). No number is hard-coded or estimated.

Robustness (a rate limit must never be scored as a wrong answer):
  * API errors / empty replies are marked "api_error" and EXCLUDED from every denominator.
  * Progress is saved after every single call to eval_checkpoint.json. Re-running resumes
    and only redoes the missing / api_error pieces.
  * 429 waits are parsed from the error text ("try again in 5m12.3s") and honoured.
  * If the required wait is longer than MAX_WAIT_SECONDS (e.g. daily token limit) the run
    stops cleanly. Run it again later; it continues where it stopped.

Usage:
    python run_eval.py                 # run / resume
    python run_eval.py --fresh         # delete the checkpoint and start over
    python run_eval.py --rebuild       # rebuild results.json from the checkpoint (no API calls)
    python run_eval.py --wait          # on a daily limit, sleep until it resets and continue (laptop must stay on)
    python run_eval.py --max-cases 5   # quick smoke test (does not touch README / REPORT)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Windows terminals: make Bangla output safe
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import GROQ_API_KEY
from groq import Groq
from tax_agent import BangladeshTaxAgent
from knowledge_base import retrieve_relevant_laws
from evaluation import TEST_DATASET

MODEL = "openai/gpt-oss-120b"      # same model for all three systems
PACE_SECONDS = 3.0                 # pause after every API-calling step
MAX_ATTEMPTS = 5                   # attempts per call before giving up (-> api_error)
MAX_WAIT_SECONDS = 600.0           # longer waits (e.g. daily limit) stop the run cleanly

BASE_DIR = Path(__file__).parent
RESULTS_FILE = BASE_DIR / "results.json"
CHECKPOINT_FILE = BASE_DIR / "eval_checkpoint.json"

SYSTEM_KEYS = ["vanilla", "rag", "agent"]
SYSTEM_NAMES = {
    "vanilla": "Vanilla LLM",
    "rag": "LLM + Basic RAG",
    "agent": "Proposed Tax Agent (RAG + Tools + Guard)",
}
DETAIL_KEYS = {"vanilla": "vanilla_eval", "rag": "rag_eval", "agent": "proposed_eval"}

# Words that mean "no tax" when a reply gives no numeric tax. Same list for all 3 systems.
EXEMPT_WORDS = ["করমুক্ত", "tax free", "tax-free", "no tax", "0 taka", "শূন্য", "কর দিতে হবে না", "০ টাকা"]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
BENGALI_DIGITS = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}


def bengali_to_english_digits(text: str) -> str:
    return "".join(BENGALI_DIGITS.get(char, char) for char in text)


# Sections that appear in this project's knowledge_base.py (verified headings: 32 employment, 36-38 rent,
# 45 business, 66 other sources incl. gifts, 166 return). Anything else counts as 'not in KB'.
VALID_KB_SECTIONS = {
    "32", "33", "36", "37", "38", "36-38", "36-37", "37-38",
    "45", "46", "49", "45-49",
    "66", "166", "sixth schedule", "finance act"
}


def extract_cited_sections(text: str, references: list = None) -> list:
    """Extracts section numbers cited in text or references, with Bengali digit normalization."""
    cited = set()
    raw_combined = (text or "") + " " + " ".join(references or [])
    combined_text = bengali_to_english_digits(raw_combined)

    # 1. Ranges like 'Section 36-38' or 'ধারা ৪৫-৪৯'
    for rm in re.findall(r'(?:section|sec\.?|ধারা)\s*[:.]?\s*(\d+\s*[-‑–]\s*\d+)(?!\d)', combined_text, re.IGNORECASE):
        rm = re.sub(r'\s+', '', rm).replace('–', '-')
        cited.add(rm.replace("‑", "-"))

    # 2. Single numbers: 'Section 32', 'ধারা ১৬৬'
    for sm in re.findall(r'(?:section|sec|ধারা)\s*[:.]?\s*(\d+)', combined_text, re.IGNORECASE):
        cited.add(sm)

    if re.search(r'sixth schedule|ষষ্ঠ তফসিল', combined_text, re.IGNORECASE):
        cited.add("sixth schedule")
    if re.search(r'finance act|অর্থ আইন', combined_text, re.IGNORECASE):
        cited.add("finance act")

    return list(cited)


VALID_SECTION_NUMBERS = {32, 33, 36, 37, 38, 45, 46, 47, 48, 49, 66, 166}


def _base(sec: str) -> str:
    """'66(ঘ)' -> '66' (drop a trailing sub-clause)."""
    return re.sub(r"\s*\(.*\)\s*$", "", sec.lower().strip().replace("‑", "-"))


def check_hallucination(cited_sections: list) -> bool:
    """True if any cited section is not a section of this project's KB (exact numbers / ranges, no substrings)."""
    for sec in cited_sections or []:
        s = _base(sec)
        if s in VALID_KB_SECTIONS:
            continue
        if s.isdigit() and int(s) in VALID_SECTION_NUMBERS:
            continue
        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                lo, hi = int(parts[0]), int(parts[1])
                if lo <= hi and all(n in VALID_SECTION_NUMBERS for n in range(lo, hi + 1)):
                    continue
        return True
    return False


def section_matches(expected: str, cited: list) -> bool:
    """Exact match, or the expected number lies inside a cited range (e.g. 36 in 36-38)."""
    exp = (expected or "").lower().strip()
    for s in cited:
        s = _base(s)
        if s == exp:
            return True
        if exp.isdigit() and "-" in s:
            parts = s.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                if int(parts[0]) <= int(exp) <= int(parts[1]):
                    return True
    return False


def extract_tax_from_text(text: str):
    """Extracts the final tax figure from a reply (FINAL_TAX: n first, then loose patterns)."""
    normalized = bengali_to_english_digits(text or "")
    m = re.search(r'FINAL_TAX\s*:\s*([\d,]+(?:\.\d+)?)', normalized, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            pass
    patterns = [
        r'(?:ট্যাক্স|কর|tax)\s*(?:হবে|দিতে হবে|আসবে|:)?\s*[:=]?\s*(?:৳|BDT|tk)?\s*([\d,]+(?:\.\d+)?)\s*(?:টাকা|taka)?',
        r'([\d,]+)\s*(?:টাকা|taka)?\s*(?:ট্যাক্স|কর|tax)'
    ]
    for pat in patterns:
        m2 = re.search(pat, normalized, re.IGNORECASE)
        if m2:
            try:
                val = float(m2.group(1).replace(",", ""))
                if val >= 0:
                    return val
            except Exception:
                pass
    return None


CLARIFICATION_PATTERNS = [
    # Sender patterns (exact token or phrase)
    r'কার কাছ', r'কে দিয়ে', r'কার থেকে', r'কে পাঠিয়েছেন', r'\bwho gave\b',
    r'\b(বাবা|পিতা|মাতা|বন্ধু|ভাই|বোন|স্ত্রী|স্বামী|আত্মীয়|অনাত্মীয়)\b',
    # Channel patterns
    r'ব্যাংকিং চ্যানেল', r'ব্যাংক ট্রান্সফার', r'নগদে', r'ক্যাশে', r'চেকের মাধ্যমে', r'\b(banking channel|cheque)\b',
    # TIN / return criteria
    r'\b(টিআইএন|টিন|tin)\b', r'ট্রেড লাইসেন্স', r'মোটর\s*গাড়ি', r'জমি বা বাড়ি',
    # Property type
    r'আবাসিক', r'বাণিজ্যিক', r'\b(residential|commercial)\b'
]


def check_clarification_reply(reply: str) -> bool:
    """Reply must contain question intent ('?' / 'জানান' / 'স্পষ্টীকরণ') AND a specific clarifying topic."""
    if not reply:
        return False
    r_lower = reply.lower()
    if not (("?" in reply) or ("জানান" in reply) or ("স্পষ্টীকরণ" in reply)):
        return False
    return any(re.search(pat, r_lower) for pat in CLARIFICATION_PATTERNS)


# ---------------------------------------------------------------------------
# API error handling / retry
# ---------------------------------------------------------------------------
class WaitTooLong(Exception):
    """The required wait is longer than MAX_WAIT_SECONDS (typically a daily token limit)."""


def is_rate_limit(msg: str) -> bool:
    low = (msg or "").lower()
    return "429" in low or "rate limit" in low or "rate_limit" in low


def parse_retry_seconds(msg: str):
    """Parses Groq style waits: 'try again in 6.78s', '5m12.3s', '1h2m3s', '280ms'. None if absent."""
    m = re.search(r"try again in\s+([0-9hms.]+)", msg or "", re.IGNORECASE)
    if not m:
        return None
    total, found = 0.0, False
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", m.group(1).rstrip(".")):
        found = True
        total += float(num) * {"h": 3600.0, "m": 60.0, "s": 1.0, "ms": 0.001}[unit]
    return total if found else None


def is_api_error(reply) -> bool:
    """Empty reply, or the agent's generic apology / raw provider error text."""
    if reply is None:
        return True
    r = reply.strip()
    if not r:
        return True
    return r.startswith("দুঃখিত, অনুরোধটি প্রক্রিয়াকরণে সমস্যা") or bool(re.search(r"Error code:\s*\d{3}", r[:300]))


def wait_or_stop(wait: float, label: str):
    if wait > MAX_WAIT_SECONDS:
        raise WaitTooLong(f"{label}: provider asks to wait {wait / 60:.1f} min (limit {MAX_WAIT_SECONDS / 60:.0f} min)")
    print(f"\n   rate limit ({label}) - waiting {wait:.0f}s ...", flush=True)
    time.sleep(wait + 1.0)


def llm_call_with_retry(client, messages, label):
    """Plain chat completion with retry. Returns (reply, error_text_or_None)."""
    last_err = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.1)
            reply = resp.choices[0].message.content or ""
            if reply.strip():
                return reply, None
            last_err = "empty reply"
            time.sleep(3.0 + attempt * 3)
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            if is_rate_limit(last_err):
                wait = parse_retry_seconds(last_err)
                if wait is None:
                    wait = 15.0 + attempt * 10
                wait_or_stop(wait, label)
            else:
                time.sleep(3.0 + attempt * 3)
    return "", last_err


# ---------------------------------------------------------------------------
# Scoring of one reply
# ---------------------------------------------------------------------------
def score_text_reply(case, reply, refs, err):
    """Scores a Vanilla / RAG reply."""
    if err or is_api_error(reply):
        return {"status": "api_error", "error": (err or reply or "")[:300], "reply_snippet": (reply or "")[:140]}

    tax = extract_tax_from_text(reply)
    sections = extract_cited_sections(reply, refs)
    expected = case["expected_tax"]

    math_ok = None
    if expected is not None:
        if tax is not None:
            math_ok = abs(tax - expected) <= 1.0
        else:
            math_ok = bool(expected == 0.0 and any(w in reply.lower() for w in EXEMPT_WORDS))

    return {
        "status": "ok",
        "tax": tax,
        "math_ok": math_ok,
        "sec_ok": section_matches(case["expected_section"], sections),
        "clar_ok": bool(case["is_ambiguous"] and check_clarification_reply(reply)),
        "hallucinated": check_hallucination(sections),
        "cited_sections": sections,
        "reply_snippet": reply[:140],
        "reply": reply[:2500],
    }


def _heads(out: dict) -> int:
    b = out.get("breakdown_by_head") or {}
    return sum(1 for k in ("net_salary", "net_rent", "taxable_gift", "business_income", "other_income") if (b.get(k) or 0) > 0)


def pick_agent_tax(tools: list):
    """
    Which tool output represents the agent's final tax figure?
    Prefer the combined_tax result that covers the most income heads; otherwise the last tool
    that returned total_tax; otherwise 0.0 if a gift check said 'not taxable'.
    """
    combined = [t["output"] for t in tools if t.get("tool") == "combined_tax" and "total_tax" in t.get("output", {})]
    if combined:
        best = max(range(len(combined)), key=lambda i: (_heads(combined[i]), i))
        return combined[best]["total_tax"]
    for t in reversed(tools):
        if "total_tax" in t.get("output", {}):
            return t["output"]["total_tax"]
    for t in tools:
        if t.get("output", {}).get("is_taxable") is False:
            return 0.0
    return None


def reply_mentions_amount(reply: str, tax):
    """Does the reply text actually show the tool's tax figure? (None when tax is 0/unknown)"""
    if tax is None or tax <= 0:
        return None
    text = bengali_to_english_digits(reply or "")
    for ch in (",", " ", " ", " "):
        text = text.replace(ch, "")
    cands = {str(int(round(tax))), f"{tax:.2f}"}
    return any(c in text for c in cands)


def score_agent_result(case, res):
    reply = res.get("content") or ""
    tools = res.get("all_tools_data") or []
    tax = pick_agent_tax(tools)
    sections = extract_cited_sections(reply, res.get("references", []))
    expected = case["expected_tax"]

    math_ok = None
    if expected is not None:
        if tax is not None:
            math_ok = abs(tax - expected) <= 1.0
        else:
            math_ok = bool(expected == 0.0 and any(w in reply.lower() for w in EXEMPT_WORDS))
            if math_ok:
                tax = 0.0

    return {
        "status": "ok",
        "tax": tax,
        "math_ok": math_ok,
        "sec_ok": section_matches(case["expected_section"], sections),
        "clar_ok": bool(case["is_ambiguous"] and check_clarification_reply(reply)),
        "hallucinated": check_hallucination(sections),
        "cited_sections": sections,
        "tools": [t.get("tool") for t in tools],
        "reply_consistent": reply_mentions_amount(reply, tax),
        "reply_snippet": reply[:140],
        "reply": reply[:2500],
    }


# ---------------------------------------------------------------------------
# The three systems
# ---------------------------------------------------------------------------
def run_vanilla(client, case):
    system_prompt = (
        f"You are an assistant answering Bangladesh income tax questions for a {case['taxpayer_cat']} taxpayer. "
        "Calculate the exact tax amount if applicable and cite the relevant section of the Bangladesh Income Tax Act 2023. "
        "At the end of your response, write the final payable tax amount strictly in this format: FINAL_TAX: <number>"
    )
    reply, err = llm_call_with_retry(
        client,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": case["query"]}],
        "vanilla",
    )
    return score_text_reply(case, reply, [], err)


def run_rag(client, case):
    retrieved = retrieve_relevant_laws(case["query"], top_k=2)
    kb_context = "\n\n".join(f"Section {', '.join(d['sections'])}: {d['title']}\n{d['snippet']}" for d in retrieved)
    system_prompt = (
        f"You are an assistant answering Bangladesh income tax questions for a {case['taxpayer_cat']} taxpayer using the provided legal documents. "
        "Do NOT invent sections not in the document. "
        "At the end of your response, write the final payable tax amount strictly in this format: FINAL_TAX: <number>\n\n"
        f"--- Tax Documents ---\n{kb_context}"
    )
    refs = [f"{', '.join(d['sections'])}: {d['title']}" for d in retrieved]
    reply, err = llm_call_with_retry(
        client,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": case["query"]}],
        "rag",
    )
    return score_text_reply(case, reply, refs, err)


def run_agent(agent, case):
    """The agent swallows API errors into an apology text, so detect that and retry here."""
    last_msg = ""
    for attempt in range(MAX_ATTEMPTS):
        res = agent.respond([{"role": "user", "content": case["query"]}], taxpayer_category=case["taxpayer_cat"])
        content = res.get("content") or ""
        if not is_api_error(content):
            return score_agent_result(case, res)
        last_msg = content
        if is_rate_limit(content):
            wait = parse_retry_seconds(content)
            if wait is None:
                wait = 15.0 + attempt * 10
            wait_or_stop(wait, "agent")
        else:
            time.sleep(3.0 + attempt * 3)
    return {"status": "api_error", "error": last_msg[:300], "reply_snippet": last_msg[:140]}


# ---------------------------------------------------------------------------
# Checkpoint + results
# ---------------------------------------------------------------------------
def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            ck = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
            if ck.get("model") == MODEL and isinstance(ck.get("cases"), dict):
                return ck
            print("Checkpoint was made with a different model - starting a fresh one.")
        except Exception:
            print("Checkpoint unreadable - starting a fresh one.")
    return {"model": MODEL, "cases": {}}


def save_checkpoint(ck):
    tmp = CHECKPOINT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(ck, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, CHECKPOINT_FILE)



def rescore_record(case, rec):
    """Recompute the derived scores of a stored 'ok' record from what was saved (reply, tax, cited sections),
    so a scoring fix never needs new API calls and old checkpoints always use the current rules."""
    if not rec or rec.get("status") != "ok":
        return rec
    reply = rec.get("reply") or rec.get("reply_snippet") or ""
    cited = rec.get("cited_sections")
    if cited is None:
        cited = extract_cited_sections(reply)
    tax, expected = rec.get("tax"), case["expected_tax"]
    math_ok = None
    if expected is not None:
        if tax is not None:
            math_ok = abs(tax - expected) <= 1.0
        else:
            math_ok = bool(expected == 0.0 and any(w in reply.lower() for w in EXEMPT_WORDS))
    rec["math_ok"] = math_ok
    rec["sec_ok"] = section_matches(case["expected_section"], cited)
    rec["clar_ok"] = bool(case["is_ambiguous"] and check_clarification_reply(reply))
    rec["hallucinated"] = check_hallucination(cited)
    return rec

def build_results(cases, ck, full_dataset: bool):
    total = len(cases)
    ambiguous = sum(1 for c in cases if c["is_ambiguous"])
    math_cases = sum(1 for c in cases if c["expected_tax"] is not None)

    metrics, denominators, summary, api_errors = {}, {}, {}, {}
    consistency = {"checked": 0, "consistent": 0}

    for key in SYSTEM_KEYS:
        m = {"correct_math": 0, "correct_section": 0, "clarification_handled": 0, "hallucinations": 0}
        d = {"math": 0, "section": 0, "clarification": 0, "hallucination": 0}
        errors = 0
        for c in cases:
            rec = rescore_record(c, ck["cases"].get(c["id"], {}).get(key))
            if not rec or rec.get("status") != "ok":
                errors += 1
                continue
            if c["expected_tax"] is not None:
                d["math"] += 1
                m["correct_math"] += bool(rec.get("math_ok"))
            d["section"] += 1
            m["correct_section"] += bool(rec.get("sec_ok"))
            if c["is_ambiguous"]:
                d["clarification"] += 1
                m["clarification_handled"] += bool(rec.get("clar_ok"))
            d["hallucination"] += 1
            m["hallucinations"] += bool(rec.get("hallucinated"))
            if key == "agent" and rec.get("reply_consistent") is not None:
                consistency["checked"] += 1
                consistency["consistent"] += bool(rec["reply_consistent"])

        def pct(n, den):
            return round(n / den * 100, 1) if den else None

        name = SYSTEM_NAMES[key]
        metrics[name] = m
        denominators[name] = d
        api_errors[name] = errors
        summary[name] = {
            "Math Accuracy (%)": pct(m["correct_math"], d["math"]),
            "Section Citation Accuracy (%)": pct(m["correct_section"], d["section"]),
            "Clarification-First Rate (%)": pct(m["clarification_handled"], d["clarification"]),
            "Hallucination Rate (%)": pct(m["hallucinations"], d["hallucination"]),
        }

    details = []
    for c in cases:
        row = {
            "id": c["id"],
            "category": c["category"],
            "query": c["query"],
            "expected_tax": c["expected_tax"],
            "expected_section": c["expected_section"],
            "is_ambiguous": c["is_ambiguous"],
        }
        for key in SYSTEM_KEYS:
            row[DETAIL_KEYS[key]] = rescore_record(c, ck["cases"].get(c["id"], {}).get(key)) or {"status": "not_run"}
        details.append(row)

    complete = full_dataset and all(v == 0 for v in api_errors.values())
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": MODEL,
        "complete": complete,
        "total_test_cases": total,
        "ambiguous_cases_count": ambiguous,
        "deterministic_cases_count": total - ambiguous,
        "math_cases_count": math_cases,
        "api_error_counts": api_errors,
        "denominators": denominators,
        "metrics": metrics,
        "summary_table": summary,
        "agent_reply_consistency": consistency,
        "case_details": details,
    }


def print_summary(results):
    print("\n" + "=" * 70)
    print(f"model: {results['model']} | cases: {results['total_test_cases']} | complete: {results['complete']}")
    for name, s in results["summary_table"].items():
        d = results["denominators"][name]
        m = results["metrics"][name]
        print(f"\n{name}  (api_errors: {results['api_error_counts'][name]})")
        print(f"  math          {m['correct_math']}/{d['math']}   {s['Math Accuracy (%)']}%")
        print(f"  section       {m['correct_section']}/{d['section']}   {s['Section Citation Accuracy (%)']}%")
        print(f"  clarification {m['clarification_handled']}/{d['clarification']}   {s['Clarification-First Rate (%)']}%")
        print(f"  hallucination {m['hallucinations']}/{d['hallucination']}   {s['Hallucination Rate (%)']}%")
    print("=" * 70)


def main():
    ap = argparse.ArgumentParser(description="Evaluate Vanilla LLM vs LLM+RAG vs Proposed Tax Agent.")
    ap.add_argument("--fresh", action="store_true", help="delete the checkpoint and start over")
    ap.add_argument("--rebuild", action="store_true", help="rebuild results.json from the checkpoint, no API calls")
    ap.add_argument("--max-cases", type=int, default=None, help="only the first N cases (smoke test)")
    ap.add_argument("--pace", type=float, default=PACE_SECONDS, help="seconds to pause between API steps")
    ap.add_argument("--wait", action="store_true", help="on a daily limit, keep waiting (up to 8h per wait) instead of stopping; leave the laptop on")
    args = ap.parse_args()
    if args.wait:
        global MAX_WAIT_SECONDS
        MAX_WAIT_SECONDS = 8 * 3600.0

    cases = TEST_DATASET[: args.max_cases] if args.max_cases else TEST_DATASET
    full_dataset = args.max_cases is None

    if args.fresh and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
    ck = load_checkpoint()

    if not args.rebuild:
        if not GROQ_API_KEY or GROQ_API_KEY.startswith("your_"):
            print("Error: put your Groq key in .env  (GROQ_API_KEY=...)  and run again.")
            sys.exit(1)

        client = Groq(api_key=GROQ_API_KEY)
        agent = BangladeshTaxAgent(api_key=GROQ_API_KEY, model=MODEL)
        runners = {
            "vanilla": lambda c: run_vanilla(client, c),
            "rag": lambda c: run_rag(client, c),
            "agent": lambda c: run_agent(agent, c),
        }

        todo = sum(
            1 for c in cases for k in SYSTEM_KEYS
            if (ck["cases"].get(c["id"], {}).get(k) or {}).get("status") != "ok"
        )
        print(f"{len(cases)} cases x 3 systems | model {MODEL} | still to do: {todo} steps (checkpoint: {CHECKPOINT_FILE.name})")

        try:
            for idx, case in enumerate(cases):
                for key in SYSTEM_KEYS:
                    rec = ck["cases"].get(case["id"], {}).get(key)
                    if rec and rec.get("status") == "ok":
                        continue
                    print(f"[{idx + 1}/{len(cases)}] {case['id']:9} {key:8} ", end="", flush=True)
                    rec = runners[key](case)
                    ck["cases"].setdefault(case["id"], {})[key] = rec
                    save_checkpoint(ck)
                    print(rec["status"], flush=True)
                    time.sleep(args.pace)
        except WaitTooLong as e:
            save_checkpoint(ck)
            print(f"\nSTOPPED: {e}")
            print("Progress is saved. Run `python run_eval.py` again later (e.g. after the daily limit resets).")
        except KeyboardInterrupt:
            save_checkpoint(ck)
            print("\nInterrupted. Progress is saved; run again to continue.")

    results = build_results(cases, ck, full_dataset)
    RESULTS_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print_summary(results)
    print(f"Saved {RESULTS_FILE.name}")

    if results["complete"]:
        try:
            import make_report
            make_report.generate()
            print("README results block and REPORT.md updated from results.json")
        except Exception as e:  # noqa: BLE001
            print(f"(report generation skipped: {e})")
        sys.exit(0)

    if not full_dataset:
        print("Smoke test only - README / REPORT not touched.")
    else:
        left = sum(results["api_error_counts"].values())
        print(f"NOT COMPLETE: {left} step(s) missing or api_error. Run `python run_eval.py` again.")
    sys.exit(2)


if __name__ == "__main__":
    main()
