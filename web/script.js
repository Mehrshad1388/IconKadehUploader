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

    // --- بارگذاری اولیه دسته‌بندی‌ها (بدون تغییر) ---
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

    // --- منطق دکمه هوش مصنوعی (بدون تغییر) ---
    aiBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

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

    // --- منطق دکمه انتشار نهایی (تغییر یافته) ---
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        setSubmitButtonLoading(true);
        updateStatus('در حال آماده‌سازی و آپلود فایل...', 'info');

        const formData = new FormData();
        // افزودن اطلاعات قبلی
        formData.append('ik_title', titleInput.value);
        formData.append('ik_icon_name', englishNameInput.value);
        formData.append('ik_description', descriptionInput.value);
        formData.append('ik_category', categorySelect.value);
        formData.append('ik_tags', tagsInput.value);
        formData.append('ik_license', document.getElementById('ik_license').value);
        formData.append('ik_svg_file', fileInput.files[0]);

        // *** بخش جدید: افزودن وضعیت چک‌باکس‌ها به درخواست ***
        formData.append('ik_capability_color', document.getElementById('ik_capability_color').checked);
        formData.append('ik_capability_size', document.getElementById('ik_capability_size').checked);
        formData.append('ik_capability_weight', document.getElementById('ik_capability_weight').checked);

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
                // برگرداندن چک‌باکس‌ها به حالت پیش‌فرض
                document.getElementById('ik_capability_color').checked = true;
                document.getElementById('ik_capability_size').checked = true;
                document.getElementById('ik_capability_weight').checked = true;
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
