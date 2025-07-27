import base64
import json
import os
import re
import sys
import google.generativeai as genai
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

# --- بخش تنظیمات ---
# این بخش دقیقا مثل قبل است
WP_URL = 'https://iconkadeh.ir'
API_ENDPOINT = f"{WP_URL}/wp-json/iconkadeh/v1/upload"
WP_USERNAME = 'mehrhas_admin'
WP_APP_PASSWORD = 'd8RB SMPT NM7v wr7J F0ln WFNg' 
# کلید Gemini API خود را در متغیرهای محیطی هاست قرار خواهیم داد
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyAhkzNcizNTitp32v8juh3iW3xIPGpq-PQ')

genai.configure(api_key=GEMINI_API_KEY)

# --- راه‌اندازی اپلیکیشن Flask ---
app = Flask(__name__, template_folder='web', static_folder='web', static_url_path='')

def clean_svg_content(svg_string):
    modified_content = re.sub(r'\s?width="[^"]*"', '', svg_string, flags=re.IGNORECASE)
    modified_content = re.sub(r'\s?height="[^"]*"', '', modified_content, flags=re.IGNORECASE)
    modified_content = re.sub(r'fill="[^"]*"', 'fill="currentColor"', modified_content, flags=re.IGNORECASE)
    return modified_content

# --- مسیر اصلی برنامه که فایل index.html را نشان می‌دهد ---
@app.route('/')
def index():
    return render_template('index.html')

# --- تبدیل توابع eel به API Endpoints ---

@app.route('/api/get_categories', methods=['GET'])
def get_categories_api():
    try:
        cat_url = f"{WP_URL}/wp-json/wp/v2/download_category?per_page=100"
        response = requests.get(cat_url, auth=(WP_USERNAME, WP_APP_PASSWORD))
        response.raise_for_status()
        categories = {cat['id']: cat['name'] for cat in response.json()}
        return jsonify(categories)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_ai_content', methods=['POST'])
def generate_ai_content_api():
    try:
        data = request.json
        file_info = data['file_info']
        english_name_hint = data['english_name']
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        svg_bytes = base64.b64decode(file_info['content'])
        svg_text_content = svg_bytes.decode('utf-8')

        prompt = f"""
        شما یک متخصص تولید محتوا برای یک وب‌سایت آیکون هستید. وظیفه شما تولید عنوان، توضیحات و برچسب‌های دقیق برای آیکون زیر است.

        **راهنمای مهم:**
        - نام انگلیسی که کاربر وارد کرده: "{english_name_hint}"
        - کد SVG آیکون:
        ```xml
        {svg_text_content}
        ```

        **قوانین خروجی (بسیار مهم):**
        1.  **عنوان (title):** باید دقیقاً در فرمت `آیکون [نام فارسی] / [English Name] Icon` باشد.
        2.  **توضیحات (description):** باید با بخش فارسی عنوان (`آیکون [نام فارسی]`) شروع شود و بلافاصله بعد از آن یک کاما (,) بیاید. سپس یک توضیح کامل و حرفه‌ای برای کاربردها و ویژگی‌های آیکون بنویس.
        3.  **برچسب‌ها (tags):** یک رشته متنی شامل ۵ تا ۷ کلمه کلیدی مرتبط و مهم (فقط فارسی)، که با کاما (,) از هم جدا شده‌اند، تولید کن.

        **مثال خروجی دقیق:**
        {{
          "title": "آیکون ذره بین جستجو / Search Icon",
          "description": "آیکون ذره بین جستجو, این آیکون نماد جستجو (Search) و یافتن اطلاعات است. بیشترین کاربرد آن در نوارهای جستجو وب‌سایت‌ها و اپلیکیشن‌ها است.",
          "tags": "جستجو, ذره بین, یافتن, رابط کاربری, وب, تحقیق, کاوش"
        }}

        پاسخ خود را **فقط و فقط** به صورت یک آبجکت JSON با سه کلید `title`, `description` و `tags` برگردان.
        """
        
        response = model.generate_content(prompt)
        text_content = response.text
        cleaned_text = text_content.strip().replace('```json', '').replace('```', '').strip()
        generated_data = json.loads(cleaned_text)

        return jsonify({'status': 'success', 'data': generated_data})

    except Exception as e:
        print(f"ERROR in Gemini generation: {e}")
        return jsonify({'status': 'error', 'message': f"یک خطای ناشناخته در ارتباط با هوش مصنوعی رخ داد: {e}"}), 500

@app.route('/api/upload_icon', methods=['POST'])
def upload_icon_api():
    try:
        data = request.form.to_dict()
        file = request.files['ik_svg_file']
        
        original_svg_string = file.read().decode('utf-8')
        cleaned_svg_string = clean_svg_content(original_svg_string)
        cleaned_bytes = cleaned_svg_string.encode('utf-8')

        files = {'ik_svg_file': (file.filename, cleaned_bytes, 'image/svg+xml')}
        response = requests.post(API_ENDPOINT, data=data, files=files, auth=(WP_USERNAME, WP_APP_PASSWORD))
        response.raise_for_status()
        
        result = response.json()
        if result.get('success'):
            return jsonify({'status': 'success', 'message': f"آیکون با موفقیت منتشر شد! لینک: {result.get('post_link')}"})
        else:
            return jsonify({'status': 'error', 'message': f"خطا از سرور: {result.get('message')}"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f"یک خطای ناشناخته در پایتون رخ داد: {e}"}), 500

# --- برای اجرای محلی (اختیاری) ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
