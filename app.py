import base64
import json
import os
import re
import sys
import eel
import requests
import google.generativeai as genai

# --- بخش تنظیمات ---
WP_URL = 'https://iconkadeh.ir'
API_ENDPOINT = f"{WP_URL}/wp-json/iconkadeh/v1/upload"
WP_USERNAME = 'mehrhas_admin'
WP_APP_PASSWORD = 'd8RB SMPT NM7v wr7J F0ln WFNg'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- راه‌اندازی Eel و Gemini ---
eel.init('web')
genai.configure(api_key=GEMINI_API_KEY)

def clean_svg_content(svg_string):
    """محتوای SVG را برای آپلود در وردپرس پاکسازی می‌کند."""
    modified_content = re.sub(r'\s?width="[^"]*"', '', svg_string, flags=re.IGNORECASE)
    modified_content = re.sub(r'\s?height="[^"]*"', '', modified_content, flags=re.IGNORECASE)
    # اطمینان از اینکه fill="none" دستکاری نمی‌شود
    modified_content = re.sub(r'fill="(?!(none|#fff|#ffffff|white))[^"]*"', 'fill="currentColor"', modified_content, flags=re.IGNORECASE)
    return modified_content

@eel.expose
def get_categories():
    """دسته‌بندی‌ها را از وردپرس دریافت می‌کند."""
    try:
        cat_url = f"{WP_URL}/wp-json/wp/v2/download_category?per_page=100"
        response = requests.get(cat_url, auth=(WP_USERNAME, WP_APP_PASSWORD), timeout=15)
        response.raise_for_status()
        return {cat['id']: cat['name'] for cat in response.json()}
    except Exception as e:
        print(f"ERROR getting categories: {e}")
        return {}

@eel.expose
def generate_ai_content(file_info, english_name_hint, model_name):
    """محتوا را با استفاده از هوش مصنوعی تولید می‌کند."""
    try:
        model = genai.GenerativeModel(model_name)
        svg_bytes = base64.b64decode(file_info['content'])
        svg_text_content = svg_bytes.decode('utf-8')

        prompt = f"""
        **شخصیت شما:** شما یک متخصص ارشد تولید محتوا و SEO برای وب‌سایت دانلود آیکون "آیکون کده" هستید.
        **وظیفه شما:** تولید عنوان، توضیحات و برچسب‌های حرفه‌ای و بهینه برای آیکون زیر.
        **اطلاعات ورودی:**
        - راهنمای نام انگلیسی: "{english_name_hint}"
        - کد SVG: ```xml\n{svg_text_content}\n```
        **قوانین تولید محتوا:**
        1.  **عنوان (title):** فرمت `آیکون [نام دقیق فارسی] / [English Name] Icon`.
        2.  **توضیحات (description):** با `آیکون [نام دقیق فارسی]،` شروع شود. یک پاراگراف جذاب ۴-۵ خطی بنویس. هرگز در مورد رنگ، اندازه یا فرمت صحبت نکن. به کاربرد و سبک طراحی (مثلاً متریال، فلت) اشاره کن.
        3.  **برچسب‌ها (tags):** یک رشته متنی شامل ۶ تا ۸ کلمه کلیدی مرتبط فارسی، جدا شده با کاما.
        **مثال خروجی:**
        {{
          "title": "آیکون ذره بین جستجو / Search Icon",
          "description": "آیکون ذره بین جستجو، نمادی واضح و کاربردی برای قابلیت جستجو و کاوش در انواع پلتفرم‌های دیجیتال است. این آیکون که با الهام از سبک طراحی متریال ساخته شده، به کاربران کمک می‌کند تا به راحتی بخش جستجوی سایت یا اپلیکیشن شما را پیدا کنند.",
          "tags": "جستجو, ذره بین, یافتن, رابط کاربری, وب, تحقیق, کاوش, سرچ"
        }}
        پاسخ را **فقط و فقط** به صورت یک آبجکت JSON با سه کلید `title`, `description` و `tags` برگردان.
        """
        
        response = model.generate_content(prompt)
        text_content = response.text
        cleaned_text = text_content.strip().replace('```json', '').replace('```', '').strip()
        generated_data = json.loads(cleaned_text)
        return {'status': 'success', 'data': generated_data}
    except Exception as e:
        print(f"ERROR in Gemini generation: {e}")
        return {'status': 'error', 'message': f"خطا در ارتباط با هوش مصنوعی: {e}"}

@eel.expose
def upload_icon(form_data, file_info):
    """آیکون را در وردپرس آپلود می‌کند."""
    try:
        original_svg_string = base64.b64decode(file_info['content']).decode('utf-8')
        cleaned_svg_string = clean_svg_content(original_svg_string)
        cleaned_bytes = cleaned_svg_string.encode('utf-8')

        # تبدیل مقادیر بولی به رشته 'true'/'false' برای ارسال
        for key in ['color', 'size', 'weight']:
            form_data[key] = 'true' if form_data[key] else 'false'

        files = {'ik_svg_file': (file_info['name'], cleaned_bytes, 'image/svg+xml')}
        response = requests.post(API_ENDPOINT, data=form_data, files=files, auth=(WP_USERNAME, WP_APP_PASSWORD), timeout=30)
        response.raise_for_status()

        result = response.json()
        if result.get('success'):
            return {'status': 'success', 'message': f"آیکون با موفقیت منتشر شد! لینک: {result.get('post_link')}"}
        else:
            return {'status': 'error', 'message': f"خطا از سرور وردپرس: {result.get('message')}"}
    except Exception as e:
        print(f"ERROR in icon upload: {e}")
        return {'status': 'error', 'message': f"خطای ناشناخته در پایتون: {e}"}

# --- اجرای اپلیکیشن ---
if __name__ == '__main__':
    try:
        eel.start('index.html', size=(800, 950), options={'port': 0})
    except (SystemExit, MemoryError, KeyboardInterrupt):
        # جلوگیری از نمایش خطاهای معمول هنگام بستن برنامه
        pass
