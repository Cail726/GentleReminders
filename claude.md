# Project: Gentle Reminders - 大学生心理状态辅助评估系统
## Core Principle: 安全、稳定、可维护、不越界、按规范开发

---

## 1. 固定技术栈（禁止擅自更改）
### Backend
- Language: Python 3.11+
- Framework: FastAPI
- Database: SQLite (single file, stored in `/data`)
- ORM: SQLAlchemy
- API Style: RESTful, JSON format

### Frontend
- Language: HTML + CSS + Vanilla JavaScript
- Visualization: ECharts (only)
- No complex frameworks (React/Vue/Angular) unless explicitly approved
- All static files in `/static`, HTML in `/frontend`

### Data & Model
- Model: MSF-XGBoost (Multi-Source Feature Fusion + XGBoost)
- No medical/psychological diagnosis, only description and suggestions
- No user sensitive data storage beyond the project requirements

---

## 2. Development Rules (Must Follow)
### 2.1 项目结构（严格遵守，禁止随意新增文件）
GentleReminders/
├─ backend/      # FastAPI backend, APIs, DB logic
├─ frontend/     # HTML pages
├─ model/        # MSF-XGB model code
├─ data/         # SQLite database files
├─ static/       # images, css, icons
├─ docs/         # 文档中心 (课设/互联网+/大创原件)
├─ design-references/  # UI design concept references
└─ CLAUDE.md     # THIS RULE FILE

### 2.2 代码规范
- All filenames: English only, no Chinese, no spaces
- Python follows PEP8
- All front-end interactions use API
- All AI outputs: descriptive only, no judgment, no diagnosis

### 2.3 安全红线（绝对禁止）
- NO psychological diagnosis
- NO medical advice
- NO personal data exposed in admin panel
- NO sensitive information collection
- NO game mechanics, NO pressure, NO punishment

---

## 3. Core Modules (Must follow this order)
1. User system (register/login)
2. Emotion check-in & diary
3. Mental tree growth system
4. AI-generated unique message + letter (tree mature)
5. MSF-XGB assessment & trend charts
6. Admin dashboard (group statistics only)

---

## 4. AI Behavior Rule
You must:
- OBEY THIS FILE 100%
- NO free creation
- NO adding features I didn’t approve
- NO changing tech stack
- NO adding libraries without notice