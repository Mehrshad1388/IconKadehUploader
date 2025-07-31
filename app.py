import base64
import json
import os
import re
import sys
import google.generativeai as genai
import requests
from flask import Flask, request, jsonify, render_template

# --- بخش تنظیمات ---
WP_URL = 'https://iconkadeh.ir'
API_ENDPOINT = f"{WP_URL}/wp-json/iconkadeh/v1/upload"
WP_USERNAME = 'mehrhas_admin'
WP_APP_PASSWORD = os.environ.get('WP_APP_PASSWORD', 'd8RB SMPT NM7v wr7J F0ln WFNg')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- راه‌اندازی سرویس‌ها ---
try:
    if not GEMINI_API_KEY:
        raise ValueError("متغیر محیطی GEMINI_API_KEY تعریف نشده است.")
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"خطا در تنظیم Gemini: {e}", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__, template_folder='web', static_folder='web', static_url_path='')


def clean_svg_content(svg_string):
    """
    SVG code را برای سازگاری با فرانت‌اند آیکون کده به شکلی امن و پایدار تمیز می‌کند.
    این تابع فقط ویژگی‌های ضروری را تغییر می‌دهد و از بازنویسی‌های پیچیده خودداری می‌کند.
    """
    # ۱. حذف ویژگی‌های عرض و ارتفاع برای ریسپانسیو بودن
    cleaned = re.sub(r'\s?width="[^"]*"', '', svg_string, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s?height="[^"]*"', '', cleaned, flags=re.IGNORECASE)

    # ۲. تمام رنگ‌های fill (به جز fill="none") را با currentColor جایگزین کن
    cleaned = re.sub(r'fill="(?!none")[^"]*"', 'fill="currentColor"', cleaned, flags=re.IGNORECASE)

    # ۳. تمام رنگ‌های stroke (به جز stroke="none") را با currentColor جایگزین کن
    cleaned = re.sub(r'stroke="(?!none")[^"]*"', 'stroke="currentColor"', cleaned, flags=re.IGNORECASE)

    # ۴. (فال‌بک نهایی) اگر پس از تمیزکاری، هیچ ویژگی رنگی currentColor وجود نداشت،
    # بر اساس نوع آیکون، ویژگی مناسب را به تگ اصلی اضافه کن.
    if 'currentColor' not in cleaned.lower():
        # اگر آیکون خطی است (بر اساس ساختار اصلی)
        if 'fill="none"' in svg_string.lower():
            # اگر stroke هم ندارد، آن را اضافه کن
            if 'stroke=' not in cleaned.lower():
                 cleaned = re.sub(r'(<svg[^>]*>)', r'\1 stroke="currentColor"', cleaned, 1, flags=re.IGNORECASE)
        # در غیر این صورت، آیکون تو پُر است
        else:
            # اگر fill هم ندارد، آن را اضافه کن
            if 'fill=' not in cleaned.lower():
                cleaned = re.sub(r'(<svg[^>]*>)', r'\1 fill="currentColor"', cleaned, 1, flags=re.IGNORECASE)

    return cleaned


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/get_categories', methods=['GET'])
def get_categories_api():
    try:
        cat_url = f"{WP_URL}/wp-json/wp/v2/download_category?per_page=100"
        response = requests.get(cat_url, auth=(WP_USERNAME, WP_APP_PASSWORD), timeout=20)
        response.raise_for_status()
        categories = {cat['id']: cat['name'] for cat in response.json()}
        return jsonify(categories)
    except requests.exceptions.RequestException as e:
        print(f"خطا در ارتباط با وردپرس برای دریافت دسته‌بندی‌ها: {e}", file=sys.stderr)
        return jsonify({"error": f"خطا در ارتباط با سایت: {e}"}), 502
    except Exception as e:
        print(f"خطای ناشناخته در دریافت دسته‌بندی‌ها: {e}", file=sys.stderr)
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
        svg_text_content = svg_bytes.decode('utf-8').lower()

        is_stroked = 'stroke-width' in svg_text_content and 'fill="none"' in svg_text_content
        icon_style = "Stroked / Line Art (مانند Lucide)" if is_stroked else "Filled (مانند Material Design)"

        prompt = f"""
        **شخصیت:** شما یک متخصص ارشد تولید محتوا و SEO برای وب‌سایت "آیکون کده" هستید.
        **وظیفه:** تولید عنوان، توضیحات و برچسب‌های حرفه‌ای و بهینه برای آیکون زیر.
        **اطلاعات ورودی:**
        - راهنمای نام انگلیسی: "{english_name_hint}"
        - سبک طراحی تشخیص داده شده: "{icon_style}"
        **قوانین:**
        1.  **عنوان (title):** فرمت `آیکون [نام دقیق فارسی] / [English Name] Icon`.
        2.  **توضیحات (description):** یک پاراگراف کامل (۴-۵ خط) که با "آیکون [نام دقیق فارسی]،" شروع شود. کاربرد آیکون در UI را شرح بده و به سبک طراحی ({icon_style}) اشاره کن. هرگز در مورد رنگ، اندازه یا فرمت صحبت نکن.
        3.  **برچسب‌ها (tags):** یک رشته شامل ۶ تا ۸ کلمه کلیدی مرتبط فارسی، جدا شده با کاما.
        **خروجی:** فقط یک آبجکت JSON با کلیدهای `title`, `description`, و `tags`.
        """
        
        response = model.generate_content(prompt)
        cleaned_text = re.sub(r'```json|```', '', response.text).strip()
        generated_data = json.loads(cleaned_text)

        return jsonify({'status': 'success', 'data': generated_data})

    except Exception as e:
        print(f"ERROR in Gemini generation: {e}", file=sys.stderr)
        return jsonify({'status': 'error', 'message': f"خطا در ارتباط با هوش مصنوعی: {e}"}), 500


@app.route('/api/upload_icon', methods=['POST'])
def upload_icon_api():
    try:
        data = request.form.to_dict()
        if 'ik_svg_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'فایل SVG ارسال نشده است.'}), 400
            
        file = request.files['ik_svg_file']
        original_svg_string = file.read().decode('utf-8')

        svg_text_lower = original_svg_string.lower()
        if 'stroke-width' in svg_text_lower and 'fill="none"' in svg_text_lower:
            data['ik_icon_type'] = 'stroked'
        else:
            data['ik_icon_type'] = 'filled'
        
        cleaned_svg_string = clean_svg_content(original_svg_string)
        cleaned_bytes = cleaned_svg_string.encode('utf-8')

        files = {'ik_svg_file': (file.filename, cleaned_bytes, 'image/svg+xml')}
        
        response = requests.post(API_ENDPOINT, data=data, files=files, auth=(WP_USERNAME, WP_APP_PASSWORD), timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if result.get('success'):
            return jsonify({'status': 'success', 'message': f"آیکون با موفقیت منتشر شد! لینک: {result.get('post_link')}"})
        else:
            return jsonify({'status': 'error', 'message': f"خطا از سرور وردپرس: {result.get('message', 'نامشخص')}"}), 400
            
    except requests.exceptions.RequestException as e:
        print(f"خطا در آپلود به وردپرس: {e}", file=sys.stderr)
        return jsonify({'status': 'error', 'message': f"خطا در ارتباط با سایت هنگام آپلود: {e}"}), 502
    except Exception as e:
        print(f"خطای ناشناخته در آپلود: {e}", file=sys.stderr)
        return jsonify({'status': 'error', 'message': f"یک خطای ناشناخته در سرور پایتون رخ داد: {e}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
