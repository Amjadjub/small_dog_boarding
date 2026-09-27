# פנסיון ביתי לכלבים קטנים — MVP

גרסה ראשונה עובדת של אתר RTL בעברית: אתר ציבורי וטופס בקשת אירוח ב־Next.js, API ואזור מנהלים ב־Django, ושמירה ב־PostgreSQL.

> כל התוכן העסקי והתמונה באתר מסומנים כתוכן המחשה. בקשה שנשלחה נשמרת כ־`pending` ואינה הזמנה מאושרת.

## דרישות

- Node.js 22+
- Python 3.12+
- Docker Desktop (עבור PostgreSQL)

## הרצה מקומית

1. מפעילים PostgreSQL:

   ```powershell
   docker compose up -d db
   ```

2. מכינים ומפעילים את השרת (PowerShell):

   ```powershell
   Copy-Item backend\.env.example backend\.env
   python -m venv backend\.venv
   backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
   backend\.venv\Scripts\python backend\manage.py migrate
   backend\.venv\Scripts\python backend\manage.py seed_admins
   backend\.venv\Scripts\python backend\manage.py runserver
   ```

3. בחלון נוסף מפעילים את הממשק:

   ```powershell
   Copy-Item frontend\.env.example frontend\.env.local
   cd frontend
   npm install
   npm run dev
   ```

4. פותחים [http://localhost:3000](http://localhost:3000). אזור המנהלים נמצא ב־`/admin/login`.

`seed_admins` דורש את `ADMIN_1_*` ו־`ADMIN_2_*` בקובץ `backend/.env`. יש לבחור שתי סיסמאות שונות וחזקות; ערכי הדוגמה אינם סיסמאות אמיתיות ולא יתקבלו.

## בדיקות ואיכות

```powershell
backend\.venv\Scripts\python backend\manage.py test
backend\.venv\Scripts\python -m ruff check backend
cd frontend
npm run lint
npm run build
```

## מבנה

- `frontend/` — Next.js, React ו־TypeScript
- `backend/` — Django, Django REST Framework ו־migrations
- `docs/` — ארכיטקטורה והחלטות הרחבה
- `docker-compose.yml` — PostgreSQL מקומי בלבד

אין במאגר מפתחות או סיסמאות. קובצי `.env` מקומיים מוחרגים מ־Git.
