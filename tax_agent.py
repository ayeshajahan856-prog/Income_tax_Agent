"""
Tax Agent Core Engine
Upgraded features:
1. Multi-Tool Loop Execution (Handles multiple simultaneous tool calls like salary + rent + gift)
2. Tokenized Word-Boundary Ambiguity & Slot Extraction (Fixes 'Mahmud', 'bondhu' substring bugs)
3. Strict Output Formatting (Short Answer -> Legal Basis -> Calculation -> Next Step)
4. Anti-hallucination guard & Section 166 enforcement
"""

import json
import re
import time
from groq import Groq
from calculator import (
    salary_tax,
    rental_tax,
    gift_check,
    combined_tax,
    compute_slab_tax,
    get_exemption_limit,
    tokenize_words,
    RULES
)
from knowledge_base import retrieve_relevant_laws

BENGALI_DIGITS = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}

def bengali_to_english_digits(text: str) -> str:
    """Converts Bengali numerals (০-৯) to English numerals (0-9)."""
    return "".join(BENGALI_DIGITS.get(char, char) for char in text)

def parse_monetary_amounts(text: str) -> list:
    """
    Extracts all monetary amounts from query in BDT.
    Handles '২০,০০,০০০', '20 lakh', '5 লাখ', '8.5 lac', '500000' etc.
    """
    normalized = bengali_to_english_digits(text).lower()
    amounts = []

    # 1. Matches like '20 lakh', '5.5 লাখ', '8 lac'
    lakh_matches = re.finditer(r'(\d+(?:\.\d+)?)\s*(?:lakh|লাখ|lac)', normalized)
    for m in lakh_matches:
        try:
            val = float(m.group(1)) * 100000
            amounts.append(val)
        except Exception:
            pass

    # 2. Matches comma-separated or plain large numbers: '2,000,000' or '20,00,000' or '850000'
    # Remove commas between digits
    cleaned = re.sub(r'(?<=\d),(?=\d)', '', normalized)
    num_matches = re.finditer(r'\b(\d{5,9}(?:\.\d+)?)\b', cleaned)
    for m in num_matches:
        try:
            val = float(m.group(1))
            # Don't add if already added by lakh parser
            if not any(abs(val - a) < 1.0 for a in amounts):
                amounts.append(val)
        except Exception:
            pass

    return amounts

def extract_contextual_amounts(text: str) -> dict:
    """
    Associates parsed monetary amounts with specific income heads based on surrounding keywords.
    Prevents blind replacement and accurately distinguishes multiple amounts (salary vs rent vs gift vs business).
    """
    normalized = bengali_to_english_digits(text).lower()
    cleaned = re.sub(r'(?<=\d),(?=\d)', '', normalized)

    amounts_with_pos = []
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:lakh|লাখ|lac)', cleaned):
        try:
            val = float(m.group(1)) * 100000
            amounts_with_pos.append((val, m.start(), m.end()))
        except Exception:
            pass

    for m in re.finditer(r'\b(\d{5,9}(?:\.\d+)?)\b', cleaned):
        try:
            val = float(m.group(1))
            if not any(abs(val - a[0]) < 1.0 for a in amounts_with_pos):
                amounts_with_pos.append((val, m.start(), m.end()))
        except Exception:
            pass

    head_keywords = {
        'net_rent': ['নিট আয়', 'নিট আয়', 'নিট ভাড়া', 'নিট ভাড়া', 'net rent', 'net rental'],
        'rent': ['ভাড়া', 'ভাড়া', 'rent', 'rental', 'বাড়ি', 'বাড়ি', 'house', 'flat', 'ফ্ল্যাট'],
        'salary': ['বেতন', 'salary', 'beton', 'চাকরি', 'job', 'পারিশ্রমিক'],
        'gift': ['উপহার', 'gift', 'upohar', 'দান'],
        'business': ['ব্যবসা', 'business', 'মুনাফা', 'লাভ', 'profit', 'বিক্রয়', 'বিক্রি']
    }

    amounts_with_pos.sort(key=lambda x: x[1])
    context_map = {}

    for val, start, end in amounts_with_pos:
        amt_center = (start + end) / 2
        best_head = None
        min_dist = 9999

        for head, kws in head_keywords.items():
            for kw in kws:
                for match in re.finditer(re.escape(kw), cleaned):
                    kw_center = (match.start() + match.end()) / 2
                    dist = abs(kw_center - amt_center)
                    if dist < 40 and dist < min_dist:
                        min_dist = dist
                        best_head = head

        if best_head:
            context_map[best_head] = val

    return context_map

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "salary_tax",
            "description": "Calculates net taxable salary and tax using Section 32/33 statutory 1/3 exemption.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gross_annual_salary": {"type": "number", "description": "Gross annual salary in BDT."},
                    "category": {"type": "string", "enum": ["regular", "female", "disabled", "freedom_fighter"]}
                },
                "required": ["gross_annual_salary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rental_tax",
            "description": "Calculates house property income deduction under Section 36-38 (25% residential, 30% commercial).",
            "parameters": {
                "type": "object",
                "properties": {
                    "annual_rent": {"type": "number", "description": "Gross annual rental income in BDT."},
                    "is_commercial": {"type": "boolean", "description": "True if commercial, False if residential."},
                    "category": {"type": "string", "enum": ["regular", "female", "disabled", "freedom_fighter"]}
                },
                "required": ["annual_rent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gift_check",
            "description": "Verifies gift taxability under Section 66 (simplified project rule) based on relative relationship and banking channel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Gift amount in BDT."},
                    "sender": {"type": "string", "description": "Who gave the gift (father, mother, friend, colleague, etc.)."},
                    "banking_channel": {"type": "boolean", "description": "True if received via bank/check/pay-order, False if cash."}
                },
                "required": ["amount", "sender"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "combined_tax",
            "description": "Calculates combined income tax from multiple heads (salary, rent, taxable gifts, business, other).",
            "parameters": {
                "type": "object",
                "properties": {
                    "gross_salary": {"type": "number", "default": 0},
                    "annual_rent": {"type": "number", "default": 0},
                    "net_rental_income": {"type": "number", "default": 0, "description": "Net rental income if already deducted."},
                    "is_commercial": {"type": "boolean", "default": False},
                    "taxable_gift": {"type": "number", "default": 0},
                    "business_income": {"type": "number", "default": 0},
                    "other_income": {"type": "number", "default": 0},
                    "category": {"type": "string", "enum": ["regular", "female", "disabled", "freedom_fighter"]}
                }
            }
        }
    }
]


def execute_tool(tool_name: str, args: dict):
    if tool_name == "salary_tax":
        return salary_tax(float(args.get("gross_annual_salary", 0)), args.get("category", "regular"))
    elif tool_name == "rental_tax":
        return rental_tax(float(args.get("annual_rent", 0)), bool(args.get("is_commercial", False)), args.get("category", "regular"))
    elif tool_name == "gift_check":
        return gift_check(float(args.get("amount", 0)), str(args.get("sender", "")), bool(args.get("banking_channel", True)))
    elif tool_name == "combined_tax":
        return combined_tax(
            gross_salary=float(args.get("gross_salary", 0)),
            annual_rent=float(args.get("annual_rent", 0)),
            net_rental_income=float(args.get("net_rental_income", 0)),
            is_commercial=bool(args.get("is_commercial", False)),
            taxable_gift=float(args.get("taxable_gift", 0)),
            business_income=float(args.get("business_income", 0)),
            other_income=float(args.get("other_income", 0)),
            category=args.get("category", "regular")
        )
    return {"error": "Unknown tool"}


class BangladeshTaxAgent:
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def update_slot_memory(self, user_query: str, current_slots: dict) -> dict:
        q = user_query.lower()
        tokens = tokenize_words(q)
        slots = dict(current_slots) if current_slots else {
            "income_type": None,
            "salary_amount": None,
            "rental_amount": None,
            "gift_amount": None,
            "gift_sender": None,
            "gift_channel": None,
            "has_tin_or_assets": None
        }

        # Salary detection
        if tokens.intersection({"salary", "বেতন", "beton", "chakri", "job"}):
            slots["income_type"] = "Salary"
            if any(w in tokens for w in ["লাখ", "lakh", "lac"]):
                for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:lakh|লাখ|lac)', q):
                    slots["salary_amount"] = float(match.group(1)) * 100000
            elif re.search(r'\b\d{5,8}\b', q):
                m = re.search(r'\b(\d{5,8})\b', q)
                slots["salary_amount"] = float(m.group(1))

        # Rent detection
        if tokens.intersection({"rent", "ভাড়া", "bhara", "bari"}):
            slots["income_type"] = "House Property"
            if any(w in tokens for w in ["লাখ", "lakh", "lac"]):
                for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:lakh|লাখ|lac)', q):
                    slots["rental_amount"] = float(match.group(1)) * 100000
            elif re.search(r'\b\d{5,8}\b', q):
                m = re.search(r'\b(\d{5,8})\b', q)
                slots["rental_amount"] = float(m.group(1))

        # Gift detection with exact token matching
        if tokens.intersection({"gift", "উপহার", "দান", "upohar"}):
            slots["income_type"] = "Gift"
            if any(w in tokens for w in ["লাখ", "lakh", "lac"]):
                for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:lakh|লাখ|lac)', q):
                    slots["gift_amount"] = float(match.group(1)) * 100000
            
            # Non-relative explicitly checked
            non_rel_matched = tokens.intersection(set(RULES["gift_rules"]["non_relatives"]))
            if non_rel_matched:
                slots["gift_sender"] = list(non_rel_matched)[0]
            else:
                rel_matched = tokens.intersection(set(RULES["gift_rules"]["exempt_relatives"]))
                if rel_matched:
                    slots["gift_sender"] = list(rel_matched)[0]

            if tokens.intersection({"bank", "ব্যাংক", "cheque", "চেক", "account"}):
                slots["gift_channel"] = "Banking Channel"
            elif tokens.intersection({"cash", "ক্যাশ", "নগদ"}):
                slots["gift_channel"] = "Cash"

        # Zero income / TIN query
        if any(w in q for w in ["ay na thakle", "shunno", "zero income", "আয় না থাকলে", "kono income nai"]):
            slots["income_type"] = "Zero/No Income"

        return slots

    def check_ambiguity_need(self, user_query: str, slots: dict) -> str:
        q = user_query.lower()
        tokens = tokenize_words(q)

        # Case 1: Zero income / "Amr ay na thakle ki kor dite hbe"
        if any(w in q for w in ["ay na thakle", "shunno", "zero income", "আয় না থাকলে", "kono income nai"]):
            if slots.get("has_tin_or_assets") is None and not tokens.intersection({"tin", "car", "bari", "গাড়ি", "বাড়ি", "টিন"}):
                return (
                    "✅ **Short Answer**: If you have zero taxable income, no statutory income tax is payable under standard rules (Tax = BDT 0).\n\n"
                    "➡️ **However, an important clarification is required under Section 166**:\n"
                    "Under Section 166 of the Income Tax Act 2023, even if your income is zero, filing an income-tax return is mandatory if you meet any of these conditions:\n"
                    "1. Do you hold an active **TIN (Taxpayer Identification Number)**?\n"
                    "2. Do you own any land, apartment, or house in City Corporation, Cantonment, or Pourashava areas?\n"
                    "3. Do you own a motor vehicle (car/jeep), or hold a commercial trade license?\n\n"
                    "*(Please answer Yes or No to determine your filing requirement)*"
                )

        # Case 2: Gift mentioned without sender
        if tokens.intersection({"gift", "উপহার", "upohar"}):
            has_sender = bool(slots.get("gift_sender"))
            has_channel = bool(slots.get("gift_channel"))

            if not has_sender:
                return (
                    "✅ **Short Answer**: Whether a gift is taxable depends on the donor's relationship to you and the transaction channel.\n\n"
                    "➡️ **Please clarify the following to compute your tax**:\n"
                    "• **Who gave you the gift?** (e.g. parents, spouse, children, siblings, or a friend / non-relative?)\n"
                    "• **Payment Method:** Was the amount received through banking channels (bank transfer, cheque, pay order) or in cash?"
                )

        return None

    def respond(self, messages_history: list, taxpayer_category: str = "regular", current_slots: dict = None) -> dict:
        latest_query = ""
        for m in reversed(messages_history):
            if m["role"] == "user":
                latest_query = m["content"]
                break

        # Normalize Bengali numerals to English numerals
        normalized_query = bengali_to_english_digits(latest_query)
        parsed_amounts = parse_monetary_amounts(latest_query)

        updated_slots = self.update_slot_memory(normalized_query, current_slots)

        # 1. Ambiguity & Clarification First
        clarification_response = self.check_ambiguity_need(normalized_query, updated_slots)
        if clarification_response:
            retrieved_docs = retrieve_relevant_laws(normalized_query, top_k=1)
            return {
                "content": clarification_response,
                "tool_data": None,
                "references": [f"{', '.join(d['sections'])}: {d['title']}" for d in retrieved_docs],
                "retrieved_snippets": [{"section": d["sections"], "snippet": d["snippet"]} for d in retrieved_docs],
                "updated_slots": updated_slots
            }

        # 2. RAG Retrieval (Concise snippet context to prevent TPM rate limits)
        retrieved_docs = retrieve_relevant_laws(normalized_query, top_k=2)
        law_context = "\n\n".join([
            f"【Statutory Section: {', '.join(d['sections'])} - {d['title']}】\nSnippet: {d['snippet']}"
            for d in retrieved_docs
        ])

        system_instruction = (
            "You are an autonomous, highly accurate AI Tax Agent specialized in the Bangladesh Income Tax Act 2023 (আয়কর আইন ২০২৩).\n"
            f"Active Assessment Year: 2025-2026 (AY 2025-26). Current Taxpayer Category: {taxpayer_category} "
            f"(Statutory Exemption Threshold: ৳ {get_exemption_limit(taxpayer_category):,}).\n\n"
            "🔴 **OUTPUT FORMAT & MANDATORY STRUCTURE (Strictly respond in English using these 4 exact headings)**:\n"
            "✅ **Short Answer**:\n(1-2 clear concise sentences stating the direct conclusion or exact net tax payable amount in BDT)\n\n"
            "📖 **Law & Section**:\n(Cite authentic sections of the Income Tax Act 2023, such as Section 32, 36, 45, 66, or Section 166, with legal justification)\n\n"
            "🧮 **Calculation Details**:\n(Step-by-step breakdown using the deterministic calculator tools. If tax is zero, state 'Tax Payable: BDT 0 (Tax-Free)')\n\n"
            "➡️ **Next Steps / Clarifications**:\n(Provide return filing guidance under Section 166, compliance advice, or request clarification if parameters are missing)\n\n"
            "⚠️ **STRICT OPERATIONAL RULES**:\n"
            "- Always write your response in clear, professional English.\n"
            "- Do not calculate tax arithmetic mentally; ALWAYS invoke the corresponding Python tool (`salary_tax`, `rental_tax`, `gift_check`, or `combined_tax`).\n"
            "- For residential rental property, assume residential (repair deduction 25%, is_commercial=False) unless commercial is explicitly stated.\n"
            "- For multiple income streams (salary + gift, salary + rent, business + salary), invoke `combined_tax`.\n"
            "- Gifts from friends or non-relatives are ALWAYS taxable as other income (`taxable_gift`).\n"
            "- Freelancing / ITES software export earnings received through official banking channels are 100% tax-exempt under Sixth Schedule (Tax = 0 BDT).\n"
            "- Never cite non-existent sections. Return filing obligation is strictly governed by Section 166.\n"
            "- If information is incomplete or ambiguous, ask a clarifying question directly.\n\n"
            f"--- [RAG Retrieved Legal Chunks] ---\n{law_context}\n-------------------------------------"
        )

        full_messages = [{"role": "system", "content": system_instruction}] + messages_history

        # Tool choice mode: required ONLY when BOTH calculation keyword and amount exist, and NOT freelancing/return-filing
        tokens = tokenize_words(normalized_query)
        has_calc_keyword = bool(tokens.intersection({
            "বেতন", "salary", "beton", "chakri", "job", "পারিশ্রমিক",
            "ভাড়া", "ভাড়া", "rent", "bhara", "bari", "বাড়ি", "বাড়ি", "flat", "ফ্ল্যাট",
            "উপহার", "gift", "upohar", "দান",
            "ব্যবসা", "business", "মুনাফা", "লাভ", "বিক্রয়", "বিক্রি"
        }))
        is_freelancing_or_return = bool(tokens.intersection({
            "freelance", "freelancing", "ফ্রিল্যান্সিং", "রেমিট্যান্স", "remittance",
            "tin", "টিআইএন", "টিন", "return", "রিটার্ন", "filing", "আইটি"
        }))
        ctx_amounts = extract_contextual_amounts(normalized_query)

        if len(ctx_amounts) > 1 and not is_freelancing_or_return:
            tool_choice_mode = {"type": "function", "function": {"name": "combined_tax"}}
        elif parsed_amounts and has_calc_keyword and not is_freelancing_or_return:
            tool_choice_mode = "required"
        else:
            tool_choice_mode = "auto"

        try:
            response = None
            for attempt in range(4):
                try:
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=full_messages,
                            tools=TOOLS,
                            tool_choice=tool_choice_mode,
                            temperature=0.1,
                        )
                    except Exception as e:
                        if "429" in str(e) or "rate limit" in str(e).lower():
                            raise e
                        # If provider has issue with 'required', gracefully fallback to 'auto'
                        if "tool_choice" in str(e).lower() or "400" in str(e):
                            response = self.client.chat.completions.create(
                                model=self.model,
                                messages=full_messages,
                                tools=TOOLS,
                                tool_choice="auto",
                                temperature=0.1,
                            )
                        else:
                            raise e
                    break
                except Exception as e:
                    if ("429" in str(e) or "rate limit" in str(e).lower()) and attempt < 3:
                        m_wait = re.search(r'try again in ([\d\.]+)s', str(e), re.IGNORECASE)
                        wait_sec = (float(m_wait.group(1)) + 1.0) if m_wait else (15.0 + attempt * 5)
                        time.sleep(wait_sec)
                        continue
                    raise e

            response_message = response.choices[0].message
            executed_tools_data = []

            # Multi-Tool Calls Loop (Iterate over ALL tool calls)
            if response_message.tool_calls:
                tool_messages = [response_message]
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    # Contextual amount validation for each specific tax head
                    ctx_amounts = extract_contextual_amounts(latest_query)

                    if function_name == "salary_tax":
                        if "salary" in ctx_amounts:
                            arguments["gross_annual_salary"] = ctx_amounts["salary"]
                        elif len(parsed_amounts) == 1:
                            arguments["gross_annual_salary"] = parsed_amounts[0]

                    elif function_name == "rental_tax":
                        if "rent" in ctx_amounts:
                            arguments["annual_rent"] = ctx_amounts["rent"]
                        elif "net_rent" in ctx_amounts:
                            arguments["annual_rent"] = ctx_amounts["net_rent"]
                        elif len(parsed_amounts) == 1:
                            arguments["annual_rent"] = parsed_amounts[0]

                    elif function_name == "gift_check":
                        if "gift" in ctx_amounts:
                            arguments["amount"] = ctx_amounts["gift"]
                        elif len(parsed_amounts) == 1:
                            arguments["amount"] = parsed_amounts[0]
                        sender_toks = tokenize_words(latest_query)
                        if sender_toks.intersection({"friend", "friends", "bondhu", "বন্ধু", "বান্ধবী"}):
                            arguments["sender"] = "friend"

                    elif function_name == "combined_tax":
                        if "salary" in ctx_amounts:
                            arguments["gross_salary"] = ctx_amounts["salary"]
                        if "rent" in ctx_amounts:
                            arguments["annual_rent"] = ctx_amounts["rent"]
                        if "net_rent" in ctx_amounts:
                            arguments["net_rental_income"] = ctx_amounts["net_rent"]
                        if "gift" in ctx_amounts:
                            arguments["taxable_gift"] = ctx_amounts["gift"]
                        if "business" in ctx_amounts:
                            arguments["business_income"] = ctx_amounts["business"]

                        # If user gave amounts but none could be matched to heads, ask clarification (unless freelancing/return query)
                        if parsed_amounts and not ctx_amounts and not is_freelancing_or_return:
                            return {
                                "content": (
                                    "✅ **সংক্ষিপ্ত উত্তর**: আপনার একাধিক খাতের আয়ের হিসাব করতে তথ্যের স্পষ্টীকরণ প্রয়োজন।\n\n"
                                    "➡️ **অনুগ্রহ করে জানান**:\n"
                                    "আপনার বেতন, বাড়ি ভাড়া, ব্যবসা বা অন্যান্য খাত থেকে প্রাপ্ত আয়ের পরিমাণ আলাদাভাবে কত?"
                                ),
                                "tool_data": None,
                                "all_tools_data": [],
                                "references": [f"{', '.join(d['sections'])}: {d['title']}" for d in retrieved_docs],
                                "retrieved_snippets": [{"section": d["sections"], "snippet": d["snippet"]} for d in retrieved_docs],
                                "updated_slots": updated_slots
                            }

                    if "category" not in arguments and function_name in ["salary_tax", "rental_tax", "combined_tax"]:
                        arguments["category"] = taxpayer_category

                    tool_output = execute_tool(function_name, arguments)
                    executed_tools_data.append({
                        "tool": function_name,
                        "arguments": arguments,
                        "output": tool_output
                    })

                    # If gift is taxable, also execute combined_tax on that taxable gift amount
                    if function_name == "gift_check" and tool_output.get("is_taxable"):
                        gift_amt = tool_output.get("taxable_gift_amount", 0)
                        c_tax = combined_tax(taxable_gift=gift_amt, category=taxpayer_category)
                        executed_tools_data.append({
                            "tool": "combined_tax",
                            "arguments": {"taxable_gift": gift_amt, "category": taxpayer_category},
                            "output": c_tax
                        })
                        # Update output to contain total_tax so evaluators and cards see tax immediately
                        tool_output["total_tax"] = c_tax.get("total_tax", 0)
                        tool_output["slabs"] = c_tax.get("slabs", [])

                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(tool_output, ensure_ascii=False)
                    })

                second_response = None
                for attempt2 in range(4):
                    try:
                        second_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=full_messages + tool_messages,
                            tools=TOOLS,
                            tool_choice="none",
                            temperature=0.1,
                        )
                        break
                    except Exception as e2:
                        if ("429" in str(e2) or "rate limit" in str(e2).lower()) and attempt2 < 3:
                            m_wait2 = re.search(r'try again in ([\d\.]+)s', str(e2), re.IGNORECASE)
                            wait_sec2 = (float(m_wait2.group(1)) + 1.0) if m_wait2 else (15.0 + attempt2 * 5)
                            time.sleep(wait_sec2)
                            continue
                        raise e2

                final_content = second_response.choices[0].message.content if second_response else ""
            else:
                final_content = response_message.content

            primary_tool = executed_tools_data[0] if executed_tools_data else None

            return {
                "content": final_content,
                "tool_data": primary_tool,
                "all_tools_data": executed_tools_data,
                "references": [f"{', '.join(d['sections'])}: {d['title']}" for d in retrieved_docs],
                "retrieved_snippets": [{"section": d["sections"], "snippet": d["snippet"]} for d in retrieved_docs],
                "updated_slots": updated_slots
            }

        except Exception as e:
            return {
                "content": f"দুঃখিত, অনুরোধটি প্রক্রিয়াকরণে সমস্যা হয়েছে: {str(e)}",
                "tool_data": None,
                "all_tools_data": [],
                "references": [],
                "retrieved_snippets": [],
                "updated_slots": updated_slots
            }
