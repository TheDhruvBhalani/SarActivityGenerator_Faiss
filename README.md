# SAR Activity Generator

An intelligent AI-powered system for automating the generation of Suspicious Activity Reports (SARs) for banking and financial institutions. This system combines Retrieval Augmented Generation (RAG), Large Language Model (LLM) orchestration, and Continual Learning to produce high-quality, regulatory-compliant SAR narratives.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [Regulatory Compliance](#regulatory-compliance)
- [Contributing](#contributing)
- [License](#license)

## Overview

Suspicious Activity Reports (SARs) are critical documents that financial institutions must file when they detect potentially suspicious transactions. Manually writing these reports is time-consuming, error-prone, and requires deep knowledge of regulatory requirements.

This system addresses these challenges by:

- **Automating narrative generation** using AI that understands regulatory language
- **Retrieving relevant context** from a knowledge base of regulations and past reports
- **Learning continuously** from analyst feedback to improve over time
- **Ensuring compliance** with PMLA, FIU-IND, and RBI guidelines

### How It Works

1. **Alert Ingestion**: The system receives an alert with customer and transaction data
2. **Context Retrieval**: RAG pipeline fetches relevant regulatory knowledge and similar past cases
3. **Narrative Generation**: LLM generates a compliant SAR narrative using the context
4. **Analyst Review**: Human analysts review, edit, and approve the generated narrative
5. **Learning Loop**: The system learns from analyst edits to improve future generations

## Key Features

### Intelligent Generation
- Context-aware narrative synthesis using transformer models
- Automatic inclusion of relevant regulatory citations
- Consistent formatting aligned with FIU-IND requirements

### Smart Retrieval (RAG)
- Semantic search over regulatory documents using FAISS
- Hybrid retrieval combining dense and sparse methods
- Cross-encoder reranking for improved relevance

### Continual Learning
- Automatic pattern extraction from analyst corrections
- Experience replay for few-shot learning
- Dynamic prompt optimization based on feedback
- Quality metrics tracking and visualization

### Enterprise Ready
- RESTful API for system integration
- JWT-based authentication
- Comprehensive audit trails
- Web-based analyst dashboard

## System Architecture

The system is organized into three integrated tracks:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SAR Generation System                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────────┐  │
│  │   TRACK A     │   │   TRACK B     │   │       TRACK C         │  │
│  │  RAG Pipeline │──▶│ LLM Engine    │──▶│  Continual Learning   │  │
│  └───────────────┘   └───────────────┘   └───────────────────────┘  │
│         │                    │                       │               │
│         ▼                    ▼                       ▼               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │
│  │ FAISS Index │     │ Transformer │     │ 5 Learning Components│   │
│  │ Knowledge DB│     │   Models    │     │ Pattern + Feedback   │   │
│  └─────────────┘     └─────────────┘     └─────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Track A: RAG Pipeline

The Retrieval Augmented Generation pipeline enriches LLM context with relevant information:

| Component | Description |
|-----------|-------------|
| **Alert Ingestion** | Parses incoming alerts and extracts key identifiers |
| **Customer Profile Retrieval** | Fetches customer demographics, account history, risk scores |
| **Transaction Summary** | Aggregates transaction statistics (volume, amount, channels) |
| **Knowledge Retrieval** | Semantic search over FAISS index for relevant regulations |
| **Context Assembly** | Combines all retrieved information into structured context |

**FAISS Configuration:**
- Embedding Model: `all-MiniLM-L6-v2` (384 dimensions)
- Index Type: Flat L2 (exact search)
- Top-K Retrieval: 5 documents

### Track B: LLM Generation Engine

The generation engine produces SAR narratives from assembled context:

| Component | Description |
|-----------|-------------|
| **Model Loader** | Loads and manages transformer models with optimizations |
| **Prompt Builder** | Constructs prompts with context, instructions, and examples |
| **Generation Engine** | Runs inference with configurable parameters |
| **Post-Processor** | Formats output and validates regulatory compliance |

**Model Support:**
- HuggingFace Transformers
- PEFT/LoRA for efficient fine-tuning
- 4-bit quantization via bitsandbytes
- Accelerate for multi-GPU support

### Track C: Continual Learning Engine

Five integrated components that enable the system to learn from analyst feedback:

| # | Component | Purpose |
|---|-----------|---------|
| 1 | **Feedback Collector** | Captures original vs. edited narratives, calculates edit distance, assigns quality scores |
| 2 | **Pattern Extractor** | Analyzes feedback corpus to identify recurring correction patterns (e.g., "always include transaction dates") |
| 3 | **Experience Replay** | Maintains a library of high-quality approved SARs for few-shot examples |
| 4 | **Prompt Updater** | Dynamically modifies generation prompts based on extracted patterns |
| 5 | **Metrics Tracker** | Monitors edit counts, quality scores, pattern compliance over time |

**Learning Triggers:**
- Pattern extraction runs every 5 feedback submissions
- Experience library accepts SARs with quality score ≥ 70
- Prompt updates trigger when new patterns are detected

## Project Structure

```
SarActivityGenerator_Faiss/
│
├── api/                          # API Layer
│   ├── __init__.py
│   ├── auth.py                   # JWT authentication & password management
│   ├── middleware.py             # CORS, request logging, error handling
│   └── routes/
│       ├── __init__.py
│       ├── health.py             # Health check endpoints
│       ├── sar.py                # SAR generation & approval endpoints
│       └── feedback.py           # Learning metrics & patterns endpoints
│
├── config/                       # Configuration
│   └── settings.py               # App settings, paths, constants
│
├── data/                         # Data Storage
│   ├── vector_db/                # FAISS index files
│   └── raw/                      # Raw data files
│
├── database/                     # Database Layer
│   └── schema.py                 # SQLite schema definitions & initialization
│
├── frontend/                     # Web Interface
│   ├── __init__.py
│   └── app.py                    # Streamlit dashboard application
│
├── llm/                          # LLM Layer
│   ├── __init__.py
│   ├── loader.py                 # Model loading & management
│   └── generation_engine.py      # Text generation logic
│
├── models/                       # Data Models
│   └── *.py                      # Pydantic/dataclass models
│
├── rag/                          # RAG Pipeline
│   ├── __init__.py
│   └── pipeline.py               # Complete RAG implementation
│
├── services/                     # Business Logic (Track C)
│   ├── __init__.py
│   ├── feedback_collector.py     # Component 1: Feedback collection
│   ├── pattern_extractor.py      # Component 2: Pattern extraction
│   ├── experience_replay.py      # Component 3: Experience library
│   ├── prompt_updater.py         # Component 4: Dynamic prompts
│   ├── metrics_tracker.py        # Component 5: Metrics dashboard
│   └── continual_learning_engine.py  # Orchestrates all 5 components
│
├── utils/                        # Utilities
│   └── *.py                      # Helper functions
│
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (not tracked)
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git
- 8GB+ RAM recommended (for transformer models)
- GPU optional but recommended for faster inference

### Step 1: Clone the Repository

```bash
git clone https://github.com/TheDhruvBhalani/SarActivityGenerator_Faiss.git
cd SarActivityGenerator_Faiss
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** PyTorch installation may vary based on your system. Visit [pytorch.org](https://pytorch.org/get-started/locally/) for platform-specific instructions.

### Step 4: Configure Environment

Create a `.env` file in the project root:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DB_PATH=./data/sar_database.db

# Model Configuration
MODEL_NAME=your-model-name
USE_QUANTIZATION=True
```

### Step 5: Initialize Databases

Databases are automatically initialized on first run, or you can initialize manually:

```python
from database.schema import initialize_main_database, initialize_track_c_database
initialize_main_database()
initialize_track_c_database()
```

## Configuration

### Settings Overview

Configuration is managed in `config/settings.py`:

| Setting | Description | Default |
|---------|-------------|---------|
| `DB_PATH` | Main SQLite database path | `./data/sar.db` |
| `TRACK_C_DB_PATH` | Learning database path | `./data/track_c.db` |
| `VECTOR_DB_DIR` | FAISS index directory | `./data/vector_db` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |

### FAISS Index Setup

To build the FAISS index from your regulatory documents:

```python
from sentence_transformers import SentenceTransformer
import faiss

# Load embedder
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Embed your documents
documents = ["Your regulatory text...", ...]
embeddings = embedder.encode(documents)

# Create and save index
index = faiss.IndexFlatL2(384)
index.add(embeddings)
faiss.write_index(index, './data/vector_db/faiss_index.bin')
```

## Usage

### Starting the API Server

**Using uvicorn (recommended for development):**
```bash
uvicorn main:app --reload --port 8000
```

**Using Python directly:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Starting the Frontend Dashboard

```bash
streamlit run frontend/app.py
```

The dashboard will open at `http://localhost:8501`

### Generating a SAR

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/generate-sar" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALERT_001",
    "use_hybrid_search": true,
    "use_reranking": true
  }'
```

**Response:**
```json
{
  "generation_id": "GEN_20240912_001",
  "alert_id": "ALERT_001",
  "narrative": "Suspicious Activity Report...",
  "rag_context": { ... },
  "audit_trail": { ... }
}
```

### Approving a SAR with Feedback

```bash
curl -X POST "http://localhost:8000/api/v1/sar/GEN_20240912_001/approve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "edited_narrative": "Your edited narrative...",
    "analyst_id": "ANALYST_001",
    "approval_status": "APPROVED"
  }'
```

## API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Authenticate and receive JWT token |

### SAR Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/generate-sar` | POST | Generate a new SAR narrative |
| `/api/v1/sar/{id}/approve` | POST | Approve SAR with analyst edits |
| `/api/v1/logic-audit-trail/{id}` | GET | Retrieve generation audit trail |

### Learning & Metrics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/learning/metrics` | GET | Get learning performance metrics |
| `/api/v1/learning/patterns` | GET | List extracted correction patterns |
| `/api/v1/learning/prompt` | GET | Get current generation prompt |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check |
| `/` | GET | API root / welcome |

## Tech Stack

### Core Framework
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async API framework |
| **Streamlit** | Interactive web dashboard |
| **SQLite** | Embedded database for persistence |
| **Pydantic** | Data validation and serialization |

### Machine Learning
| Technology | Purpose |
|------------|---------|
| **PyTorch** | Deep learning framework |
| **Transformers** | Pre-trained language models |
| **Sentence Transformers** | Text embeddings |
| **FAISS** | Vector similarity search |
| **PEFT** | Parameter-efficient fine-tuning |
| **bitsandbytes** | Model quantization |

### Security
| Technology | Purpose |
|------------|---------|
| **python-jose** | JWT token handling |
| **passlib** | Password hashing (bcrypt) |

### Data Processing
| Technology | Purpose |
|------------|---------|
| **pandas** | Data manipulation |
| **numpy** | Numerical operations |

## Regulatory Compliance

This system is designed to generate SARs compliant with Indian financial regulations:

### PMLA (Prevention of Money Laundering Act)
- Section 12: Reporting obligations to FIU-IND
- Section 12AA: Enhanced due diligence requirements
- Rule 7: Record keeping requirements

### RBI Master Direction on KYC
- Customer Due Diligence (CDD) procedures
- Enhanced Due Diligence (EDD) for high-risk customers
- Ongoing monitoring requirements

### FIU-IND Guidelines
- STR (Suspicious Transaction Report) format
- Reporting timelines (7 working days)
- Quality standards for narratives

### FATF Recommendations
- Risk-based approach implementation
- Typology awareness (structuring, layering, integration)
- Red flag indicators

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

---

**Disclaimer:** This system is a tool to assist analysts and does not replace human judgment. All generated SARs must be reviewed by qualified compliance professionals before submission to regulatory authorities.
