document.addEventListener('DOMContentLoaded', async () => {
    // --- انتخاب تمام المان‌های لازم (بدون تغییر) ---
    const form = document.getElementById('upload-form');
    const categorySelect = document.getElementById('ik_category');
    const fileInput = document.getElementById('ik_svg_file');
    const englishNameInput = document.getElementById('ik_icon_name');
    const tagsInput = document.getElementById('ik_tags');
    const aiBtn = document.getElementById('generate-ai-btn');
    const submitBtn = document.getElementById('submit-btn');
    const requiredInputs = document.querySelectorAll('.required');
    const titleInput = document.getElementById('ik_title');
    const descriptionInput = document.getElementById('ik_description');

    // --- بارگذاری اولیه دسته‌بندی‌ها با fetch (بدون تغییر) ---
    try {
        const response = await fetch('/api/get_categories');
        if (!response.ok) throw new Error('Network response was not ok');
        const categories = await response.json();
        
        categorySelect.innerHTML = '<option value="">یک دسته‌بندی انتخاب کنید</option>';
        if (Object.keys(categories).length > 0) {
            for (const id in categories) {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = categories[id];
                categorySelect.appendChild(option);
            }
        }
    } catch (error) {
        updateStatus('خطا در دریافت دسته‌بندی‌ها از سایت.', 'error');
    }

    // --- توابع بررسی وضعیت دکمه‌ها (بدون تغییر) ---
    const checkAiButtonState = () => {
        const fileSelected = fileInput.files.length > 0;
        const nameEntered = englishNameInput.value.trim() !== '';
        aiBtn.disabled = !(fileSelected && nameEntered);
    };

    const checkSubmitButtonState = () => {
        let allFilled = true;
        requiredInputs.forEach(input => {
            if (input.value.trim() === '') allFilled = false;
        });
        submitBtn.disabled = !allFilled;
    };

    // --- افزودن Event Listener ها (بدون تغییر) ---
    [fileInput, englishNameInput, ...requiredInputs].forEach(input => {
        input.addEventListener('input', () => {
            checkAiButtonState();
            checkSubmitButtonState();
        });
        input.addEventListener('change', () => {
            checkAiButtonState();
            checkSubmitButtonState();
        });
    });

    // --- منطق دکمه هوش مصنوعی با fetch ---
    aiBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        // <<< مرحله ۱: خواندن مقدار مدل انتخاب شده از فیلد کشویی
        const selectedModel = document.getElementById('ik_ai_model').value;

        setAiButtonLoading(true);
        updateStatus('در حال ارسال درخواست به هوش مصنوعی...', 'info');

        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = async () => {
            const base64Content = reader.result.split(',')[1];
            const fileInfo = { 'name': file.name, 'content': base64Content };

            try {
                const response = await fetch('/api/generate_ai_content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    // <<< مرحله ۲: ارسال نام مدل به همراه سایر اطلاعات
                    body: JSON.stringify({
                        file_info: fileInfo,
                        english_name: englishNameInput.value.trim(),
                        model_name: selectedModel 
                    })
                });

                const result = await response.json();

                if (result.status === 'success') {
                    titleInput.value = result.data.title;
                    descriptionInput.value = result.data.description;
                    tagsInput.value = result.data.tags;
                    updateStatus('محتوا با موفقیت تولید شد.', 'success');
                    titleInput.dispatchEvent(new Event('input'));
                    descriptionInput.dispatchEvent(new Event('input'));
                } else {
                    updateStatus(`خطا: ${result.message}`, 'error');
                }
            } catch (error) {
                updateStatus(`خطای شبکه در ارتباط با هوش مصنوعی: ${error}`, 'error');
            } finally {
                setAiButtonLoading(false);
            }
        };
        reader.onerror = () => {
            updateStatus('خطا در خواندن فایل SVG.', 'error');
            setAiButtonLoading(false);
        };
    });

    // --- منطق دکمه انتشار نهایی (بدون تغییر) ---
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        setSubmitButtonLoading(true);
        updateStatus('در حال آماده‌سازی و آپلود فایل...', 'info');

        const formData = new FormData();
        formData.append('ik_title', titleInput.value);
        formData.append('ik_icon_name', englishNameInput.value);
        formData.append('ik_description', descriptionInput.value);
        formData.append('ik_category', categorySelect.value);
        formData.append('ik_tags', tagsInput.value);
        formData.append('ik_license', document.getElementById('ik_license').value);
        formData.append('ik_svg_file', fileInput.files[0]);

        try {
            const response = await fetch('/api/upload_icon', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            updateStatus(result.message, result.status);

            if (result.status === 'success') {
                form.reset();
                document.querySelector('.file-text').textContent = 'یک فایل SVG را انتخاب کنید یا اینجا بکشید';
                checkAiButtonState();
                checkSubmitButtonState();
            }
        } catch (error) {
            updateStatus(`خطای شبکه هنگام آپلود: ${error}`, 'error');
        } finally {
            setSubmitButtonLoading(false);
        }
    });
    
    // --- توابع کمکی (بدون تغییر) ---
    function setAiButtonLoading(isLoading) {
        const btnText = aiBtn.querySelector('.ai-btn-text');
        aiBtn.disabled = isLoading;
        btnText.textContent = isLoading ? 'در حال پردازش...' : 'تولید با هوش مصنوعی';
    }

    function setSubmitButtonLoading(isLoading) {
        const btnText = submitBtn.querySelector('.btn-text');
        const spinner = submitBtn.querySelector('.spinner');
        submitBtn.disabled = isLoading;
        btnText.textContent = isLoading ? 'در حال ارسال...' : '✨ ساخت و انتشار آیکون';
        spinner.style.display = isLoading ? 'block' : 'none';
    }

    function updateStatus(message, type) {
        const statusBar = document.getElementById('status-bar');
        statusBar.textContent = message;
        statusBar.className = 'status-bar';
        if (type) {
            statusBar.classList.add(type);
        }
    }
    
    checkAiButtonState();
    checkSubmitButtonState();
});




// -------------------------------------- بخش جدید


// اسکریپت آپلودر فایل SVG
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('svgFileInput');
    const fileDummy = document.getElementById('fileDummy');
    const fileText = document.getElementById('fileText');
    
    // تابع برای نمایش وضعیت انتخاب فایل
    function showFileSelected(fileName) {
        fileDummy.classList.add('file-selected');
        fileText.textContent = `✓ فایل انتخاب شد: ${fileName}`;
        
        // انیمیشن پالس برای نشان دادن موفقیت
        fileDummy.style.animation = 'pulse 0.6s ease-in-out';
        setTimeout(() => {
            fileDummy.style.animation = '';
        }, 600);
    }
    
    // تابع برای برگرداندن به حالت اولیه
    function resetFileState() {
        fileDummy.classList.remove('file-selected');
        fileText.textContent = '📁 فایل SVG خود را اینجا بکشید یا کلیک کنید';
    }
    
    // رویداد تغییر فایل
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // بررسی فرمت فایل
            if (file.type === 'image/svg+xml' || file.name.toLowerCase().endsWith('.svg')) {
                showFileSelected(file.name);
            } else {
                alert('لطفاً فقط فایل‌های SVG انتخاب کنید!');
                fileInput.value = '';
                resetFileState();
            }
        } else {
            resetFileState();
        }
    });
    
    // رویدادهای Drag & Drop
    fileDummy.addEventListener('dragover', function(e) {
        e.preventDefault();
        fileDummy.style.borderColor = 'rgba(153, 33, 232, 0.8)';
        fileDummy.style.background = 'rgba(153, 33, 232, 0.1)';
    });
    
    fileDummy.addEventListener('dragleave', function(e) {
        e.preventDefault();
        fileDummy.style.borderColor = 'rgba(255, 255, 255, 0.4)';
        fileDummy.style.background = 'rgba(248, 249, 250, 0.15)';
    });
    
    fileDummy.addEventListener('drop', function(e) {
        e.preventDefault();
        fileDummy.style.borderColor = 'rgba(255, 255, 255, 0.4)';
        fileDummy.style.background = 'rgba(248, 249, 250, 0.15)';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'image/svg+xml' || file.name.toLowerCase().endsWith('.svg')) {
                fileInput.files = files;
                showFileSelected(file.name);
            } else {
                alert('لطفاً فقط فایل‌های SVG بکشید!');
            }
        }
    });
    
    // کلیک روی منطقه فایل
    fileDummy.addEventListener('click', function() {
        fileInput.click();
    });
});

// اضافه کردن استایل انیمیشن پالس
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.02);
            box-shadow: 0 0 0 10px rgba(40, 167, 69, 0.3);
        }
        100% {
            transform: scale(1);
        }
    }
`;
document.head.appendChild(style);
