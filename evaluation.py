"""
Evaluation Dataset for Bangladesh Tax Agent
Total Cases: 40 Comprehensive Real-World Scenarios
All expected values are hand-calculated with step-by-step mathematical working in comments.
"""

TEST_DATASET = [
    # =========================================================================
    # 1. SALARY CASES (Section 32/33: Exemption = min(Gross/3, 450,000))
    # =========================================================================
    {
        # Working: Gross 850,000 -> Exemption 850,000/3 = 283,333.33 (<= 450,000)
        # Taxable = 566,666.67
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 116,666.67 @ 10% = 11,666.67
        # Total Tax = 16,666.67
        "id": "SAL-01",
        "category": "Salary",
        "query": "আমার বার্ষিক মোট বেতন ৮,৫০,০০০ টাকা। পুরুষ করদাতা। ট্যাক্স কত হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 16666.67,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Gross 1,200,000 -> Exemption 1,200,000/3 = 400,000 (<= 450,000)
        # Taxable = 800,000
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 350,000 @ 10% = 35,000
        # Total Tax = 40,000.0
        "id": "SAL-02",
        "category": "Salary",
        "query": "My annual salary is 1200000 BDT. How much income tax should I pay?",
        "taxpayer_cat": "regular",
        "expected_tax": 40000.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Gross 480,000 -> Exemption 160,000 -> Taxable = 320,000
        # Threshold for regular male = 350,000 -> Taxable <= Threshold -> Tax = 0.0
        "id": "SAL-03",
        "category": "Salary",
        "query": "Amar monthly salary 40000 taka (annual 480000). Tax koto?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Gross 600,000 -> Exemption 200,000 -> Taxable = 400,000
        # Female threshold = 400,000 -> Taxable <= Threshold -> Tax = 0.0
        "id": "SAL-04",
        "category": "Salary",
        "query": "বার্ষিক বেতন ৬,০০,০০০ টাকা, কিন্তু করদাতা একজন নারী। ট্যাক্স কত?",
        "taxpayer_cat": "female",
        "expected_tax": 0.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Gross 2,000,000 -> Exemption = min(666,666.67, 450,000) = 450,000
        # Taxable = 1,550,000
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 400,000 @ 10% = 40,000;
        #        500,000 @ 15% = 75,000; 200,000 @ 20% = 40,000
        # Total Tax = 5,000 + 40,000 + 75,000 + 40,000 = 160,000.0
        "id": "SAL-05",
        "category": "Salary",
        "query": "বার্ষিক বেতন ২০,০০,০০০ টাকা। পুরুষ করদাতা। মোট ট্যাক্স কত?",
        "taxpayer_cat": "regular",
        "expected_tax": 160000.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Gross 1,500,000 -> Exemption = 450,000 -> Taxable = 1,050,000
        # Female threshold = 400,000
        # Slabs: 400,000 @ 0% = 0; 100,000 @ 5% = 5,000; 400,000 @ 10% = 40,000; 150,000 @ 15% = 22,500
        # Total Tax = 67,500.0
        "id": "SAL-06",
        "category": "Salary",
        "query": "Female senior executive annual salary 1500000 BDT. Tax calculation?",
        "taxpayer_cat": "female",
        "expected_tax": 67500.0,
        "expected_section": "32",
        "is_ambiguous": False
    },

    # =========================================================================
    # 2. HOUSE PROPERTY RENT CASES (Section 36-38: Res=25%, Comm=30%)
    # =========================================================================
    {
        # Working: Gross Rent 400,000 -> Residential deduction 25% = 100,000 -> Taxable = 300,000
        # Threshold = 350,000 -> Taxable <= Threshold -> Tax = 0.0
        "id": "RENT-01",
        "category": "House Rent",
        "query": "একটি আবাসিক ফ্ল্যাট ভাড়া দিয়ে বছরে ৪,০০,০০০ টাকা পাই। কোনো অন্য আয় নেই। ট্যাক্স কত?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "36",
        "is_ambiguous": False
    },
    {
        # Working: Gross Rent 1,000,000 -> Commercial deduction 30% = 300,000 -> Taxable = 700,000
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 250,000 @ 10% = 25,000
        # Total Tax = 30,000.0
        "id": "RENT-02",
        "category": "House Rent",
        "query": "বাণিজ্যিক দোকান ভাড়া থেকে বছরে ১০,০০,০০০ টাকা পাই। কত ট্যাক্স হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 30000.0,
        "expected_section": "36",
        "is_ambiguous": False
    },
    {
        # Working: Gross 600,000 -> Res 25% = 150,000 -> Taxable = 450,000
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000 -> Total Tax = 5,000.0
        "id": "RENT-03",
        "category": "House Rent",
        "query": "Residential building annual rent 600000 taka. Calculate payable tax.",
        "taxpayer_cat": "regular",
        "expected_tax": 5000.0,
        "expected_section": "36",
        "is_ambiguous": False
    },
    {
        # Working: Gross 800,000 -> Res 25% = 200,000 -> Taxable = 600,000
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 150,000 @ 10% = 15,000 -> Total = 20,000.0
        "id": "RENT-04",
        "category": "House Rent",
        "query": "Amar flat theke annual 8 lakh taka rent ashe. Tax calculation dao.",
        "taxpayer_cat": "regular",
        "expected_tax": 20000.0,
        "expected_section": "36",
        "is_ambiguous": False
    },
    {
        # Working: Commercial Gross 500,000 -> Comm 30% = 150,000 -> Taxable = 350,000 <= 350,000 -> 0.0
        "id": "RENT-05",
        "category": "House Rent",
        "query": "বাণিজ্যিক গুদাম ভাড়া হতে বার্ষিক ৫,০০,০০০ টাকা পাই। কর কত?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "36",
        "is_ambiguous": False
    },

    # =========================================================================
    # 3. GIFT TAXATION CASES (Section 66(ঘ) - অন্যান্য উৎস হতে আয়)
    # =========================================================================
    {
        # Working: Close relative (Father) via banking channel -> 100% Tax Free -> Tax = 0.0
        "id": "GIFT-01",
        "category": "Gift",
        "query": "বাবা আমাকে ব্যাংকের মাধ্যমে ৫ লাখ টাকা উপহার দিয়েছেন। ট্যাক্স দেওয়া লাগবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "66",
        "is_ambiguous": False
    },
    {
        # Working: Non-relative (Friend) -> Taxable Gift 500,000 BDT under Section 66(ঘ)
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 50,000 @ 10% = 5,000
        # Total Tax = 10,000.0
        "id": "GIFT-02",
        "category": "Gift",
        "query": "amar ekjon bondhu amake 5 lakh taka gift dise bank e, tax lagbe?",
        "taxpayer_cat": "regular",
        "expected_tax": 10000.0,
        "expected_section": "66",
        "is_ambiguous": False
    },
    {
        # Working: Non-relative ('Mahmud amar bondhu') -> Taxable Gift 600,000 BDT under Section 66(ঘ)
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 150,000 @ 10% = 15,000
        # Total Tax = 20,000.0
        "id": "GIFT-03",
        "category": "Gift",
        "query": "Mahmud amar bondhu, she amake 6 lakh taka gift korlo. Tax koto?",
        "taxpayer_cat": "regular",
        "expected_tax": 20000.0,
        "expected_section": "66",
        "is_ambiguous": False
    },
    {
        # Working: Ambiguous gift - missing sender and channel -> Must trigger clarification first
        "id": "GIFT-04",
        "category": "Gift (Ambiguous)",
        "query": "আমি ৫ লাখ টাকা উপহার পেয়েছি। ট্যাক্স নিয়ম কী?",
        "taxpayer_cat": "regular",
        "expected_tax": None,
        "expected_section": "66",
        "is_ambiguous": True
    },
    {
        # Working: Mother gave cash -> Section 66 cash limitation / compliance check
        "id": "GIFT-05",
        "category": "Gift",
        "query": "মা আমাকে ক্যাশে ৩ লাখ টাকা দিয়েছেন ব্যাংকে জমা দেওয়ার জন্য।",
        "taxpayer_cat": "regular",
        "expected_tax": None,
        "expected_section": "66",
        "is_ambiguous": False
    },
    {
        # Working: Sister bank transfer 200,000 -> Close relative tax-free -> Tax = 0.0
        "id": "GIFT-06",
        "category": "Gift",
        "query": "আমার বোন আমাকে ব্যাংক একাউন্টে ২ লাখ টাকা পাঠিয়েছে উপহার হিসেবে।",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "66",
        "is_ambiguous": False
    },

    # =========================================================================
    # 4. ZERO INCOME & RETURN FILING (Section 166)
    # =========================================================================
    {
        # Working: Ambiguous zero income -> Must clarify TIN, motor car, urban property
        "id": "ZERO-01",
        "category": "Zero Income (Ambiguous)",
        "query": "amr ayy na thakle ki kor dite hbe",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "166",
        "is_ambiguous": True
    },
    {
        # Working: Private car owner with zero income -> Mandatory return filing under Section 166(2)
        "id": "ZERO-02",
        "category": "Return Filing",
        "query": "আমার কোনো চাকরি বা ব্যবসা নেই, কিন্তু আমার একটি প্রাইভেট কার আছে। রিটার্ন দেওয়া লাগবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "166",
        "is_ambiguous": False
    },
    {
        # Working: Trade license holder with zero profit -> Mandatory return filing under Section 166
        "id": "ZERO-03",
        "category": "Return Filing",
        "query": "I have no income this year, but I have a trade license. Is tax return mandatory?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "166",
        "is_ambiguous": False
    },
    {
        # Working: Student with no income and no assets -> Return not mandatory
        "id": "ZERO-04",
        "category": "Return Filing",
        "query": "আমি একজন ছাত্র, আমার কোনো আয় বা সম্পদ নেই। আমার কি রিটার্ন দাখিল করতে হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "166",
        "is_ambiguous": False
    },

    # =========================================================================
    # 5. FREELANCING & ITES (Sixth Schedule, Part 1 cl. 21)
    # =========================================================================
    {
        # Working: Government approved ITES via banking channel -> 100% Tax Exempt -> Tax = 0.0
        "id": "FREE-01",
        "category": "Freelancing",
        "query": "আমি আপওয়ার্ক থেকে ফ্রিল্যান্সিং রেমিট্যান্স আয় করি বছরে ৮ লাখ টাকা। ট্যাক্স কীভাবে হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "Sixth Schedule",
        "is_ambiguous": False
    },
    {
        # Working: Fiverr IT software export via banking channel -> Tax Exempt -> Tax = 0.0
        "id": "FREE-02",
        "category": "Freelancing",
        "query": "Fiverr freelancing software export revenue 1500000 BDT via banking channel. Tax rate?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "Sixth Schedule",
        "is_ambiguous": False
    },
    {
        # Working: Freelancer received money via informal/hundi channel -> Not exempt, full tax applicable
        "id": "FREE-03",
        "category": "Freelancing",
        "query": "ফ্রিল্যান্সিংয়ের টাকা ব্যাংকে না এনে হুন্ডিতে ক্যাশ এনেছি ৫ লাখ টাকা। এটা কি করমুক্ত?",
        "taxpayer_cat": "regular",
        "expected_tax": None,
        "expected_section": "Sixth Schedule",
        "is_ambiguous": False
    },

    # =========================================================================
    # 6. BUSINESS & PROFESSION (Section 45-49)
    # =========================================================================
    {
        # Working: Net business profit 600,000 BDT
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 150,000 @ 10% = 15,000
        # Total Tax = 20,000.0
        "id": "BIZ-01",
        "category": "Business",
        "query": "মুদি দোকান থেকে খরচ বাদ দিয়ে বছরে ৬,০০,০০০ টাকা নীট লাভ হয়েছে। কত ট্যাক্স হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 20000.0,
        "expected_section": "45",
        "is_ambiguous": False
    },
    {
        # Working: Net business profit 800,000 BDT
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 350,000 @ 10% = 35,000
        # Total Tax = 40,000.0
        "id": "BIZ-02",
        "category": "Business",
        "query": "My retail shop profit after operational expenses is 800000 BDT. Tax?",
        "taxpayer_cat": "regular",
        "expected_tax": 40000.0,
        "expected_section": "45",
        "is_ambiguous": False
    },
    {
        # Working: Small boutique shop profit 300,000 BDT <= 350,000 regular threshold -> Tax = 0.0
        "id": "BIZ-03",
        "category": "Business",
        "query": "আমার ছোট বুটিক শপ থেকে বছরে ৩ লাখ টাকা নিট লাভ হয়। আমাকে কি কর দিতে হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "45",
        "is_ambiguous": False
    },

    # =========================================================================
    # 7. COMBINED INCOME CASES
    # =========================================================================
    {
        # Working: Salary 600,000 (Net = 400,000) + Net Rent 200,000 = Total Taxable 600,000 BDT
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 150,000 @ 10% = 15,000 -> Total = 20,000.0
        "id": "COMB-01",
        "category": "Combined Income",
        "query": "বার্ষিক বেতন ৬,০০,০০০ টাকা এবং বাড়িভাড়া থেকে নিট আয় ২,০০,০০০ টাকা। মোট ট্যাক্স কত?",
        "taxpayer_cat": "regular",
        "expected_tax": 20000.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Salary 900,000 (Net = 600,000) + Res Rent 400,000 (Net = 300,000) = Total Taxable 900,000
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 400,000 @ 10% = 40,000; 50,000 @ 15% = 7,500
        # Total Tax = 52,500.0
        "id": "COMB-02",
        "category": "Combined Income",
        "query": "Annual salary 900000 and residential rental income 400000. Total tax?",
        "taxpayer_cat": "regular",
        "expected_tax": 52500.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Salary 500,000 (Net 333,333.33) + Gift friend 100,000 = Total 433,333.33
        # Regular male threshold 350,000. Remaining = 83,333.33 @ 5% = 4,166.67
        # Minimum tax applies (City corp 5,000) -> Total Tax = 5,000.0
        "id": "COMB-03",
        "category": "Combined Income",
        "query": "বার্ষিক বেতন ৫ লাখ টাকা এবং বন্ধুর কাছ থেকে ১ লাখ টাকা উপহার পেয়েছি।",
        "taxpayer_cat": "regular",
        "expected_tax": 5000.0,
        "expected_section": "32",
        "is_ambiguous": False
    },

    # =========================================================================
    # 8. HIGH NET WORTH & PWC 30% TOP SLAB VERIFICATION
    # =========================================================================
    {
        # Working: Taxable income 4,000,000 BDT
        # Slabs:
        # 350,000 @ 0% = 0
        # 100,000 @ 5% = 5,000
        # 400,000 @ 10% = 40,000
        # 500,000 @ 15% = 75,000
        # 500,000 @ 20% = 100,000
        # 2,000,000 @ 25% = 500,000
        # Remaining 150,000 @ 30% = 45,000
        # Total Tax = 5,000 + 40,000 + 75,000 + 100,000 + 500,000 + 45,000 = 765,000.0
        "id": "TOP-01",
        "category": "High Net Worth",
        "query": "My taxable income is 4000000 BDT. Compute tax according to statutory progressive slabs.",
        "taxpayer_cat": "regular",
        "expected_tax": 765000.0,
        "expected_section": "Finance Act",
        "is_ambiguous": False
    },
    {
        # Working: Taxable income 5,000,000 BDT
        # 3,850,000 up to 25% slab = 720,000; Remaining 1,150,000 @ 30% = 345,000
        # Total Tax = 1,065,000.0
        "id": "TOP-02",
        "category": "High Net Worth",
        "query": "করযোগ্য আয় ৫০,০০,০০০ (৫০ লাখ) টাকা হলে মোট প্রদেয় কর কত?",
        "taxpayer_cat": "regular",
        "expected_tax": 1065000.0,
        "expected_section": "Finance Act",
        "is_ambiguous": False
    },

    # =========================================================================
    # 9. SPECIAL TAXPAYER CATEGORIES (Female, Disabled, Freedom Fighter)
    # =========================================================================
    {
        # Working: Disabled person threshold = 475,000 BDT
        # Taxable business income 450,000 BDT <= 475,000 -> Tax = 0.0
        "id": "CAT-01",
        "category": "Special Category",
        "query": "আমি একজন প্রতিবন্ধী ব্যক্তি, আমার বার্ষিক দোকান আয় ৪,৫০,০০০ টাকা। ট্যাক্স কত?",
        "taxpayer_cat": "disabled",
        "expected_tax": 0.0,
        "expected_section": "Finance Act",
        "is_ambiguous": False
    },
    {
        # Working: Freedom Fighter threshold = 500,000 BDT
        # Net income 500,000 BDT <= 500,000 -> Tax = 0.0
        "id": "CAT-02",
        "category": "Special Category",
        "query": "গেজেটভুক্ত বীর মুক্তিযোদ্ধা করদাতার বার্ষিক আয় ৫ লাখ টাকা হলে কর কত?",
        "taxpayer_cat": "freedom_fighter",
        "expected_tax": 0.0,
        "expected_section": "Finance Act",
        "is_ambiguous": False
    },
    {
        # Working: Senior citizen (age 68) female, threshold 400,000 BDT
        # Annual pension/salary 700,000 -> Exemption 233,333.33 -> Taxable = 466,666.67
        # Slabs: 400,000 @ 0% = 0; Remaining 66,666.67 @ 5% = 3,333.33
        # Minimum tax applies -> Total Tax = 5,000.0
        "id": "CAT-03",
        "category": "Special Category",
        "query": "আমার বয়স ৬৮ বছর (মহিলা)। বার্ষিক পেনশন বা আয় ৭ লাখ টাকা। ট্যাক্স কত?",
        "taxpayer_cat": "female",
        "expected_tax": 5000.0,
        "expected_section": "Finance Act",
        "is_ambiguous": False
    },

    # =========================================================================
    # 10. MULTI-HEAD COMBINED EDGE CASES
    # =========================================================================
    {
        # Working: Salary 1,200,000 (Net 800,000) + Commercial Rent 600,000 (Net 420,000)
        # Total Taxable = 1,220,000 BDT
        # Slabs: 350,000 @ 0% = 0; 100,000 @ 5% = 5,000; 400,000 @ 10% = 40,000;
        #        370,000 @ 15% = 55,500 -> Total Tax = 100,500.0
        "id": "EDGE-01",
        "category": "Combined Edge",
        "query": "বেতন ১২ লাখ টাকা এবং বাণিজ্যিক দোকান ভাড়া ৬ লাখ টাকা। মোট ট্যাক্স কত?",
        "taxpayer_cat": "regular",
        "expected_tax": 100500.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: House rent without stating residential/commercial -> Ambiguous
        "id": "EDGE-02",
        "category": "Ambiguous Rent",
        "query": "আমি বাড়িভাড়া বাবদ বছরে ৫ লাখ টাকা পাই।",
        "taxpayer_cat": "regular",
        "expected_tax": None,
        "expected_section": "36",
        "is_ambiguous": True
    },
    {
        # Working: Salary with no other income below threshold
        # Gross 300,000 -> Net 200,000 <= 350,000 -> Tax = 0.0
        "id": "EDGE-03",
        "category": "Salary",
        "query": "আমার বার্ষিক আয় ৩,০০,০০০ টাকা। আমাকে কত কর দিতে হবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "32",
        "is_ambiguous": False
    },
    {
        # Working: Software firm employee receiving offshore remittance via bank -> Section 32 employment
        "id": "EDGE-04",
        "category": "Freelancing",
        "query": "Software export revenue received in bank account from foreign client 2000000 BDT. Is it tax free?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "Sixth Schedule",
        "is_ambiguous": False
    },
    {
        # Working: Business loss or zero profit
        "id": "EDGE-05",
        "category": "Business",
        "query": "এই বছর ব্যবসায় কোনো লাভ হয়নি, উল্টো লোকসান হয়েছে। কর কত আসবে?",
        "taxpayer_cat": "regular",
        "expected_tax": 0.0,
        "expected_section": "45",
        "is_ambiguous": False
    }
]
