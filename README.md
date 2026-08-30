# SASES

**SASES** (Seed-Apollo Self-Evolving System) is a privacy-first, local-first AI self-evolving ecosystem.  
It combines autonomous seed iteration, credit systems, pollination mechanisms, contribution ranking, and an extensible harness runtime to create a distributed AI service network.

> **One brain, many windows.**  
> SASES is designed to be lightweight, modular, and community-driven.

---

## ✨ Core Features

- **Seed Architecture**  
  Automatic generation, branching, synthesis, verification, backtracking, and knowledge accumulation.

- **Apollo Security Architecture**  
  Content safety scanning, tamper-proof state signatures, and risk control.

- **Root-Vein Architecture**  
  Multi-model routing, tool invocation, and future device I/O support.

- **Credit & Pollination System**  
  Earn credits by contributing seeds, manual pollination, or providing feedback. Credits are protected by HMAC state signatures.

- **Contribution Leaderboard**  
  A reputation-based ranking that rewards real contributions instead of simple credit accumulation.

- **Modular Harness Runtime (planned)**  
  A unified runtime for mini-apps, space nodes, and AGI tool orchestration.

---

## 🧱 Project Structure
sases/
├── app_full.py # FastAPI entry point
├── main.py # Autonomous seed iteration loop
├── process_seeds.py # Process external seed pool
├── merge_external_seeds.py # Merge and deduplicate seeds
├── auto_process_external.py # Monitor and auto-process seeds
├── core/
│ ├── config.py # Centralized configuration
│ ├── db.py # Database initialization
│ ├── auth_service.py # Authentication, credits, signatures
│ ├── knowledge_base.py # Knowledge base management
│ ├── contribution_log.py # Contribution logging and leaderboard
│ ├── seed_utils.py # Code utilities and API wrapper
│ ├── similarity.py # Semantic deduplication
│ ├── sandbox.py # Safe code execution
│ └── safety_scan.py # Content safety scanning
├── tests/ # Unit tests (27 passed)
└── static/ # Web console and chat UI

text

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn openai chromadb rank_bm25 passlib[bcrypt] python-jose[cryptography] python-multipart scikit-learn
2. Configure environment variables
Create a .env file or set the following variables:

text
DEEPSEEK_API_KEY=your_deepseek_api_key
SASES_SECRET_KEY=your_jwt_secret
Optional:

text
MODEL_NAME=deepseek-v4-flash
SASES_PORT=8001
3. Start the web service
bash
python -m uvicorn app_full:app --reload --port 8001
Visit http://127.0.0.1:8001/static/index.html to open the console.

🧪 Run Tests
bash
python -m pytest tests/ -v
All 27 unit tests should pass.

🎯 Current Status
Seed iteration loop with semantic deduplication

External seed submission and processing

Credit system with HMAC tamper detection

Pollination mechanism (manual and auto)

Contribution leaderboard

Modular route structure (core/api_routes/)

Basic web console and chat UI

📜 License
This project is licensed under the Apache License 2.0.

🤝 Contributing
Contributions are welcome! Please read CONTRIBUTING.md before submitting a pull request.

📬 Contact
GitHub: SASESseed/sases

Hugging Face: BlossomArchitecture