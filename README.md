# Daily Report Automation System

ระบบรายงานประจำวันอัตโนมัติ (Daily Report Automation System) พัฒนาด้วย Streamlit, PostgreSQL, Gemini AI และ Playwright

## การติดตั้ง (Installation)

1. **ติดตั้ง Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **ติดตั้ง Playwright Browser:**
   ```bash
   playwright install chromium
   ```

3. **ตั้งค่าฐานข้อมูล (PostgreSQL):**
   - สร้างฐานข้อมูลชื่อ `daily_report_db`
   - แก้ไขไฟล์ `.env` (คัดลอกมาจาก `.env.example`) เพื่อระบุข้อมูลการเชื่อมต่อ

4. **ตั้งค่าเริ่มต้น (First Run):**
   - ระบบจะสร้างตารางในฐานข้อมูลให้โดยอัตโนมัติเมื่อรันครั้งแรก
   - แก้ไข `config.yaml` เพื่อเพิ่มผู้ใช้งานเริ่มต้น

## การรันระบบ (Running the App)

```bash
streamlit run app.py
```

## โครงสร้างระบบ
- `app.py`: หน้าจอหลักของระบบ
- `database.py`: จัดการข้อมูลใน PostgreSQL
- `gemini_ai.py`: เชื่อมต่อ Gemini API
- `image_generator.py`: สร้างภาพรายงาน PNG (800x1150px)
- `telegram_bot.py`: ส่งรายงานเข้ากลุ่ม Telegram
