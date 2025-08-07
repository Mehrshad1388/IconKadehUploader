import base64
import json
import os
import re
import sys

import google.generativeai as genai
import requests
from flask import Flask, jsonify, render_template, request

# --- بخش تنظیمات (بدون تغییر) ---
# این بخش شامل URL وردپرس، اطلاعات احراز هویت و کلید API است.
WP_URL = 'https://iconkadeh.ir'
API_ENDPOINT = f"{WP_URL}/wp-json/iconkadeh/v1/upload"
WP_USERNAME = 'mehrhas_admin'
WP_APP_PASSWORD = 'd8RB SMPT NM7v wr7J F0ln WFNg'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)

# --- راه‌اندازی اپلیکیشن Flask (بدون تغییر) ---
# اپلیکیشن Flask با تنظیمات مربوط به پوشه‌ها و مسیرها راه‌اندازی می‌شود.
app = Flask(__name__, template_folder='web', static_folder='web', static_url_path='')


def clean_svg_content(svg_string):
    """
    محتوای یک فایل SVG را پاکسازی می‌کند.
    این تابع، ویژگی‌های عرض، ارتفاع و fill را از محتوای SVG حذف یا جایگزین می‌کند.
    """
    modified_content = re.sub(r'\s?width="[^"]*"', '', svg_string, flags=re.IGNORECASE)
    modified_content = re.sub(r'\s?height="[^"]*"', '', modified_content, flags=re.IGNORECASE)
    modified_content = re.sub(r'fill="[^"]*"', 'fill="currentColor"', modified_content, flags=re.IGNORECASE)
    return modified_content


@app.route('/')
def index():
    """مسیر اصلی برای نمایش صفحه HTML."""
    return render_template('index.html')


@app.route('/api/get_categories', methods=['GET'])
def get_categories_api():
    """
    دسته بندی‌های آیکون را از API وردپرس دریافت کرده و به صورت JSON برمی‌گرداند.
    """
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
    """
    محتوای عنوان، توضیحات و برچسب‌های آیکون را با استفاده از هوش مصنوعی جمینی تولید می‌کند.
    """
    try:
        data = request.json
        file_info = data['file_info']
        english_name_hint = data['english_name']
        # دریافت نام مدل از درخواست، با مقدار پیش‌فرض
        model_name = data.get('model_name', 'gemini-1.5-flash')

        # استفاده از مدل انتخاب‌شده توسط کاربر
        model = genai.GenerativeModel(model_name)

        svg_bytes = base64.b64decode(file_info['content'])
        svg_text_content = svg_bytes.decode('utf-8')

        # --- پرامپت جدید و بسیار هوشمندتر ---
        prompt = f"""
**شخصیت شما:** شما یک متخصص ارشد تولید محتوا و SEO برای وب‌سایت دانلود آیکون "آیکون کده" هستید. مخاطبان شما طراحان وب و توسعه‌دهندگان اپلیکیشن هستند.

**وظیفه شما:** تولید عنوان، توضیحات و برچسب‌های حرفه‌ای، جذاب و بهینه برای موتورهای جستجو (SEO) برای آیکون زیر.

**اطلاعات ورودی:**
- راهنمای نام انگلیسی از کاربر: "{english_name_hint}"
- کد SVG آیکون:
```xml
{svg_text_content}
```

**قوانین تولید محتوا (بسیار مهم):**
1.  **عنوان (title):**
    - فرمت باید `آیکون [نام دقیق و توصیفی فارسی] / [English Name] Icon` باشد.
    - نام فارسی باید خلاقانه و شامل کلمات کلیدی مهم باشد (مثلاً به جای "جستجو"، بنویس "ذره بین جستجو"). عنوان نباید خیلی طولانی شود.

2.  **توضیحات (description):**
    - با عبارت فارسی عنوان (`آیکون [نام دقیق و توصیفی فارسی]`) و یک کاما (,) شروع شود.
    - یک پاراگراف کامل و جذاب (حدود ۴-۵ خط) بنویس.
    - **ممنوعیت‌ها:** هرگز در مورد **رنگ، اندازه یا فرمت فایل** صحبت نکن، زیرا کاربران می‌توانند این موارد را در سایت تغییر دهند (آیکون‌ها `fill="currentColor"` هستند).
    - **الزامات:**
        - کاربرد اصلی آیکون را شرح بده.
        - به موارد استفاده آن در رابط کاربری (UI) وب‌سایت‌ها و اپلیکیشن‌ها اشاره کن.
        - **سبک طراحی آیکون** را از روی ظاهر آن تشخیص بده (مثلاً: Material Design, Fluent, iOS Style, فلت, مینیمال) و در متن ذکر کن.

3.  **برچسب‌ها (tags):**
    - یک رشته متنی شامل ۶ تا ۸ کلمه کلیدی بسیار مرتبط (فقط فارسی) که با کاما (,) از هم جدا شده‌اند. هم کلمات عمومی و هم کلمات تخصصی‌تر را پوشش بده.

**مثال خروجی برای آیکون جستجو:**
{{
  "title": "آیکون ذره بین جستجو / Search Icon",
  "description": "آیکون ذره بین جستجو, نمادی واضح و کاربردی برای قابلیت جستجو و کاوش در انواع پلتفرم‌های دیجیتال است. این آیکون که با الهام از سبک طراحی متریال (Material Design) ساخته شده، به کاربران کمک می‌کند تا به راحتی بخش جستجوی سایت یا اپلیکیشن شما را پیدا کنند. استفاده از آن در نوار ناوبری، هدر وب‌سایت یا به عنوان یک دکمه شناور، تجربه کاربری را بهبود بخشیده و دسترسی به اطلاعات را تسریع می‌کند.",
  "tags": "جستجو, ذره بین, یافتن, رابط کاربری, وب, تحقیق, کاوش, سرچ"
}}

پاسخ را **فقط و فقط** به صورت یک آبجکت JSON با سه کلید `title`, `description` و `tags` برگردان.
"""

        response = model.generate_content(prompt)
        text_content = response.text
        cleaned_text = text_content.strip().replace('```json', '').replace('```', '').strip()
        generated_data = json.loads(cleaned_text)

        return jsonify({'status': 'success', 'data': generated_data})

    except Exception as e:
        print(f"ERROR in Gemini generation: {e}")
        return jsonify({'status': 'error', 'message': f"یک خطای ناشناخته در ارتباط با هوش مصنوعی رخ داد: {e}"}), 500


# بقیه کد بدون تغییر باقی می‌ماند
@app.route('/api/upload_icon', methods=['POST'])
def upload_icon_api():
    """
    آیکون را از کاربر دریافت کرده، پاکسازی می‌کند و سپس به API وردپرس آپلود می‌کند.
    """
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
