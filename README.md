# 🎓 OppRank – AI Opportunity Inbox Copilot

**Parse, rank, and prioritize scholarship, internship, and competition emails – no API key required.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📌 Problem Statement

University students receive dozens of emails about scholarships, internships, fellowships, and competitions. Many are ignored, misunderstood, or lost in spam. **OppRank** scans opportunity emails, extracts key details (deadline, eligibility, required documents), and ranks them based on a student’s profile – showing exactly which opportunities to pursue first and why.

---

## ✨ Features

- ✅ **Email parsing** – Upload JSON, paste raw emails, or use built‑in samples  
- ✅ **AI‑free extraction** – Rule‑based (regex + keywords) – works offline, no API key  
- ✅ **Deadline handling** – Detects dates, marks expired opportunities (still shows them)  
- ✅ **Smart ranking** – Scores based on urgency, relevance, eligibility, and completeness  
- ✅ **Personalised output** – Explains priority reasons and provides an action checklist  
- ✅ **Student profile** – Degree, CGPA, skills, preferred types, financial need, location  
- ✅ **Web interface** – Built with Streamlit, runs in your browser  

---

## 🧰 Tech Stack

| Layer       | Technology                     |
|-------------|--------------------------------|
| Frontend    | Streamlit                      |
| Backend     | Python 3.8+                    |
| Extraction  | Regex + keyword matching       |
| Date parsing| `python-dateutil`              |
| Data        | JSON, Python dataclasses       |

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/opprank.git
   cd opprank
