# คู่มือการติดตั้งและใช้งานระบบ (Setup & User Guide)

คู่มือนี้สำหรับติดตั้งระบบรายงานประจำวันอัตโนมัติบน Windows 11

---

## 1. การติดตั้งฐานข้อมูล (PostgreSQL)

1. **ดาวน์โหลด:** ไปที่ [PostgreSQL Windows Downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads) และเลือกเวอร์ชันล่าสุด (เช่น 16 หรือ 17)
2. **การติดตั้ง:**
   - รันไฟล์ `.exe` ที่ดาวน์โหลดมา
   - ในขั้นตอน **Password**: ให้ตั้งรหัสผ่าน (เช่น `admin123`) และ **จดจำไว้**
   - ในขั้นตอน **Port**: ใช้ค่ามาตรฐาน `5432`
3. **สร้างฐานข้อมูล:**
   - เปิดโปรแกรม **pgAdmin 4** (ติดตั้งมาพร้อมกับ PostgreSQL)
   - คลิกขวาที่ **Databases** -> **Create** -> **Database...**
   - ใส่ชื่อฐานข้อมูลว่า: `daily_report_db` แล้วกด **Save**

---

## 2. การตั้งค่าสภาพแวดล้อม (Environment Setup)

1. **ไฟล์ .env:**
   - เปิดไฟล์ `.env` ใน VS Code
   - แก้ไขข้อมูลให้ตรงกับที่คุณตั้งค่าไว้:
     ```env
     DB_HOST=localhost
     DB_NAME=daily_report_db
     DB_USER=postgres
     DB_PASS=รหัสผ่านที่คุณตั้งตอนติดตั้ง
     DB_PORT=5432
     ```

2. **ไฟล์ config.yaml:**
   - ไฟล์นี้ใช้จัดการระบบ Login
   - หากต้องการเปลี่ยนรหัสผ่านเริ่มต้นของ `admin` ให้ใช้รหัสที่ผ่านการ Hash แล้ว (ในไฟล์ปัจจุบันเป็นค่าตัวอย่าง)

---

## 3. การเตรียม Library (ทำเพียงครั้งเดียว)

หากคุณยังไม่ได้ทำขั้นตอนที่ผมเตรียมไว้ให้ ให้เปิด Terminal ใน VS Code แล้วพิมพ์:

```powershell
# 1. สร้าง Virtual Environment
python -m venv venv

# 2. เปิดใช้งาน venv
.\venv\Scripts\activate

# 3. ติดตั้ง Library
pip install -r requirements.txt

# 4. ติดตั้ง Browser สำหรับ Playwright
playwright install chromium
```

---

## 4. การเริ่มใช้งานโปรแกรม (Starting the App)

ทุกครั้งที่ต้องการเริ่มใช้งาน ให้เปิด Terminal ใน VS Code และพิมพ์คำสั่งนี้:

```powershell
# 1. เปิดใช้งาน venv (ถ้ายังไม่ได้เปิด)
.\venv\Scripts\activate

# 2. รันโปรแกรม
streamlit run app.py
```

---

## 5. การตั้งค่าภายในแอป (ครั้งแรก)

เมื่อเปิดหน้าเว็บขึ้นมาแล้ว:
1. Login ด้วย username: `admin` (รหัสผ่านตามที่ตั้งใน config.yaml)
2. ไปที่เมนู **"ตั้งค่าส่วนตัว" (User Settings)**
3. กรอก **Gemini API Key** และ **Telegram Bot Token / Chat ID** ของคุณ
4. กด **บันทึก** เพื่อเริ่มทำรายงาน!

---

## โครงสร้างไฟล์สำคัญ
- `app.py`: ตัวโปรแกรมหลัก
- `database.py`: จัดการฐานข้อมูล
- `gemini_ai.py`: ระบบ AI แต่งบทความ
- `image_generator.py`: ระบบสร้างรูปภาพรายงาน
- `uploads/`: โฟลเดอร์เก็บรูปภาพที่อัปโหลดและรูปรายงานที่สร้างเสร็จ
