import google.generativeai as genai
import os

def generate_report_content(api_key, system_instruction, title, keywords):
    if not api_key:
        return "Error: Gemini API Key not configured."
    
    try:
        genai.configure(api_key=api_key)
        
        # Default instruction if none provided
        if not system_instruction:
            system_instruction = "คุณเป็นเจ้าหน้าที่ประชาสัมพันธ์ของหน่วยงานตรวจคนเข้าเมือง ให้ช่วยเขียนบทความข่าวประชาสัมพันธ์ภาษาไทยจากหัวข้อและคำสำคัญที่ให้มา โดยใช้ภาษาที่เป็นทางการ สละสลวย และถูกต้องตามหลักภาษาไทย"
            
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction
        )
        
        prompt = f"หัวเรื่อง: {title}\nคำสำคัญ: {keywords}\n\nกรุณาแต่งบทความสรุปเหตุการณ์สำหรับรายงานประจำวัน:"
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating content: {e}"
