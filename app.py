import streamlit as st
import streamlit.components.v1 as components
from streamlit_quill import st_quill
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from database import init_db, get_user_by_username, create_user, get_user_settings, update_user_settings, create_report, get_reports, get_report_by_id, update_report, get_reports_count, get_all_users, update_user_role, delete_user, update_admin_role_if_needed
from gemini_ai import generate_report_content
from image_generator import run_generate_image, generate_html_preview
from telegram_bot import send_telegram_report
import os
import base64
from datetime import datetime
from dotenv import load_dotenv
import json
import bcrypt
import re

STYLE_FILE = "style_defaults.json"

def load_style_defaults():
    default_template = {
        "header_text": "ตม.จว.นครศรีธรรมราช",
        "header_font": "TH Sarabun IT 9",
        "header_size": 38,
        "header_color": "#ffffff",
        "header_bg_color": "#00af50",
        "header_bg_transparent": False,
        "header_pos_y": 15,
        "header_align": "กลาง",
        "header_height": 125,
        "header_pad_l": 0,
        "header_pad_r": 0,
        "header_border_shape": "สี่เหลี่ยม",
        "title_font": "TH Sarabun IT 9",
        "title_size": 40,
        "title_color": "#ffffff",
        "title_bg_color": "#00af50",
        "title_bg_transparent": False,
        "title_pos_y": 150,
        "title_align": "กลาง",
        "title_height": 109,
        "title_pad_l": 0,
        "title_pad_r": 0,
        "title_border_shape": "สี่เหลี่ยม",
        "image_width": 538,
        "image_height": 397,
        "image_pos_x": 94,
        "image_pos_y": 282,
        "image_border_color": "#00af50",
        "image_border_width": 6,
        "image_border_shape": "ขอบโค้ง",
        "font_family": "TH Sarabun IT 9",
        "font_size": 14,
        "content_text_color": "#ffffff",
        "content_bg_color": "#141414",
        "content_bg_opacity": 5,
        "content_border_color": "#ffffff",
        "content_border_width": 0,
        "content_border_opacity": 0,
        "content_border_shape": "ขอบโค้ง"
    }
    if os.path.exists(STYLE_FILE):
        try:
            with open(STYLE_FILE, "r", encoding="utf-8") as f:
                saved_template = json.load(f)
                # Merge saved settings on top of default template
                for k, v in saved_template.items():
                    default_template[k] = v
                return default_template
        except:
            pass
    return default_template

def save_style_defaults(defaults):
    with open(STYLE_FILE, "w", encoding="utf-8") as f:
        json.dump(defaults, f, ensure_ascii=False, indent=4)

def save_config(cfg):
    with open('config.yaml', 'w') as file:
        yaml.dump(cfg, file, default_flow_style=False)

load_dotenv()

# Page config
st.set_page_config(page_title="Daily Report Automation", layout="wide")

# Initialize DB
init_db()

# Load authenticator config
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login
authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
username = st.session_state.get('username')
name = st.session_state.get('name')

if authentication_status:
    user_data = get_user_by_username(username)
    if not user_data:
        # Create user in DB if exists in config but not in DB
        user_id = create_user(username, "password_not_stored_here", name)
        user_data = get_user_by_username(username)
    
    update_admin_role_if_needed(username)
    user_data = get_user_by_username(username)
    
    user_id = user_data['id']
    user_role = user_data['role']
    
    # Sidebar Navigation
    st.sidebar.markdown("### 📌 เมนูหลัก")
    menu_options = ["📝 ทำรายงานใหม่", "⚙️ ตั้งค่ารูปแบบเทมเพลต", "🗂️ ประวัติรายงาน", "👤 ตั้งค่าส่วนตัว"]
    if user_role == 'admin':
        menu_options.append("👥 จัดการผู้ใช้งาน")
        
    menu = st.sidebar.radio("", menu_options)
    
    st.sidebar.markdown("---")
    authenticator.logout('🚪 ออกจากระบบ', 'sidebar')
    
    if menu == "📝 ทำรายงานใหม่":
        st.header("📝 ทำรายงานประจำวันใหม่")
        
        settings = get_user_settings(user_id)
        
        style_defaults = load_style_defaults()
        def get_def(key, default_val):
            return style_defaults.get(key, default_val)
        
        if 'report_content' not in st.session_state:
            st.session_state['report_content'] = ""

        left_col, right_col = st.columns([1.2, 1])
        with left_col:
            with st.container(border=True):
                st.markdown("#### 📄 ข้อมูลรายงาน")
                report_date = st.date_input("วันที่", datetime.now())
                title_text = st.text_input("หัวข้อกิจกรรม", value="", placeholder="เช่น การตรวจสอบสถานประกอบการ...")
            
            with st.container(border=True):
                st.markdown("#### 🖼️ รูปภาพประกอบ")
                uploaded_files = st.file_uploader("อัปโหลดรูปภาพกิจกรรม (สูงสุด 4 รูป)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            
            with st.container(border=True):
                st.markdown("#### ✍️ เนื้อหารายงาน")
                keywords = st.text_area("คำสำคัญ/รายละเอียดเพิ่มเติม (สำหรับให้ AI ช่วยเขียน)", placeholder="ใส่รายละเอียดสั้นๆ เพื่อให้ AI แต่งบทความ...")
                generate_ai = st.button("🤖 ให้ AI ช่วยแต่งเนื้อหา (คลิกหลังจากพิมพ์คำสำคัญเสร็จ)")
                st.markdown("---")
                content = st_quill(value=st.session_state['report_content'], placeholder="เนื้อหารายงาน...", html=True)
        
            submit_btn = st.button("💾 บันทึกและสร้างภาพรายงาน", type="primary", use_container_width=True)

            if generate_ai:
                if not title_text or not keywords:
                    st.warning("กรุณากรอกหัวข้อและคำสำคัญก่อน")
                else:
                    with st.spinner("กำลังให้ AI แต่งเนื้อหา..."):
                        settings = get_user_settings(user_id)
                        content_generated = generate_report_content(
                            settings.get('gemini_api_key', ''),
                            settings.get('ai_system_instruction', ''),
                            title_text,
                            keywords
                        )
                        st.session_state['report_content'] = content_generated
                        st.rerun()
            elif submit_btn:
                with st.spinner("กำลังบันทึกและสร้างภาพ..."):
                    # Save files
                    image_paths = []
                    for i, file in enumerate(uploaded_files[:4]):
                        path = f"uploads/{user_id}_{datetime.now().timestamp()}_{i}.jpg"
                        with open(path, "wb") as f:
                            f.write(file.getbuffer())
                        image_paths.append(path)
                    
                    # Create report in DB
                    report_id = create_report(user_id, report_date, get_def("header_text", "ตม.จว.นครศรีธรรมราช"), title_text, content, image_paths, get_def("font_family", "TH Sarabun IT 9"), get_def("font_size", 19))
                    
                    if report_id:
                        # Generate Image
                        output_image = f"uploads/report_{report_id}.png"
                        img_data = {
                            'header_text': get_def("header_text", "ตม.จว.นครศรีธรรมราช"),
                            'header_font': get_def("header_font", "TH Sarabun IT 9"),
                            'header_size': get_def("header_size", 32),
                            'header_color': get_def("header_color", "#1a5d1a"),
                            'header_bg_color': 'transparent' if get_def("header_bg_transparent", True) else get_def("header_bg_color", "#ffffff"),
                            'header_pos_y': get_def("header_pos_y", 40),
                            'header_align': get_def("header_align", "กลาง"),
                            'header_height': get_def("header_height", 40),
                            'header_pad_l': get_def("header_pad_l", 20),
                            'header_pad_r': get_def("header_pad_r", 20),
                            'header_border_shape': get_def("header_border_shape", "ขอบโค้ง"),
                            
                            'title_text': title_text,
                            'title_font': get_def("title_font", "TH Sarabun IT 9"),
                            'title_size': get_def("title_size", 28),
                            'title_color': get_def("title_color", "#1a5d1a"),
                            'title_bg_color': 'transparent' if get_def("title_bg_transparent", True) else get_def("title_bg_color", "#ffffff"),
                            'title_pos_y': get_def("title_pos_y", 150),
                            'title_align': get_def("title_align", "ซ้าย"),
                            'title_height': get_def("title_height", 40),
                            'title_pad_l': get_def("title_pad_l", 10),
                            'title_pad_r': get_def("title_pad_r", 10),
                            'title_border_shape': get_def("title_border_shape", "ขอบโค้ง"),
                            
                            'image_width': get_def("image_width", 620),
                            'image_height': get_def("image_height", 250),
                            'image_pos_x': get_def("image_pos_x", 50),
                            'image_pos_y': get_def("image_pos_y", 250),
                            'image_border_color': get_def("image_border_color", "#1a5d1a"),
                            'image_border_width': get_def("image_border_width", 3),
                            'image_border_shape': get_def("image_border_shape", "ขอบโค้ง"),
                            
                            'content': content,
                            'content_bg_color': get_def("content_bg_color", "#ffffff"),
                            'content_bg_opacity': get_def("content_bg_opacity", 0),
                            'content_border_color': get_def("content_border_color", "#cccccc"),
                            'content_border_width': get_def("content_border_width", 0),
                            'content_border_opacity': get_def("content_border_opacity", 100),
                            'content_border_shape': get_def("content_border_shape", "ขอบโค้ง"),
                            'content_text_color': get_def("content_text_color", "#333333"),
                            
                            'report_date': report_date.strftime("%d/%m/%Y"),
                            'images': image_paths,
                            'font_family': get_def("font_family", "TH Sarabun IT 9"),
                            'font_size': get_def("font_size", 19)
                        }
                        run_generate_image(img_data, output_image)
                        
                        st.success("บันทึกรายงานสำเร็จ!")
                        st.image(output_image, caption="ภาพรายงานที่สร้างขึ้น", use_container_width=True)
                        
                        # Download Button
                        with open(output_image, "rb") as file:
                            st.download_button(
                                label="📥 ดาวน์โหลดรูปภาพรายงาน (PNG)",
                                data=file,
                                file_name=f"daily_report_{report_id}.png",
                                mime="image/png"
                            )
                        
                        # Telegram Notification
                        if st.button("🚀 ส่งเข้า Telegram ทันที"):
                            success, msg = send_telegram_report(
                                settings['telegram_bot_token'],
                                settings['telegram_chat_id'],
                                output_image,
                                f"รายงานประจำวัน: {title_text}"
                            )
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                                
                        st.markdown("---")
                        if st.button("✨ เริ่มทำรายงานใหม่", type="secondary", use_container_width=True):
                            st.session_state['report_content'] = ""
                            st.rerun()
    

        with right_col:
            st.subheader("👁️ ภาพตัวอย่าง (Realtime Preview)")
            
            preview_base64_images = []
            if uploaded_files:
                for file in uploaded_files[:4]:
                    preview_base64_images.append(base64.b64encode(file.getvalue()).decode('utf-8'))
            
            preview_data = {
                'header_text': get_def("header_text", "ตม.จว.นครศรีธรรมราช"),
                'header_font': get_def("header_font", "TH Sarabun IT 9"),
                'header_size': get_def("header_size", 32),
                'header_color': get_def("header_color", "#1a5d1a"),
                'header_bg_color': get_def("header_bg_color", "#ffffff"),
                'header_bg_transparent': get_def("header_bg_transparent", True),
                'header_pos_y': get_def("header_pos_y", 40),
                'header_align': get_def("header_align", "กลาง"),
                'header_height': get_def("header_height", 40),
                'header_pad_l': get_def("header_pad_l", 20),
                'header_pad_r': get_def("header_pad_r", 20),
                'header_border_shape': get_def("header_border_shape", "ขอบโค้ง"),
                
                'title_text': title_text if title_text else "หัวข้อกิจกรรม (ตัวอย่าง)",
                'title_font': get_def("title_font", "TH Sarabun IT 9"),
                'title_size': get_def("title_size", 28),
                'title_color': get_def("title_color", "#1a5d1a"),
                'title_bg_color': 'transparent' if get_def("title_bg_transparent", True) else get_def("title_bg_color", "#ffffff"),
                'title_bg_transparent': get_def("title_bg_transparent", True),
                'title_pos_y': get_def("title_pos_y", 150),
                'title_align': get_def("title_align", "ซ้าย"),
                'title_height': get_def("title_height", 40),
                'title_pad_l': get_def("title_pad_l", 10),
                'title_pad_r': get_def("title_pad_r", 10),
                'title_border_shape': get_def("title_border_shape", "ขอบโค้ง"),
                
                'image_width': get_def("image_width", 620),
                'image_height': get_def("image_height", 250),
                'image_pos_x': get_def("image_pos_x", 50),
                'image_pos_y': get_def("image_pos_y", 250),
                'image_border_color': get_def("image_border_color", "#1a5d1a"),
                'image_border_width': get_def("image_border_width", 3),
                'image_border_shape': get_def("image_border_shape", "ขอบโค้ง"),
                
                'content': content if content else "<p>เนื้อหารายงานตัวอย่าง...</p>",
                'content_bg_color': get_def("content_bg_color", "#ffffff"),
                'content_bg_opacity': get_def("content_bg_opacity", 0),
                'content_border_color': get_def("content_border_color", "#cccccc"),
                'content_border_width': get_def("content_border_width", 0),
                'content_border_opacity': get_def("content_border_opacity", 100),
                'content_border_shape': get_def("content_border_shape", "ขอบโค้ง"),
                'content_text_color': get_def("content_text_color", "#333333"),
                
                'report_date': report_date.strftime("%d/%m/%Y"),
                'preview_images_base64': preview_base64_images,
                'font_family': get_def("font_family", "TH Sarabun IT 9"),
                'font_size': get_def("font_size", 19),
                
                'header_image_path': 'templates/default_header.png',
                'footer_image_path': 'templates/default_footer.png',
                'bg_image_path': 'templates/img_template.png'
            }
            
            html_preview = generate_html_preview(preview_data)
            
            # Inject CSS to scale the body directly inside the HTML document
            scale_css = """
            <style>
                html {
                    display: flex;
                    justify-content: center;
                    background-color: #f0f2f6;
                    height: 676px;
                    overflow: hidden;
                }
                body {
                    transform: scale(0.65);
                    transform-origin: top center;
                    margin: 0;
                    min-width: 720px !important;
                    min-height: 1040px !important;
                    flex-shrink: 0;
                }
            </style>
            """
            scaled_html = html_preview.replace('</head>', f'{scale_css}</head>')
            
            components.html(scaled_html, height=680)

    elif menu == "⚙️ ตั้งค่ารูปแบบเทมเพลต":
        st.header("⚙️ ตั้งค่ารูปแบบเทมเพลต (Template Settings)")
        
        style_defaults = load_style_defaults()
        def get_def(key, default_val):
            return style_defaults.get(key, default_val)

        left_col, right_col = st.columns([1.2, 1])
        with left_col:
            with st.form("template_settings_form"):
                header_text = st.text_input("ชื่อหน่วยงาน (ป้ายส่วนหัว)", value=get_def("header_text", "ตม.จว.นครศรีธรรมราช"))
                
                tab1, tab2, tab3, tab4 = st.tabs(["🏷️ ป้ายส่วนหัว", "📝 หัวข้อกิจกรรม", "🖼️ รูปภาพ", "📄 เนื้อหา"])
                
                fonts = ["TH Sarabun IT 9", "Arial", "Courier New", "Tahoma"]
                shape_opts = ["ขอบโค้ง", "สี่เหลี่ยม"]
                align_opts = ["ซ้าย", "กลาง", "ขวา"]
                
                with tab1:
                    hc1, hc2, hc3, hc4 = st.columns(4)
                    with hc1:
                        h_font_val = get_def("header_font", "TH Sarabun IT 9")
                        h_idx = fonts.index(h_font_val) if h_font_val in fonts else 0
                        header_font = st.selectbox("ฟอนต์", fonts, index=h_idx, key="hf")
                    with hc2:
                        header_size = st.number_input("ขนาด", min_value=10, max_value=100, value=get_def("header_size", 32), key="hs")
                    with hc3:
                        header_color = st.color_picker("สีอักษร", value=get_def("header_color", "#1a5d1a"), key="hc")
                    with hc4:
                        header_bg_color = st.color_picker("สีพื้นหลัง", value=get_def("header_bg_color", "#ffffff"), key="hbg")
                        header_bg_transparent = st.checkbox("โปร่งใส (ป้ายส่วนหัว)", value=get_def("header_bg_transparent", True), key="hbgt")
                
                    st.markdown("---")
                    hc_size1, hc_size2, hc_size3 = st.columns(3)
                    with hc_size1:
                        header_height = st.slider("ความสูงพื้นหลัง", 20, 150, get_def("header_height", 40), key="hh")
                    with hc_size2:
                        header_pad_l = st.slider("ระยะห่างจากขอบซ้าย", 0, 300, get_def("header_pad_l", 20), key="hpl")
                    with hc_size3:
                        header_pad_r = st.slider("ระยะห่างจากขอบขวา", 0, 300, get_def("header_pad_r", 20), key="hpr")
                    
                    hc_pos1, hc_pos2, hc_pos3 = st.columns(3)
                    with hc_pos1:
                        header_pos_y = st.slider("เลื่อนตำแหน่งแนวตั้ง (ขึ้น-ลง)", min_value=0, max_value=300, value=get_def("header_pos_y", 40), key="hpy")
                    with hc_pos2:
                        h_align_val = get_def("header_align", "กลาง")
                        h_align_idx = align_opts.index(h_align_val) if h_align_val in align_opts else 1
                        header_align = st.radio("จัดตำแหน่งแนวนอน", align_opts, index=h_align_idx, horizontal=True, key="halign")
                    with hc_pos3:
                        h_shape_val = get_def("header_border_shape", "ขอบโค้ง")
                        h_shape_idx = shape_opts.index(h_shape_val) if h_shape_val in shape_opts else 0
                        header_border_shape = st.radio("รูปทรงกรอบส่วนหัว", shape_opts, index=h_shape_idx, horizontal=True, key="hshape")

                with tab2:
                    tc1, tc2, tc3, tc4 = st.columns(4)
                    with tc1:
                        t_font_val = get_def("title_font", "TH Sarabun IT 9")
                        t_idx = fonts.index(t_font_val) if t_font_val in fonts else 0
                        title_font = st.selectbox("ฟอนต์หัวข้อ", fonts, index=t_idx, key="tf")
                    with tc2:
                        title_size = st.number_input("ขนาดหัวข้อ", min_value=10, max_value=100, value=get_def("title_size", 28), key="ts")
                    with tc3:
                        title_color = st.color_picker("สีอักษรหัวข้อ", value=get_def("title_color", "#1a5d1a"), key="tc")
                    with tc4:
                        title_bg_color = st.color_picker("สีพื้นหลังหัวข้อ", value=get_def("title_bg_color", "#ffffff"), key="tbg")
                        title_bg_transparent = st.checkbox("โปร่งใส (หัวข้อกิจกรรม)", value=get_def("title_bg_transparent", True), key="tbgt")
                    
                    st.markdown("---")
                    tc_size1, tc_size2, tc_size3 = st.columns(3)
                    with tc_size1:
                        title_height = st.slider("ความสูงพื้นหลัง (หัวข้อกิจกรรม)", 20, 150, get_def("title_height", 40), key="th")
                    with tc_size2:
                        title_pad_l = st.slider("ระยะห่างหัวข้อจากขอบซ้าย", 0, 300, get_def("title_pad_l", 10), key="tpl")
                    with tc_size3:
                        title_pad_r = st.slider("ระยะห่างหัวข้อจากขอบขวา", 0, 300, get_def("title_pad_r", 10), key="tpr")
                    
                    tc_pos1, tc_pos2, tc_pos3 = st.columns(3)
                    with tc_pos1:
                        title_pos_y = st.slider("เลื่อนตำแหน่งหัวข้อแนวตั้ง (ขึ้น-ลง)", min_value=0, max_value=400, value=get_def("title_pos_y", 150), key="tpy")
                    with tc_pos2:
                        t_align_val = get_def("title_align", "ซ้าย")
                        t_align_idx = align_opts.index(t_align_val) if t_align_val in align_opts else 0
                        title_align = st.radio("จัดตำแหน่งแนวนอนหัวข้อ", align_opts, index=t_align_idx, horizontal=True, key="talign")
                    with tc_pos3:
                        t_shape_val = get_def("title_border_shape", "ขอบโค้ง")
                        t_shape_idx = shape_opts.index(t_shape_val) if t_shape_val in shape_opts else 0
                        title_border_shape = st.radio("รูปทรงกรอบหัวข้อ", shape_opts, index=t_shape_idx, horizontal=True, key="tshape")
            
                with tab3:
                    ic_size1, ic_size2 = st.columns(2)
                    with ic_size1:
                        image_width = st.slider("ความกว้างกรอบรูปภาพ", min_value=100, max_value=720, value=get_def("image_width", 620), key="iw")
                    with ic_size2:
                        image_height = st.slider("ความสูงรูปภาพ (px)", min_value=100, max_value=600, value=get_def("image_height", 250), key="ih")
                    
                    ic_pos1, ic_pos2 = st.columns(2)
                    with ic_pos1:
                        image_pos_x = st.slider("เลื่อนตำแหน่งแนวนอน (ซ้าย-ขวา)", min_value=0, max_value=720, value=get_def("image_pos_x", 50), key="ipx")
                    with ic_pos2:
                        image_pos_y = st.slider("เลื่อนตำแหน่งแนวตั้ง (ขึ้น-ลง)", min_value=0, max_value=800, value=get_def("image_pos_y", 250), key="ipy")
                    
                    st.markdown("---")
                    ic1, ic2, ic3 = st.columns(3)
                    with ic1:
                        image_border_color = st.color_picker("สีของกรอบรูป", value=get_def("image_border_color", "#1a5d1a"), key="ibc")
                    with ic2:
                        image_border_width = st.number_input("ความหนากรอบรูป", min_value=0, max_value=20, value=get_def("image_border_width", 3), key="ibw")
                    with ic3:
                        i_shape_val = get_def("image_border_shape", "ขอบโค้ง")
                        i_shape_idx = shape_opts.index(i_shape_val) if i_shape_val in shape_opts else 0
                        image_border_shape = st.radio("รูปทรงกรอบรูป", shape_opts, index=i_shape_idx, horizontal=True, key="ishape")
            
                with tab4:
                    cc1, cc2, cc3 = st.columns(3)
                    with cc1:
                        c_font_val = get_def("font_family", "TH Sarabun IT 9")
                        c_idx = fonts.index(c_font_val) if c_font_val in fonts else 0
                        font_family = st.selectbox("ฟอนต์เนื้อหา", fonts, index=c_idx, key="cf")
                    with cc2:
                        font_size = st.slider("ขนาดฟอนต์เนื้อหา (px)", 14, 30, get_def("font_size", 19), key="cs")
                    with cc3:
                        content_text_color = st.color_picker("สีอักษรเนื้อหา", value=get_def("content_text_color", "#333333"), key="ctc")
                    
                    cc4, cc5, cc6 = st.columns(3)
                    with cc4:
                        content_bg_color = st.color_picker("สีพื้นหลังเนื้อหา", value=get_def("content_bg_color", "#ffffff"), key="cbg")
                        content_bg_opacity = st.slider("ความโปร่งแสงพื้นหลัง (%)", 0, 100, get_def("content_bg_opacity", 0), key="cbo")
                    with cc5:
                        content_border_color = st.color_picker("สีขอบเนื้อหา", value=get_def("content_border_color", "#cccccc"), key="cbc")
                        content_border_opacity = st.slider("ความโปร่งแสงขอบ (%)", 0, 100, get_def("content_border_opacity", 100), key="cbo2")
                    with cc6:
                        content_border_width = st.number_input("ความหนาขอบเนื้อหา", min_value=0, max_value=20, value=get_def("content_border_width", 0), key="cbw")
                        c_shape_val = get_def("content_border_shape", "ขอบโค้ง")
                        c_shape_idx = shape_opts.index(c_shape_val) if c_shape_val in shape_opts else 0
                        content_border_shape = st.radio("รูปทรงกรอบเนื้อหา", shape_opts, index=c_shape_idx, horizontal=True, key="cshape")
                
                submitted = st.form_submit_button("🔄 อัปเดตภาพตัวอย่าง & บันทึกเทมเพลต", type="primary", use_container_width=True)
            
            if submitted:
                save_style_defaults({
                    "header_text": header_text,
                    "header_font": header_font,
                    "header_size": header_size,
                    "header_color": header_color,
                    "header_bg_color": header_bg_color,
                    "header_bg_transparent": header_bg_transparent,
                    "header_pos_y": header_pos_y,
                    "header_align": header_align,
                    "header_height": header_height,
                    "header_pad_l": header_pad_l,
                    "header_pad_r": header_pad_r,
                    "header_border_shape": header_border_shape,
                    "title_font": title_font,
                    "title_size": title_size,
                    "title_color": title_color,
                    "title_bg_color": title_bg_color,
                    "title_bg_transparent": title_bg_transparent,
                    "title_pos_y": title_pos_y,
                    "title_align": title_align,
                    "title_height": title_height,
                    "title_pad_l": title_pad_l,
                    "title_pad_r": title_pad_r,
                    "title_border_shape": title_border_shape,
                    "image_width": image_width,
                    "image_height": image_height,
                    "image_pos_x": image_pos_x,
                    "image_pos_y": image_pos_y,
                    "image_border_color": image_border_color,
                    "image_border_width": image_border_width,
                    "image_border_shape": image_border_shape,
                    "font_family": font_family,
                    "font_size": font_size,
                    "content_text_color": content_text_color,
                    "content_bg_color": content_bg_color,
                    "content_bg_opacity": content_bg_opacity,
                    "content_border_color": content_border_color,
                    "content_border_width": content_border_width,
                    "content_border_opacity": content_border_opacity,
                    "content_border_shape": content_border_shape
                })
                st.success("บันทึกการตั้งค่ารูปแบบเทมเพลตสำเร็จ!")

        with right_col:
            st.subheader("👁️ ภาพตัวอย่าง (Mockup Preview)")
            
            preview_data = {
                'header_text': header_text,
                'header_font': header_font,
                'header_size': header_size,
                'header_color': header_color,
                'header_bg_color': header_bg_color,
                'header_bg_transparent': header_bg_transparent,
                'header_pos_y': header_pos_y,
                'header_align': header_align,
                'header_height': header_height,
                'header_pad_l': header_pad_l,
                'header_pad_r': header_pad_r,
                'header_border_shape': header_border_shape,
                
                'title_text': "ตัวอย่างหัวข้อรายงาน (Mockup Title)",
                'title_font': title_font,
                'title_size': title_size,
                'title_color': title_color,
                'title_bg_color': 'transparent' if title_bg_transparent else title_bg_color,
                'title_bg_transparent': title_bg_transparent,
                'title_pos_y': title_pos_y,
                'title_align': title_align,
                'title_height': title_height,
                'title_pad_l': title_pad_l,
                'title_pad_r': title_pad_r,
                'title_border_shape': title_border_shape,
                
                'image_width': image_width,
                'image_height': image_height,
                'image_pos_x': image_pos_x,
                'image_pos_y': image_pos_y,
                'image_border_color': image_border_color,
                'image_border_width': image_border_width,
                'image_border_shape': image_border_shape,
                
                'content': "<p class='ql-indent-1'>นี่คือข้อความตัวอย่างสำหรับทดสอบการจัดวางเนื้อหารายงานของคุณ... การปรับเปลี่ยนฟอนต์ ขนาด หรือสี จะแสดงผลให้เห็นทันทีที่นี่ เพื่อให้คุณตรวจสอบความสวยงามของเทมเพลตก่อนนำไปใช้งานจริง</p><p>ข้อความนี้เป็นเพียงข้อความจำลองเท่านั้น</p>",
                'content_bg_color': content_bg_color,
                'content_bg_opacity': content_bg_opacity,
                'content_border_color': content_border_color,
                'content_border_width': content_border_width,
                'content_border_opacity': content_border_opacity,
                'content_border_shape': content_border_shape,
                
                'report_date': datetime.now().strftime("%d/%m/%Y"),
                'preview_images_base64': [], # Empty list triggers placeholders
                'font_family': font_family,
                'font_size': font_size,
                'content_text_color': content_text_color,
                
                'header_image_path': 'templates/default_header.png',
                'footer_image_path': 'templates/default_footer.png',
                'bg_image_path': 'templates/img_template.png'
            }
            
            html_preview = generate_html_preview(preview_data)
            
            # Inject CSS to scale the body directly inside the HTML document
            scale_css = """
            <style>
                html {
                    display: flex;
                    justify-content: center;
                    background-color: #f0f2f6;
                    height: 676px;
                    overflow: hidden;
                }
                body {
                    transform: scale(0.65);
                    transform-origin: top center;
                    margin: 0;
                    min-width: 720px !important;
                    min-height: 1040px !important;
                    flex-shrink: 0;
                }
            </style>
            """
            scaled_html = html_preview.replace('</head>', f'{scale_css}</head>')
            
            components.html(scaled_html, height=680)

    elif menu == "🗂️ ประวัติรายงาน":
        if 'editing_report_id' not in st.session_state:
            st.session_state['editing_report_id'] = None
            
        if st.session_state['editing_report_id']:
            st.header("✏️ แก้ไขรายงาน")
            
            if st.button("⬅️ กลับไปหน้าประวัติรายงาน"):
                st.session_state['editing_report_id'] = None
                st.rerun()
                
            report_id = st.session_state['editing_report_id']
            rep = get_report_by_id(report_id)
            if not rep:
                st.error("ไม่พบข้อมูลรายงาน")
                st.session_state['editing_report_id'] = None
                st.rerun()
                
            settings = get_user_settings(user_id)
            style_defaults = load_style_defaults()
            def get_def(key, default_val):
                return style_defaults.get(key, default_val)
                
            if 'edit_report_content' not in st.session_state or st.session_state.get('last_edit_id') != report_id:
                st.session_state['edit_report_content'] = rep['content'] or ""
                st.session_state['last_edit_id'] = report_id

            left_col, right_col = st.columns([1.2, 1])
            with left_col:
                with st.container(border=True):
                    st.markdown("#### 📄 ข้อมูลรายงาน")
                    report_date = st.date_input("วันที่", rep['report_date'], key="edit_date")
                    title_text = st.text_input("หัวข้อกิจกรรม", value=rep['title_text'], key="edit_title")
                
                with st.container(border=True):
                    st.markdown("#### 🖼️ รูปภาพประกอบ")
                    uploaded_files = st.file_uploader("อัปโหลดรูปภาพกิจกรรมใหม่ (สูงสุด 4 รูป - หากไม่เลือกจะใช้รูปเดิม)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="edit_files")
                
                with st.container(border=True):
                    st.markdown("#### ✍️ เนื้อหารายงาน")
                    keywords = st.text_area("คำสำคัญ/รายละเอียดเพิ่มเติม (สำหรับ AI)", placeholder="ใส่รายละเอียดสั้นๆ เพื่อให้ AI แต่งบทความ...", key="edit_keywords")
                    generate_ai = st.button("🤖 ให้ AI ช่วยแต่งเนื้อหาใหม่", key="edit_ai")
                    st.markdown("---")
                    content = st_quill(value=st.session_state['edit_report_content'], placeholder="เนื้อหารายงาน...", html=True, key="edit_quill")
            
                submit_btn = st.button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True, key="edit_submit")

                if generate_ai:
                    if not title_text or not keywords:
                        st.warning("กรุณากรอกหัวข้อและคำสำคัญก่อน")
                    else:
                        with st.spinner("กำลังให้ AI แต่งเนื้อหา..."):
                            content_generated = generate_report_content(
                                settings.get('gemini_api_key', ''),
                                settings.get('ai_system_instruction', ''),
                                title_text,
                                keywords
                            )
                            st.session_state['edit_report_content'] = content_generated
                            st.rerun()
                elif submit_btn:
                    with st.spinner("กำลังบันทึกและสร้างภาพใหม่..."):
                        # Handle images
                        image_paths = rep['image_paths']
                        if uploaded_files:
                            image_paths = []
                            for i, file in enumerate(uploaded_files[:4]):
                                path = f"uploads/{user_id}_{datetime.now().timestamp()}_{i}_edit.jpg"
                                with open(path, "wb") as f:
                                    f.write(file.getbuffer())
                                image_paths.append(path)
                        
                        # Update report in DB
                        success = update_report(report_id, report_date, rep.get('header_text', get_def("header_text", "ตม.จว.นครศรีธรรมราช")), title_text, content, image_paths, rep.get('font_family', get_def("font_family", "TH Sarabun IT 9")), rep.get('content_font_size', get_def("font_size", 19)))
                        
                        if success:
                            # Generate Image
                            output_image = f"uploads/report_{report_id}.png"
                            img_data = {
                                'header_text': rep.get('header_text', get_def("header_text", "ตม.จว.นครศรีธรรมราช")),
                                'header_font': get_def("header_font", "TH Sarabun IT 9"),
                                'header_size': get_def("header_size", 32),
                                'header_color': get_def("header_color", "#1a5d1a"),
                                'header_bg_color': 'transparent' if get_def("header_bg_transparent", True) else get_def("header_bg_color", "#ffffff"),
                                'header_pos_y': get_def("header_pos_y", 40),
                                'header_align': get_def("header_align", "กลาง"),
                                'header_height': get_def("header_height", 40),
                                'header_pad_l': get_def("header_pad_l", 20),
                                'header_pad_r': get_def("header_pad_r", 20),
                                'header_border_shape': get_def("header_border_shape", "ขอบโค้ง"),
                                
                                'title_text': title_text,
                                'title_font': get_def("title_font", "TH Sarabun IT 9"),
                                'title_size': get_def("title_size", 28),
                                'title_color': get_def("title_color", "#1a5d1a"),
                                'title_bg_color': 'transparent' if get_def("title_bg_transparent", True) else get_def("title_bg_color", "#ffffff"),
                                'title_pos_y': get_def("title_pos_y", 150),
                                'title_align': get_def("title_align", "ซ้าย"),
                                'title_height': get_def("title_height", 40),
                                'title_pad_l': get_def("title_pad_l", 10),
                                'title_pad_r': get_def("title_pad_r", 10),
                                'title_border_shape': get_def("title_border_shape", "ขอบโค้ง"),
                                
                                'image_width': get_def("image_width", 620),
                                'image_height': get_def("image_height", 250),
                                'image_pos_x': get_def("image_pos_x", 50),
                                'image_pos_y': get_def("image_pos_y", 250),
                                'image_border_color': get_def("image_border_color", "#1a5d1a"),
                                'image_border_width': get_def("image_border_width", 3),
                                'image_border_shape': get_def("image_border_shape", "ขอบโค้ง"),
                                
                                'content': content,
                                'content_bg_color': get_def("content_bg_color", "#ffffff"),
                                'content_bg_opacity': get_def("content_bg_opacity", 0),
                                'content_border_color': get_def("content_border_color", "#cccccc"),
                                'content_border_width': get_def("content_border_width", 0),
                                'content_border_opacity': get_def("content_border_opacity", 100),
                                'content_border_shape': get_def("content_border_shape", "ขอบโค้ง"),
                                'content_text_color': get_def("content_text_color", "#333333"),
                                
                                'report_date': report_date.strftime("%d/%m/%Y"),
                                'images': image_paths,
                                'font_family': rep.get('font_family', get_def("font_family", "TH Sarabun IT 9")),
                                'font_size': rep.get('content_font_size', get_def("font_size", 19))
                            }
                            run_generate_image(img_data, output_image)
                            
                            st.success("บันทึกการแก้ไขสำเร็จ!")
                            st.session_state['editing_report_id'] = None
                            st.rerun()

            with right_col:
                st.subheader("👁️ ภาพตัวอย่าง (Realtime Preview)")
                
                preview_base64_images = []
                if uploaded_files:
                    for file in uploaded_files[:4]:
                        preview_base64_images.append(base64.b64encode(file.getvalue()).decode('utf-8'))
                elif rep.get('image_paths'):
                    for img_path in rep['image_paths']:
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as img_file:
                                preview_base64_images.append(base64.b64encode(img_file.read()).decode('utf-8'))
                
                preview_data = {
                    'header_text': rep.get('header_text', get_def("header_text", "ตม.จว.นครศรีธรรมราช")),
                    'header_font': get_def("header_font", "TH Sarabun IT 9"),
                    'header_size': get_def("header_size", 32),
                    'header_color': get_def("header_color", "#1a5d1a"),
                    'header_bg_color': get_def("header_bg_color", "#ffffff"),
                    'header_bg_transparent': get_def("header_bg_transparent", True),
                    'header_pos_y': get_def("header_pos_y", 40),
                    'header_align': get_def("header_align", "กลาง"),
                    'header_height': get_def("header_height", 40),
                    'header_pad_l': get_def("header_pad_l", 20),
                    'header_pad_r': get_def("header_pad_r", 20),
                    'header_border_shape': get_def("header_border_shape", "ขอบโค้ง"),
                    
                    'title_text': title_text if title_text else "หัวข้อกิจกรรม (ตัวอย่าง)",
                    'title_font': get_def("title_font", "TH Sarabun IT 9"),
                    'title_size': get_def("title_size", 28),
                    'title_color': get_def("title_color", "#1a5d1a"),
                    'title_bg_color': 'transparent' if get_def("title_bg_transparent", True) else get_def("title_bg_color", "#ffffff"),
                    'title_bg_transparent': get_def("title_bg_transparent", True),
                    'title_pos_y': get_def("title_pos_y", 150),
                    'title_align': get_def("title_align", "ซ้าย"),
                    'title_height': get_def("title_height", 40),
                    'title_pad_l': get_def("title_pad_l", 10),
                    'title_pad_r': get_def("title_pad_r", 10),
                    'title_border_shape': get_def("title_border_shape", "ขอบโค้ง"),
                    
                    'image_width': get_def("image_width", 620),
                    'image_height': get_def("image_height", 250),
                    'image_pos_x': get_def("image_pos_x", 50),
                    'image_pos_y': get_def("image_pos_y", 250),
                    'image_border_color': get_def("image_border_color", "#1a5d1a"),
                    'image_border_width': get_def("image_border_width", 3),
                    'image_border_shape': get_def("image_border_shape", "ขอบโค้ง"),
                    
                    'content': content if content else "<p>เนื้อหารายงานตัวอย่าง...</p>",
                    'content_bg_color': get_def("content_bg_color", "#ffffff"),
                    'content_bg_opacity': get_def("content_bg_opacity", 0),
                    'content_border_color': get_def("content_border_color", "#cccccc"),
                    'content_border_width': get_def("content_border_width", 0),
                    'content_border_opacity': get_def("content_border_opacity", 100),
                    'content_border_shape': get_def("content_border_shape", "ขอบโค้ง"),
                    'content_text_color': get_def("content_text_color", "#333333"),
                    
                    'report_date': report_date.strftime("%d/%m/%Y"),
                    'preview_images_base64': preview_base64_images,
                    'font_family': rep.get('font_family', get_def("font_family", "TH Sarabun IT 9")),
                    'font_size': rep.get('content_font_size', get_def("font_size", 19)),
                    
                    'header_image_path': 'templates/default_header.png',
                    'footer_image_path': 'templates/default_footer.png',
                    'bg_image_path': 'templates/img_template.png'
                }
                
                html_preview = generate_html_preview(preview_data)
                
                scale_css = """
                <style>
                    html {
                        display: flex;
                        justify-content: center;
                        background-color: #f0f2f6;
                        height: 676px;
                        overflow: hidden;
                    }
                    body {
                        transform: scale(0.65);
                        transform-origin: top center;
                        margin: 0;
                        min-width: 720px !important;
                        min-height: 1040px !important;
                        flex-shrink: 0;
                    }
                </style>
                """
                scaled_html = html_preview.replace('</head>', f'{scale_css}</head>')
                
                components.html(scaled_html, height=680)
        else:
            st.header("📂 ประวัติรายงาน")
            
            import math
            # Initialize pagination and filter states
            if 'page_number' not in st.session_state:
                st.session_state.page_number = 1
            if 'items_per_page' not in st.session_state:
                st.session_state.items_per_page = 10
            if 'filter_search' not in st.session_state:
                st.session_state.filter_search = ""
            if 'filter_start_date' not in st.session_state:
                st.session_state.filter_start_date = None
            if 'filter_end_date' not in st.session_state:
                st.session_state.filter_end_date = None

            # Search & Filter Form
            with st.form("filter_form"):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    search_term = st.text_input("🔍 ค้นหา (หัวข้อ, เนื้อหา)", value=st.session_state.filter_search, placeholder="พิมพ์คำที่ต้องการค้นหา...")
                with col2:
                    start_date = st.date_input("ตั้งแต่", value=st.session_state.filter_start_date)
                with col3:
                    end_date = st.date_input("ถึง", value=st.session_state.filter_end_date)
                    
                filter_submit = st.form_submit_button("ค้นหา")
            
            # Apply filters
            if filter_submit:
                st.session_state.filter_search = search_term
                st.session_state.filter_start_date = start_date
                st.session_state.filter_end_date = end_date
                st.session_state.page_number = 1  # Reset to page 1 on new search
            
            # Pagination Controls (Top)
            total_count = get_reports_count(user_id, user_role, st.session_state.filter_search, st.session_state.filter_start_date, st.session_state.filter_end_date)
            
            p_col1, p_col2, p_col3, p_col4 = st.columns([1, 1, 1, 2])
            with p_col1:
                items_per_page = st.selectbox("แสดงทีละ", [5, 10, 20, 50, 100], index=[5, 10, 20, 50, 100].index(st.session_state.items_per_page))
                if items_per_page != st.session_state.items_per_page:
                    st.session_state.items_per_page = items_per_page
                    st.session_state.page_number = 1
                    st.rerun()
            
            total_pages = math.ceil(total_count / st.session_state.items_per_page) if total_count > 0 else 1
            
            with p_col2:
                if st.button("⬅️ ก่อนหน้า", disabled=(st.session_state.page_number <= 1)):
                    st.session_state.page_number -= 1
                    st.rerun()
            with p_col3:
                if st.button("ถัดไป ➡️", disabled=(st.session_state.page_number >= total_pages)):
                    st.session_state.page_number += 1
                    st.rerun()
            with p_col4:
                st.markdown(f"<div style='padding-top: 30px;'><b>หน้า {st.session_state.page_number} / {total_pages}</b> (รวม {total_count} รายการ)</div>", unsafe_allow_html=True)

            offset = (st.session_state.page_number - 1) * st.session_state.items_per_page
            reports = get_reports(user_id, user_role, st.session_state.filter_search, st.session_state.filter_start_date, st.session_state.filter_end_date, limit=st.session_state.items_per_page, offset=offset)
            
            if not reports:
                st.info("ยังไม่มีข้อมูลรายงาน หรือไม่พบข้อมูลที่ตรงกับการค้นหา")
            else:
                for rep in reports:
                    with st.expander(f"{rep['report_date']} - {rep['title_text']}"):
                        st.write(f"**เนื้อหา:** {rep['content']}")
                        if rep.get('image_paths') and len(rep['image_paths']) > 0:
                            st.image(rep['image_paths'][0], width=200)
                        
                        col_action1, col_action2, col_action3 = st.columns([1, 1, 2])
                        with col_action1:
                            if st.button(f"ดูรายละเอียด / ส่งซ้ำ", key=f"view_{rep['id']}"):
                                st.session_state[f"show_details_{rep['id']}"] = True
                        with col_action2:
                            if st.button(f"✏️ แก้ไข", key=f"edit_btn_{rep['id']}"):
                                st.session_state['editing_report_id'] = rep['id']
                                st.rerun()

                        if st.session_state.get(f"show_details_{rep['id']}", False):
                            report_path = f"uploads/report_{rep['id']}.png"
                            if os.path.exists(report_path):
                                st.image(report_path, use_container_width=True)
                                
                                with open(report_path, "rb") as file:
                                    st.download_button(
                                        label=f"📥 ดาวน์โหลดรูป {rep['report_date']}",
                                        data=file,
                                        file_name=f"daily_report_{rep['id']}.png",
                                        mime="image/png",
                                        key=f"dl_{rep['id']}"
                                    )

                                settings = get_user_settings(user_id)
                                if st.button("ส่งเข้า Telegram อีกครั้ง", key=f"tg_{rep['id']}"):
                                    success, msg = send_telegram_report(
                                        settings['telegram_bot_token'],
                                        settings['telegram_chat_id'],
                                        report_path,
                                        f"รายงานซ้ำ: {rep['title_text']}"
                                    )
                                    if success: st.success(msg)
                                    else: st.error(msg)
                            else:
                                st.warning("ไม่พบไฟล์ภาพรายงานต้นฉบับ")

    elif menu == "👤 ตั้งค่าส่วนตัว":
        st.header("⚙️ ตั้งค่าส่วนตัว")
        settings = get_user_settings(user_id)
        
        with st.form("settings_form"):
            gemini_key = st.text_input("Gemini API Key", value=settings['gemini_api_key'] or "", type="password")
            bot_token = st.text_input("Telegram Bot Token", value=settings['telegram_bot_token'] or "", type="password")
            chat_id = st.text_input("Telegram Chat ID", value=settings['telegram_chat_id'] or "")
            system_inst = st.text_area("คำสั่งควบคุม AI (System Instruction)", value=settings['ai_system_instruction'] or "", height=150)
            
            save_settings = st.form_submit_button("บันทึกการตั้งค่า")
            
        if save_settings:
            if update_user_settings(user_id, gemini_key, bot_token, chat_id, system_inst):
                st.success("บันทึกการตั้งค่าเรียบร้อย")
            else:
                st.error("เกิดข้อผิดพลาดในการบันทึก")
        
        st.markdown("---")
        st.subheader("🔐 เปลี่ยนรหัสผ่าน")
        with st.form("custom_reset_password_form"):
            new_pwd = st.text_input("รหัสผ่านใหม่", type="password")
            new_pwd_confirm = st.text_input("ยืนยันรหัสผ่านใหม่", type="password")
            
            if st.form_submit_button("ยืนยันการเปลี่ยนรหัสผ่าน"):
                if not new_pwd:
                    st.warning("กรุณากรอกรหัสผ่านใหม่")
                elif new_pwd != new_pwd_confirm:
                    st.error("รหัสผ่านไม่ตรงกัน")
                elif len(new_pwd) < 4:
                    st.error("รหัสผ่านต้องมีความยาวอย่างน้อย 4 ตัวอักษร")
                elif not re.match(r"^[a-zA-Z0-9]+$", new_pwd):
                    st.error("รหัสผ่านต้องประกอบด้วยตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น (ห้ามเว้นวรรคหรือใช้อักขระพิเศษ)")
                else:
                    try:
                        # Hash the new password using bcrypt
                        hashed_pwd = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        # Update config
                        config['credentials']['usernames'][username]['password'] = hashed_pwd
                        save_config(config)
                        st.success("เปลี่ยนรหัสผ่านสำเร็จ! กรุณาล็อกเอาท์และเข้าสู่ระบบใหม่ด้วยรหัสผ่านใหม่")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

    elif menu == "👥 จัดการผู้ใช้งาน":
        st.header("👥 จัดการผู้ใช้งาน (Admin Panel)")
        if user_role != 'admin':
            st.error("คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        else:
            tab1, tab2 = st.tabs(["📋 รายชื่อผู้ใช้", "➕ เพิ่มผู้ใช้ใหม่"])
            
            with tab1:
                st.subheader("รายชื่อผู้ใช้งานในระบบ")
                users = get_all_users()
                for u in users:
                    with st.expander(f"👤 {u['username']} ({u['full_name']}) - {u['role']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_role = st.selectbox("สิทธิ์การใช้งาน", ["staff", "admin"], index=0 if u['role'] == 'staff' else 1, key=f"role_{u['username']}")
                            if st.button("บันทึกสิทธิ์", key=f"save_{u['username']}"):
                                if update_user_role(u['username'], new_role):
                                    st.success("เปลี่ยนสิทธิ์สำเร็จ")
                                    st.rerun()
                                else:
                                    st.error("เกิดข้อผิดพลาด")
                        with col2:
                            if u['username'] != 'admin':
                                if st.button("🗑️ ลบผู้ใช้นี้", key=f"del_{u['username']}"):
                                    if u['username'] in config['credentials']['usernames']:
                                        del config['credentials']['usernames'][u['username']]
                                        save_config(config)
                                    delete_user(u['username'])
                                    st.success("ลบสำเร็จ")
                                    st.rerun()

            with tab2:
                st.subheader("เพิ่มผู้ใช้ใหม่")
                with st.form("add_user_form"):
                    new_username = st.text_input("Username")
                    new_name = st.text_input("ชื่อ-สกุล (Full Name)")
                    new_email = st.text_input("Email")
                    new_password = st.text_input("Password", type="password")
                    new_role_opt = st.selectbox("Role", ["staff", "admin"])
                    
                    if st.form_submit_button("เพิ่มผู้ใช้"):
                        if new_username and new_password and new_name and new_email:
                            if new_username in config['credentials']['usernames']:
                                st.error("Username นี้มีอยู่แล้วในระบบ")
                            elif not re.match(r"^[a-zA-Z0-9]+$", new_password):
                                st.error("รหัสผ่านต้องประกอบด้วยตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น")
                            elif len(new_password) < 4:
                                st.error("รหัสผ่านต้องมีความยาวอย่างน้อย 4 ตัวอักษร")
                            else:
                                hashed_pwd = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                config['credentials']['usernames'][new_username] = {
                                    'email': new_email,
                                    'name': new_name,
                                    'password': hashed_pwd
                                }
                                save_config(config)
                                create_user(new_username, "password_not_stored_here", new_name, new_role_opt)
                                st.success("เพิ่มผู้ใช้สำเร็จ")
                                # No rerun needed, user can see success message
                        else:
                            st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
