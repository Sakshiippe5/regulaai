import pymupdf

PAGE_1 = """SAMPLE REGULATORY CIRCULAR (FICTIONAL - FOR DEVELOPMENT ONLY)
Circular No. SAMPLE/2026-27/01
Date: April 1, 2026
Subject: Cyber Incident Reporting and Resilience for Urban Co-operative Banks

1. Applicability
1.1 This circular applies to all Urban Co-operative Banks and Small Finance Banks.

2. Incident reporting
2.1 Banks shall report any cyber security incident to the regulator within 6 hours of detection.
2.2 Banks shall designate a Chief Information Security Officer (CISO) by June 30, 2026.
"""

PAGE_2 = """3. Policy and governance
3.1 The Board shall approve a Cyber Security Policy and review it at least annually.
3.2 Banks shall conduct a vulnerability assessment at least once every six months.

4. Disclosure and certification
4.1 Banks shall disclose cyber incidents affecting customers on their website within 24 hours of confirmation.
4.2 Compliance with this circular shall be certified to the regulator by September 30, 2026.
"""

doc = pymupdf.open()
for content in (PAGE_1, PAGE_2):
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 545, 790), content, fontsize=11)
doc.save("data/circulars/sample_cyber_circular.pdf")
print("Created data/circulars/sample_cyber_circular.pdf")