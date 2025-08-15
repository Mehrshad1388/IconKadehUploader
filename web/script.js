document.addEventListener('DOMContentLoaded', async () => {
    // --- انتخاب تمام المان‌های لازم ---
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
    const fileDummy = document.querySelector('.file-dummy');
    const fileText = document.querySelector('.file-text');
    const originalFileText = fileText.textContent;

    // --- بارگذاری اولیه دسته‌بندی‌ها با Eel ---
    try {
        const categories = await eel.get_categories()();
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
        updateStatus('خطا در دریافت دسته‌بندی‌ها. از اجرای صحیح بک‌اند مطمئن شوید.', 'error');
    }

    // --- تابع مدیریت ظاهر کادر آپلود ---
    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            fileDummy.classList.add('file-selected');
            fileText.textContent = fileInput.files[0].name;
        } else {
            fileDummy.classList.remove('file-selected');
            fileText.textContent = originalFileText;
        }
    }

    // --- توابع بررسی وضعیت دکمه‌ها ---
    const checkAiButtonState = () => {
        aiBtn.disabled = !(fileInput.files.length > 0 && englishNameInput.value.trim() !== '');
    };
    const checkSubmitButtonState = () => {
        submitBtn.disabled = ![...requiredInputs].every(input => input.value.trim() !== '');
    };

    // --- افزودن Event Listener ها ---
    fileInput.addEventListener('change', handleFileSelection);
    [fileInput, englishNameInput, ...requiredInputs].forEach(input => {
        input.addEventListener('input', () => {
            checkAiButtonState();
            checkSubmitButtonState();
        });
        input.addEventListener('change', () => { // برای select ها
            checkAiButtonState();
            checkSubmitButtonState();
        });
    });

    // --- منطق دکمه هوش مصنوعی با Eel ---
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
                const result = await eel.generate_ai_content(fileInfo, englishNameInput.value.trim(), selectedModel)();
                if (result.status === 'success') {
                    titleInput.value = result.data.title;
                    descriptionInput.value = result.data.description;
                    tagsInput.value = result.data.tags;
                    updateStatus('محتوا با موفقیت تولید شد.', 'success');
                    [titleInput, descriptionInput].forEach(el => el.dispatchEvent(new Event('input')));
                } else {
                    updateStatus(`خطا: ${result.message}`, 'error');
                }
            } catch (error) {
                updateStatus(`خطای ارتباط با پایتون: ${error}`, 'error');
            } finally {
                setAiButtonLoading(false);
            }
        };
        reader.onerror = () => {
            updateStatus('خطا در خواندن فایل SVG.', 'error');
            setAiButtonLoading(false);
        };
    });

    // --- منطق دکمه انتشار نهایی با Eel ---
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        setSubmitButtonLoading(true);
        updateStatus('در حال آماده‌سازی و آپلود فایل...', 'info');

        const formData = {
            'ik_title': titleInput.value,
            'ik_icon_name': englishNameInput.value,
            'ik_description': descriptionInput.value,
            'ik_category': categorySelect.value,
            'ik_tags': tagsInput.value,
            'ik_license': document.getElementById('ik_license').value,
            'color': document.getElementById('ik_can_change_color').checked,
            'size': document.getElementById('ik_can_change_size').checked,
            'weight': document.getElementById('ik_can_change_weight').checked
        };

        const file = fileInput.files[0];
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = async () => {
            const base64Content = reader.result.split(',')[1];
            const fileInfo = { 'name': file.name, 'content': base64Content };

            try {
                const result = await eel.upload_icon(formData, fileInfo)();
                updateStatus(result.message, result.status);

                if (result.status === 'success') {
                    form.reset();
                    document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
                    fileDummy.classList.remove('file-selected');
                    fileText.textContent = originalFileText;
                    checkAiButtonState();
                    checkSubmitButtonState();
                }
            } catch (error) {
                updateStatus(`خطای ارتباط با پایتون هنگام آپلود: ${error}`, 'error');
            } finally {
                setSubmitButtonLoading(false);
            }
        };
    });
    
    // --- توابع کمکی ---
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
        if (type) statusBar.classList.add(type);
    }
    
    checkAiButtonState();
    checkSubmitButtonState();
});
