"""
Deterministic Tax Calculator Engine
Driven by verified rules.json (Income Tax Act 2023 & Finance Acts).
Supports:
- Assessment Year 2025-2026 (PwC verified slabs + 30% top bracket)
- Assessment Year 2026-2027 (Budget proposals)
- Exact tokenized gift verification (no substring false-positives)
- Statutory Minimum Tax (BDT 5,000)
"""

import json
import os
import re

RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")

def load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

RULES = load_rules()


def normalize_bangla_sender_word(word: str) -> str:
    """Strips Bengali suffixes (র, ের, য়ের, কে) or maps canonical relatives/senders."""
    w = word.strip().lower()
    SENDER_CANONICAL = {
        "বাবার": "বাবা", "বাবাকে": "বাবা",
        "মায়ের": "মা", "মায়ের": "মা", "মাকে": "মা",
        "পিতার": "পিতা", "পিতাকে": "পিতা",
        "মাতার": "মাতা", "মাতাকে": "মাতা",
        "ভাইয়ের": "ভাই", "ভাইয়ের": "ভাই", "ভাইকে": "ভাই",
        "বোনের": "বোন", "বোনকে": "বোন",
        "বন্ধুর": "বন্ধু", "বন্ধুকে": "বন্ধু",
        "ছেলের": "ছেলে", "ছেলেকে": "ছেলে",
        "মেয়ের": "মেয়ে", "মেয়ের": "মেয়ে", "মেয়েকে": "মেয়ে", "মেয়েকে": "মেয়ে",
        "স্বামীর": "স্বামী", "স্বামীকে": "স্বামী",
        "স্ত্রীর": "স্ত্রী", "স্ত্রীকে": "স্ত্রী",
        "কলিগের": "কলিগ", "সহকর্মীর": "সহকর্মী",
        "ব্যাংকে": "ব্যাংক"
    }
    if w in SENDER_CANONICAL:
        return SENDER_CANONICAL[w]
    for sfx in ["য়ের", "য়ের", "ের", "কে", "র"]:
        if w.endswith(sfx) and len(w) > len(sfx) + 1:
            return w[:-len(sfx)]
    return w


def tokenize_words(text: str) -> set:
    """Extracts lowercase individual word tokens supporting English & Bengali, including suffix-stripped forms."""
    raw_tokens = set(re.findall(r"[\w\u0980-\u09FF]+", text.lower()))
    expanded = set(raw_tokens)
    for t in raw_tokens:
        norm = normalize_bangla_sender_word(t)
        if norm:
            expanded.add(norm)
    return expanded


def get_year_config(year: str = None) -> dict:
    active_year = year or RULES.get("active_assessment_year", "2025-2026")
    if active_year not in RULES["years"]:
        active_year = "2025-2026"
    return RULES["years"][active_year]


def get_exemption_limit(category: str = "regular", year: str = None) -> int:
    cat = category.lower().strip()
    y_conf = get_year_config(year)
    limits = y_conf["exemption_limits"]
    if cat in ["female", "female_senior", "senior", "মহিলা"]:
        return limits["female_senior"]["limit"]
    elif cat in ["disabled", "প্রতিবন্ধী", "third_gender"]:
        return limits["disabled"]["limit"]
    elif cat in ["freedom_fighter", "মুক্তিযোদ্ধা"]:
        return limits["freedom_fighter"]["limit"]
    return limits["regular"]["limit"]


def compute_slab_tax(taxable_income: float, category: str = "regular", year: str = None, apply_min_tax: bool = True) -> dict:
    y_conf = get_year_config(year)
    exemption = get_exemption_limit(category, year)

    if taxable_income <= exemption:
        return {
            "taxable_income": taxable_income,
            "exemption_limit": exemption,
            "total_tax": 0.0,
            "slabs": [
                {
                    "slab": f"প্রথম {exemption:,.0f} টাকা পর্যন্ত",
                    "rate": "0%",
                    "amount": taxable_income,
                    "tax": 0.0
                }
            ],
            "min_tax_applied": False,
            "status": "করমুক্ত (Tax Free)"
        }

    remaining = taxable_income - exemption
    calculated_tax = 0.0
    slabs = [
        {
            "slab": f"প্রথম {exemption:,.0f} টাকা পর্যন্ত",
            "rate": "0%",
            "amount": exemption,
            "tax": 0.0
        }
    ]

    for item in y_conf["slabs"]:
        if remaining <= 0:
            break
        limit = item["limit"]
        rate = item["rate"]
        label = item["label"]

        if limit is None:
            tax_chunk = remaining * rate
            calculated_tax += tax_chunk
            slabs.append({
                "slab": label,
                "rate": f"{int(rate * 100)}%",
                "amount": remaining,
                "tax": round(tax_chunk, 2)
            })
            remaining = 0
        else:
            chunk = min(remaining, limit)
            tax_chunk = chunk * rate
            calculated_tax += tax_chunk
            slabs.append({
                "slab": label,
                "rate": f"{int(rate * 100)}%",
                "amount": chunk,
                "tax": round(tax_chunk, 2)
            })
            remaining -= chunk

    # Statutory Minimum Tax check (BDT 5,000 for City Corporation / default)
    min_tax_amount = y_conf.get("minimum_tax", {}).get("default", 5000)
    final_tax = calculated_tax
    min_tax_applied = False

    if apply_min_tax and calculated_tax > 0 and calculated_tax < min_tax_amount:
        final_tax = float(min_tax_amount)
        min_tax_applied = True

    return {
        "taxable_income": taxable_income,
        "exemption_limit": exemption,
        "calculated_tax": round(calculated_tax, 2),
        "total_tax": round(final_tax, 2),
        "min_tax_applied": min_tax_applied,
        "slabs": slabs,
        "status": "করযোগ্য (Taxable)"
    }


def salary_tax(gross_annual_salary: float, category: str = "regular", year: str = None) -> dict:
    s_rules = RULES["salary_rules"]
    fraction_deduction = gross_annual_salary * s_rules["exemption_fraction"]
    allowable_exemption = min(fraction_deduction, s_rules["max_exemption_amount"])
    net_taxable_salary = max(0.0, gross_annual_salary - allowable_exemption)

    tax_result = compute_slab_tax(net_taxable_salary, category, year)
    tax_result["gross_salary"] = gross_annual_salary
    tax_result["salary_exemption_applied"] = round(allowable_exemption, 2)
    tax_result["section"] = s_rules["section"]
    return tax_result


def rental_tax(annual_rent: float, is_commercial: bool = False, category: str = "regular", year: str = None) -> dict:
    hp_rules = RULES["house_property_rules"]
    rate = hp_rules["commercial_repair_deduction"] if is_commercial else hp_rules["residential_repair_deduction"]
    repair_allowance = annual_rent * rate
    net_rental_income = max(0.0, annual_rent - repair_allowance)

    tax_result = compute_slab_tax(net_rental_income, category, year)
    tax_result["gross_rent"] = annual_rent
    tax_result["property_type"] = "বাণিজ্যিক (Commercial)" if is_commercial else "আবাসিক (Residential)"
    tax_result["repair_allowance"] = round(repair_allowance, 2)
    tax_result["net_rental_income"] = round(net_rental_income, 2)
    tax_result["section"] = hp_rules["section"]
    return tax_result


def gift_check(amount: float, sender: str = "", banking_channel: bool = True) -> dict:
    """
    Exact word token matching.
    Prevents false matches where substrings like 'ma' in 'Mahmud' or 'bon' in 'bondhu' trigger exemption.
    """
    g_rules = RULES["gift_rules"]
    sender_tokens = tokenize_words(sender)

    # 1. Explicit Non-relatives check (friend, bondhu, colleague)
    non_relative_tokens = set(g_rules["non_relatives"])
    has_non_relative = bool(sender_tokens.intersection(non_relative_tokens))

    # 2. Close Relatives check (exact word match)
    exempt_tokens = set(g_rules["exempt_relatives"])
    has_exempt_relative = bool(sender_tokens.intersection(exempt_tokens))

    # If sender explicitly contains friend/colleague, it's non-relative regardless of name
    if has_non_relative or not has_exempt_relative:
        return {
            "amount": amount,
            "sender": sender,
            "banking_channel": banking_channel,
            "is_taxable": True,
            "taxable_gift_amount": amount,
            "reason": "পিতা, মাতা, স্বামী, স্ত্রী বা নির্দিষ্ট নিকটাত্মীয় ব্যতীত বন্ধু বা অন্য ব্যক্তি থেকে প্রাপ্ত উপহার অন্যান্য খাতের আয় হিসেবে করযোগ্য।",
            "section": g_rules["section"]
        }

    # If it is a close relative:
    if banking_channel:
        return {
            "amount": amount,
            "sender": sender,
            "banking_channel": True,
            "is_taxable": False,
            "taxable_gift_amount": 0.0,
            "reason": "পিতা, মাতা, স্বামী, স্ত্রী বা নিকটাত্মীয়দের কাছ থেকে ব্যাংকিং চ্যানেলে প্রাপ্ত উপহার ধারা ৬৬(ঘ) অনুযায়ী সম্পূর্ণ করমুক্ত।",
            "section": g_rules["section"]
        }
    else:
        return {
            "amount": amount,
            "sender": sender,
            "banking_channel": False,
            "is_taxable": True,
            "taxable_gift_amount": amount,
            "reason": "নিকটাত্মীয় হলেও নগদ অর্থে (ক্যাশ) ২০,০০০ টাকার অধিক উপহার প্রাপ্তি ধারা ৬৬(ঘ) অনুযায়ী আইনগত যাচাই সাপেক্ষে করযোগ্য হতে পারে।",
            "section": g_rules["section"]
        }


def combined_tax(
    gross_salary: float = 0.0,
    annual_rent: float = 0.0,
    net_rental_income: float = 0.0,
    is_commercial: bool = False,
    taxable_gift: float = 0.0,
    business_income: float = 0.0,
    other_income: float = 0.0,
    category: str = "regular",
    year: str = None
) -> dict:
    sal_res = salary_tax(gross_salary, category, year) if gross_salary > 0 else {"salary_exemption_applied": 0, "taxable_income": 0}
    net_salary = sal_res.get("taxable_income", 0)

    if net_rental_income > 0:
        net_rent = net_rental_income
        rent_ded = 0.0
    elif annual_rent > 0:
        rent_res = rental_tax(annual_rent, is_commercial, category, year)
        net_rent = rent_res.get("net_rental_income", 0)
        rent_ded = rent_res.get("repair_allowance", 0)
    else:
        net_rent = 0.0
        rent_ded = 0.0

    total_net = net_salary + net_rent + taxable_gift + business_income + other_income
    tax_result = compute_slab_tax(total_net, category, year)

    tax_result["breakdown_by_head"] = {
        "gross_salary": gross_salary,
        "salary_exemption": sal_res.get("salary_exemption_applied", 0),
        "net_salary": net_salary,
        "gross_rent": annual_rent if annual_rent > 0 else net_rental_income,
        "rent_deduction": rent_ded,
        "net_rent": net_rent,
        "taxable_gift": taxable_gift,
        "business_income": business_income,
        "other_income": other_income,
        "total_taxable_income": total_net
    }
    return tax_result


# Convenience aliases for standard naming
calculate_salary_tax = salary_tax
calculate_rental_tax = rental_tax
calculate_combined_tax = combined_tax
check_gift_taxability = gift_check