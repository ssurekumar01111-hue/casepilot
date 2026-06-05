"""
CasePilot — Document Templates
Defines which documents to generate per dispute type
"""

DISPUTE_DOCUMENTS = {
    "landlord_deposit": [
        "legal_notice",
        "consumer_complaint",
        "affidavit"
    ],
    "landlord_eviction": [
        "legal_notice",
        "affidavit"
    ],
    "consumer": [
        "consumer_complaint",
        "legal_notice"
    ],
    "rti_filing": [
        "rti_first_appeal",
        "rti_second_appeal"
    ],
    "workplace": [
        "legal_notice",
        "police_complaint",
        "affidavit"
    ],
    "cyber_crime": [
        "police_complaint",
        "legal_notice"
    ],
    "motor_accident": [
        "legal_notice",
        "police_complaint"
    ],
    "default": [
        "legal_notice",
        "affidavit"
    ]
}

DOCUMENT_PROMPTS = {
    "legal_notice": """Generate a formal legal notice in professional legal language.
Structure:
- Header: LEGAL NOTICE (bold)
- To: [Opponent name and address placeholder]
- Subject line summarizing the dispute
- Opening: "I/We, the undersigned..."
- Facts section: numbered paragraphs with all extracted case facts
- Legal basis: cite the specific acts and sections found
- Demand: clear specific demand (payment/action/response)
- Timeline: "within 15 days of receipt of this notice"
- Consequence: legal action warning
- Closing: signature block
Make it 400-600 words. Professional, firm, legally precise.""",

    "consumer_complaint": """Generate a formal consumer complaint for filing at the District Consumer Disputes Redressal Commission.
Structure:
- Title: COMPLAINT UNDER CONSUMER PROTECTION ACT, 2019
- Before: District Consumer Disputes Redressal Commission, [City]
- Complainant: [Name, Address]
- Opposite Party: [Name, Address]
- FACTS OF THE CASE: numbered paragraphs
- CAUSE OF ACTION: specific violations under Consumer Protection Act 2019
- RELIEF SOUGHT: specific reliefs requested with amounts
- DECLARATION: "I/We declare that the facts stated above are true..."
- Date and signature block
Make it structured and complete for actual filing.""",

    "rti_first_appeal": """Generate a First Appeal under Right to Information Act 2005, Section 19(1).
Structure:
- To: The First Appellate Authority, [Department Name]
- Subject: First Appeal under Section 19(1) of RTI Act 2005
- RTI Application details: date filed, registration number placeholder
- Grounds of appeal: failure to respond within 30 days
- Relief sought: direction to provide information immediately
- Declaration
Make it concise and legally precise.""",

    "rti_second_appeal": """Generate a Second Appeal to the Central/State Information Commission under RTI Act Section 19(3).
Structure:
- To: The Central/State Information Commissioner
- Subject: Second Appeal under Section 19(3) of RTI Act 2005
- Details of original RTI and First Appeal
- Grounds for second appeal
- Relief sought including penalty under Section 20
- Declaration""",

    "police_complaint": """Generate a formal police complaint (FIR/Written Complaint).
Structure:
- To: The Station House Officer, [Police Station Name]
- Subject: Complaint regarding [dispute type]
- Complainant details
- FACTS: chronological numbered paragraphs
- ACCUSED/OPPOSITE PARTY details
- PRAYER: request to register FIR and take action
- Applicable IPC/BNS sections
- Declaration
Make it factual, chronological, and suitable for police filing.""",

    "affidavit": """Generate a sworn affidavit.
Structure:
- Title: AFFIDAVIT
- I, [Name], aged [age], residing at [address], do hereby solemnly affirm and state as follows:
- Numbered paragraphs with case facts in first person
- "That the facts stated above are true to the best of my knowledge and belief."
- "No part of it is false and nothing material has been concealed."
- Deponent signature line
- Verification clause
- Notary/Oath Commissioner section
Make it suitable for court filing."""
}
