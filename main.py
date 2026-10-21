"""
Bangladesh Income Tax Assistant (CLI Interface)
Interactive Goal-Based Tax Agent powered by RAG and Groq.
"""

import sys
import json

# Terminal UTF-8 fix for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import GROQ_API_KEY
from tax_agent import BangladeshTaxAgent
from calculator import get_exemption_limit

def main():
    agent = BangladeshTaxAgent(api_key=GROQ_API_KEY)
    
    print("=" * 65)
    print("  🇧🇩 BANGLADESH INCOME TAX AI AGENT (CLI)")
    print("  Based on Bangladesh Income Tax Act 2023 & NBR Rules")
    print("=" * 65)
    print("ক্যাটাগরি নির্বাচন করুন:")
    print("1. সাধারণ পুরুষ (Regular Male - 3.5 Lakh Free)")
    print("2. নারী / ৬৫+ বছর বয়সী (Female & Senior - 4.0 Lakh Free)")
    print("3. প্রতিবন্ধী ব্যক্তি (Disabled - 4.75 Lakh Free)")
    print("4. গেজেটভুক্ত মুক্তিযোদ্ধা (Freedom Fighter - 5.0 Lakh Free)")
    
    choice = input("Select category [1-4] (Default 1): ").strip()
    cat_map = {
        "1": "regular",
        "2": "female",
        "3": "disabled",
        "4": "freedom_fighter"
    }
    user_cat = cat_map.get(choice, "regular")
    print(f">> Selected Profile: {user_cat} (Tax-free limit: BDT {get_exemption_limit(user_cat):,})")
    print("\nপ্রশ্ন করুন বাংলা, ইংরেজি বা বাংলিশে। বের হতে 'exit' লিখুন।\n" + "-" * 65)

    messages_history = []

    while True:
        try:
            user_input = input("\nUser 🧑: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\nধন্যবাদ! আয়কর সহকারী সেশন সমাপ্ত।")
                break

            messages_history.append({"role": "user", "content": user_input})
            
            print("\nAgent 🤖 ভাবছে...", end="\r")
            result = agent.respond(messages_history, taxpayer_category=user_cat)
            reply = result["content"]
            
            print("\nAgent 🤖: " + reply)
            
            if result.get("references"):
                print("\n[📚 উদ্ধৃত আইন ও ধারা: " + ", ".join(result["references"]) + "]")

            messages_history.append({"role": "assistant", "content": reply})

        except KeyboardInterrupt:
            print("\nসেশন সমাপ্ত।")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()