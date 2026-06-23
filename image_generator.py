import asyncio
from playwright.async_api import async_playwright
from jinja2 import Template
import base64
import os

def image_to_base64(image_path):
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_html_preview(data):
    # Load template
    template_path = os.path.join("templates", "report_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    template = Template(template_content)
    
    # Prepare images
    if 'preview_images_base64' in data:
        base64_images = data['preview_images_base64']
    else:
        base64_images = [image_to_base64(img) for img in data.get('images', [])]
    
    # Header/Footer/Background images
    header_img = data.get('header_image_path', 'templates/default_header.png')
    footer_img = data.get('footer_image_path', 'templates/default_footer.png')
    bg_img = data.get('bg_image_path', 'templates/img_template.png')
    
    def hex_to_rgba(hex_color, opacity):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f"rgba({r}, {g}, {b}, {opacity/100})"
        return hex_color
        
    content_bg = hex_to_rgba(data.get('content_bg_color', '#ffffff'), data.get('content_bg_opacity', 0))
    
    # If defaults don't exist, we might want to handle it (but for now assume they exist or use empty)
    header_base64 = f"data:image/png;base64,{image_to_base64(header_img)}" if os.path.exists(header_img) else ""
    footer_base64 = f"data:image/png;base64,{image_to_base64(footer_img)}" if os.path.exists(footer_img) else ""
    bg_base64 = f"data:image/png;base64,{image_to_base64(bg_img)}" if os.path.exists(bg_img) else ""

    def get_int(key, default_val):
        val = data.get(key)
        if val is None or val == "":
            return default_val
        try:
            return int(val)
        except ValueError:
            return default_val

    html_content = template.render(
        header_text=data.get('header_text', 'รายงานประจำวัน'),
        header_font=data.get('header_font', 'TH Sarabun IT 9'),
        header_size=get_int('header_size', 32),
        header_color=data.get('header_color', '#1a5d1a'),
        header_bg_color=data.get('header_bg_color', 'transparent'),
        header_pos_y=get_int('header_pos_y', 40),
        header_align=data.get('header_align', 'กลาง'),
        header_height=get_int('header_height', 40),
        header_pad_l=get_int('header_pad_l', 20),
        header_pad_r=get_int('header_pad_r', 20),
        header_border_shape=data.get('header_border_shape', 'ขอบโค้ง'),
        title_text=data.get('title_text', ''),
        title_font=data.get('title_font', 'TH Sarabun IT 9'),
        title_size=get_int('title_size', 28),
        title_color=data.get('title_color', '#1a5d1a'),
        title_bg_color=data.get('title_bg_color', 'transparent'),
        title_pos_y=get_int('title_pos_y', 150),
        title_align=data.get('title_align', 'ซ้าย'),
        title_height=get_int('title_height', 40),
        title_pad_l=get_int('title_pad_l', 10),
        title_pad_r=get_int('title_pad_r', 10),
        title_border_shape=data.get('title_border_shape', 'ขอบโค้ง'),
        image_width=get_int('image_width', 620),
        image_height=get_int('image_height', 250),
        image_pos_x=get_int('image_pos_x', 50),
        image_pos_y=get_int('image_pos_y', 250),
        image_border_color=data.get('image_border_color', '#1a5d1a'),
        image_border_width=get_int('image_border_width', 3),
        image_border_shape=data.get('image_border_shape', 'ขอบโค้ง'),
        content=data.get('content', ''),
        content_bg=content_bg,
        content_border_color=data.get('content_border_color', '#cccccc'),
        content_border_width=data.get('content_border_width', 0),
        content_border_shape=data.get('content_border_shape', 'ขอบโค้ง'),
        report_date=data.get('report_date', ''),
        images=base64_images,
        font_family=data.get('font_family', 'TH Sarabun IT 9'),
        font_size=data.get('font_size', 19),
        content_text_color=data.get('content_text_color', '#333333'),
        header_image=header_base64,
        footer_image=footer_base64,
        bg_image=bg_base64
    )
    return html_content

async def generate_report_image(data, output_path):
    html_content = generate_html_preview(data)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 720, 'height': 1040})
        await page.set_content(html_content)
        # Wait for images to load
        await page.wait_for_timeout(1000) 
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def run_generate_image(data, output_path):
    asyncio.run(generate_report_image(data, output_path))
