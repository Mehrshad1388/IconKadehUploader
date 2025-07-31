import base64
import json
import os
import re
import sys
import google.generativeai as genai
import requests
from flask import Flask, request, jsonify, render_template


# --- بخش تنظیمات (دست نخورده) ---
WP_URL = 'https://iconkadeh.ir'
API_ENDPOINT = f"{WP_URL}/wp-json/iconkadeh/v1/upload"
WP_USERNAME = 'mehrhas_admin'
WP_APP_PASSWORD = 'd8RB SMPT NM7v wr7J F0ln WFNg'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)

# --- راه‌اندازی اپلیکیشن Flask (دست نخورده) ---
app = Flask(__name__, template_folder='web', static_folder='web', static_url_path='')


def clean_svg_content(svg_string):
    # حذف کامنت‌های HTML
    modified_content = re.sub(r'<!--(.*?)-->', '', svg_string, flags=re.DOTALL)
    # حذف عرض و ارتفاع
    modified_content = re.sub(r'\s?width="[^"]*"', '', modified_content, flags=re.IGNORECASE)
    modified_content = re.sub(r'\s?height="[^"]*"', '', modified_content, flags=re.IGNORECASE)
    # *** اصلاح کلیدی: فقط fill هایی که "none" نیستند را جایگزین کن ***
    modified_content = re.sub(r'fill="(?!none")[^"]*"', 'fill="currentColor"', modified_content, flags=re.IGNORECASE)
    # برای اطمینان، stroke ها را هم به currentColor تبدیل می‌کنیم
    modified_content = re.sub(r'stroke="[^"]*"', 'stroke="currentColor"', modified_content, flags=re.IGNORECASE)
    return modified_content.strip()


@app.route('/')
def index():
    return render_template('index.html')


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
        model_name = data.get('model_name', 'gemini-1.5-flash')
        
        model = genai.GenerativeModel(model_name)
        
        svg_bytes = base64.b64decode(file_info['content'])
        svg_text_content = svg_bytes.decode('utf-8')

        prompt = f"""
        **شخصیت شما:** شما یک متخصص ارشد تولید محتوا و SEO برای وب‌سایت دانلود آیکون "آیکون کده" هستید.
        **وظیفه شما:** تولید عنوان، توضیحات و برچسب‌های حرفه‌ای و بهینه برای موتورهای جستجو (SEO) برای آیکون زیر.
        **اطلاعات ورودی:**
        - راهنمای نام انگلیسی از کاربر: "{english_name_hint}"
        - کد SVG آیکون:
        ```xml
        {svg_text_content}
        ```
        **قوانین تولید محتوا (بسیار مهم):**
        1.  **عنوان (title):**
            - فرمت باید `آیکون [نام دقیق و توصیفی فارسی] / [English Name] Icon` باشد.
        2.  **توضیحات (description):**
            - با عبارت فارسی عنوان (`آیکون [نام دقیق و توصیفی فارسی]`) و یک کاما (,) شروع شود.
            - یک پاراگراف کامل و جذاب (حدود ۴-۵ خط) بنویس.
            - **ممنوعیت‌ها:** هرگز در مورد **رنگ، اندازه یا فرمت فایل** صحبت نکن.
            - **الزامات:**
                - کاربرد اصلی آیکون را شرح بده.
                - به موارد استفاده آن در رابط کاربری (UI) وب‌سایت‌ها و اپلیکیشن‌ها اشاره کن.
        3.  **برچسب‌ها (tags):**
            - یک رشته متنی شامل ۶ تا ۸ کلمه کلیدی بسیار مرتبط (فقط فارسی) که با کاما (,) از هم جدا شده‌اند.
        **خروجی:**
        فقط و فقط یک آبجکت JSON با سه کلید `title`, `description` و `tags`.
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

        # *** افزودن منطق تشخیص نوع آیکون ***
        if 'fill="none"' in original_svg_string.lower() and 'stroke=' in original_svg_string.lower():
            data['ik_icon_type'] = 'stroked'
        else:
            data['ik_icon_type'] = 'filled'
        
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
