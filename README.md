# 🏥 Clinical KAP Dashboard: Menopause & HRT

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![Next.js](https://img.shields.io/badge/Next.js-15.0+-black.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)

## 📖 Overview

A full-stack, research-grade web application built to dynamically automate the Knowledge, Attitudes, and Practices (KAP) statistical analysis pipeline for the clinical study: **"Knowledge and Attitudes of Menopause and Hormone Replacement Therapy Among Perimenopausal and Postmenopausal Women in Ibadan, Nigeria"**.

This application modernizes traditional statistical workflows (e.g., SPSS/Stata) by combining a high-fidelity Python statistical engine (FastAPI/Pandas/SciPy) with a fully interactive React (Next.js) data visualization dashboard. It allows researchers to upload raw `.xlsx` survey datasets, instantly compute complex psychometrics, heavily validate inferential statistics, and securely download publication-ready analytical reports.

## ✨ Key Features

- **Automated Data Cleaning**: Automatically filters out non-consenting participants and validates raw uploads in memory.
- **Advanced Psychometric Scoring Engine**:
  - Dynamically splits Knowledge and Attitudes into 4 distinct clinical constructs (Menopause Knowledge, HRT Knowledge, Menopause Attitude, HRT Attitude).
  - Intelligently handles complex, multi-select questions (e.g. converting 12-item lists into weighted scores).
  - Handles filter-question skips (e.g., scoring unattempted sections with 0 or reverting to baseline without destroying the denominator $n$).
  - Internally calculates reliability matrixes (Cronbach's Alpha $\alpha$) ensuring survey consistency.
- **Rigorous Inferential Statistics**:
  - Dynamically calculates Pearson's Chi-Square ($\chi^2$) tests of independence mapping demographics to categorical outcomes.
  - Features an **autonomous exact test fallback**: If sparse data causes expected frequencies to drop below 5 in >20% of cross-tabs, the engine automatically defers to **Fisher's Exact Test** utilizing a 9,999-iteration Monte Carlo permutation simulation via `SciPy`.
- **Interactive UI/UX**: A modern, glass-morphic React dashboard featuring multi-axis D3 charts, custom parent-child nested statistical tables, and live data cards.
- **Zero Disk I/O**: Performs all data crunching and Excel compilation entirely in RAM (Memory Buffers) for maximum speed and data privacy.

---

## 🛠 Technology Stack

### Backend (Analytical Engine)

- **Language:** Python
- **Framework:** FastAPI / Uvicorn
- **Data Science:** Pandas, NumPy
- **Statistics:** SciPy 1.15.2
- **I/O:** Openpyxl, python-multipart

### Frontend (User Interface)

- **Language:** TypeScript
- **Framework:** Next.js (React)
- **Styling:** Tailwind CSS, Lucide Icons, Shadcn UI
- **Visualization:** Recharts
- **State Management:** React Hook Form, Axios

---

## 🚀 Quick Start & Reproducibility

This repository requires two terminal instances to run correctly in a local environment. Ensure you have `Node.js` (for `npm`/`pnpm`) and `Python 3.10+` installed on your machine.

### 1. Start the Backend API

Navigate to the `backend` directory, activate your virtual environment, install the dependencies, and start the Uvicorn server:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

_The statistical engine will now be listening locally at `http://localhost:8000`._

### 2. Start the Frontend Dashboard

Open a new terminal, navigate to the `frontend` directory, install packages, and launch the development server:

```bash
cd frontend
pnpm install  # Or npm install / yarn
pnpm run dev
```

_The interactive dashboard will now be accessible in your browser at `http://localhost:3000`._

---

## 📊 Analytical Pipeline Methodology

1.  **Ingestion:** The FastAPI server securely ingests target `.xlsx` files exclusively into an in-memory buffer.
2.  **Imputation & Cleaning:** Columns are normalized, and missing critical sociodemographic variables undergo proportional stochastic imputation to preserve natural cohort variance without inflating modes.
3.  **Construct Bounding:** Raw Likert scales and boolean test arrays are evaluated. Missing sections (due to legacy forms or skipped filter questions) are safely imputed with minimal mathematical baselines to anchor the dataset ($n=239$).
4.  **Descriptive Evaluation:** Individual performance is dynamically matched against the specific cohort Mean to categorize outcomes as strictly "Good/Poor" or "Positive/Negative".
5.  **Inferential Execution:** P-values are synthesized using dynamically evaluated Chi-Square algorithms and Fisher exact testing logic depending on expected cell densities.
6.  **Report Generation:** A comprehensive 8-sheet Excel file (`results_output.xlsx`), including deep cross-tabulations and itemized Cronbach's Alpha scores, is passed back to the frontend.

## 📄 License

This clinical tool is open-sourced software licensed under the **MIT License**.
