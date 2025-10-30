# HNG13 Task | Stage 2 | Backend | Country Currency & Exchange API (FastAPI)

A RESTful API that fetches countries from **restcountries.com**, matches currencies with exchange rates from **open.er-api.com**, computes an **estimated_gdp**, caches data in a MySQL database, and provides CRUD + image summary.



## Requirements
- Python 3.10+
- MySQL server


This project was built as part of the **HNG13 Internship — Stage 2 Backend Task**.

---

## 🚀 Features

- Fetches all countries from restcountries.com

- Retrieves live exchange rates from open.er-api.com

- Computes **estimated_gdp** = **population** × **random(1000–2000)** ÷ **exchange_rate**

- Stores and updates data in MySQL as cached records

- Generates an image summary (cache/summary.png) after refresh

- Provides filters, sorting, and CRUD endpoints

- Handles API and DB errors gracefully

- Deployed easily on **Railway**


---
## 💻 Tech Stack

- `Backend:` FastAPI

- `Language:` Python

- `HTTP Client:` requests

- `Environment Management:` python-dotenv

- `Deployment:` Railway

---

## 🧩 API Endpoints

| Method | Endpoint | Description |
|:-------|:----------|:-------------|
| **POST** | `/countries/refresh` | fetch external data & cache to DB (and generate cache/summary.png) |
| **GET** | `/countries` | list cached countries (filters: region, currency; sort: gdp_desc or gdp_asc) |
| **GET** | `/countries/{name}` | get one country |
| **GET** | `/status` | total countries + last refresh time |
| **GET** | `/countries/image` | serve generated summary image |
| **DELETE** | `/countries/{name}` | delete a country |

---

### ✅ Example Request — Create / Analyze String

**POST** `/countries/refresh`

### Example Response
```json
{
    "status": "success",
    "total_countries": 250,
    "last_refreshed_at": "2025-10-26T15:56:10.495906+00:00"
}
```
```

### ✅ Example Request — Filter Countries

**GET** `/countries?region=Africa`


### Example Response
```json
[
  {
    "id": 1,
    "name": "Nigeria",
    "capital": "Abuja",
    "region": "Africa",
    "population": 206139589,
    "currency_code": "NGN",
    "exchange_rate": 1600.23,
    "estimated_gdp": 25767448125.2,
    "flag_url": "https://flagcdn.com/ng.svg",
    "last_refreshed_at": "2025-10-22T18:00:00Z"
  }
]

 


```
---
## Step 1: Install MySQL on Windows
- Use MySQL Installer (Recommended)

Go to the official site:
👉 https://dev.mysql.com/downloads/installer/

Download MySQL Installer for Windows (either Full or Web version)

Run the installer and select:

✅ MySQL Server

🧩 MySQL Workbench (optional GUI)

🖥️ MySQL Shell (optional CLI)

Proceed with installation

## Step 2: Configure MySQL Server

During setup:

Choose Standalone MySQL Server / Classic Configuration

Set your root password (example: mypassword)

Leave the default port: 3306

📝 Note these:

Username: root
Password: (whatever you set)
Port: 3306

## Step 3: Verify Installation

- After installation, open Command Prompt or PowerShell and run:

 - mysql -u root -p


- Enter your password.
 - If successful, you’ll see:
 - mysql>


Type exit; to quit.

🧱 Step 4: Create the Database

Log back in:

mysql -u root -p


Then create your database:

CREATE DATABASE country_api;


Confirm it exists:

SHOW DATABASES;

---
## Create a .env file
- Create a .env file in the project root:
```bash
cp .env.example .env

```
## ⚙️ Environment variables
- Then edit .env with your preferred database connection string.
```env
# Format: mysql+pymysql://<user>:<password>@<host>:<port>/<database>
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/country_api



```
## Cloning the repository
```bash
git clone https://github.com/danielzfega/hng13-country-api-fastapi
cd hng13-country-api-fastapi


```
## Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate     # On macOS/Linux
venv\Scripts\activate        # On Windows


```
## List of dependencies - Sample requirements.txt
```txt
fastapi==0.115.0
uvicorn==0.30.0
sqlalchemy==2.0.43
psycopg[binary]==3.2.3
httpx
Pillow
pymysql
pydantic==2.8.2
python-dotenv==1.0.1
alembic==1.11.1


```
## Install dependencies
```bash
pip install -r requirements.txt


```
## Start the development server
```bash
uvicorn main:app --reload


```
## Live access to endpoint at
```bash
https://hng13-profile-api-django-production.up.railway.app/me
