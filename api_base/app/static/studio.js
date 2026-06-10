// studio.js (ES module)

const state = {
  comic_id: null,
  step: 1,
  totalSteps: 4,
  scriptText: '',
  layoutJson: null,
  characters: [],
  frames: [],
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/* -------------------------------
   UI Helpers: Nút bấm & Thông báo
   -------------------------------*/
function setButtonLoading(btnEl, isLoading, loadingText = 'Đang xử lý...') {
  if (!btnEl) return;
  if (isLoading) {
    btnEl.dataset.originalText = btnEl.textContent;
    btnEl.textContent = loadingText;
    btnEl.disabled = true;
    btnEl.style.opacity = '0.7';
  } else {
    btnEl.textContent = btnEl.dataset.originalText || btnEl.textContent;
    btnEl.disabled = false;
    btnEl.style.opacity = '1';
  }
}

function setStudioStatus(message, isError = false) {
  const el = document.getElementById('studioStatus');
  if (!el) return;
  el.textContent = message || '';
  el.style.color = isError ? 'var(--danger)' : 'var(--text-muted)';
  el.style.fontWeight = isError ? '600' : '400';
}

// Thay thế hàm showToast trong studio.js
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast'; // Class này sẽ ăn theo CSS mới
    
    // Nếu có lỗi, đổi màu đỏ
    if (type === 'error') {
        toast.style.backgroundColor = '#ef4444 !important'; 
    }

    toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠'}</span> <span>${message}</span>`;
    container.appendChild(toast);

    // Kích hoạt animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Tự xóa sau 3 giây
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 2500);
}

function showSuccess(message) {
    // Gọi hàm showToast cũ nhưng ép kiểu 'success'
    showToast(message, 'success');
}

/* -------------------------------
   Progress UI (Chuyển bước)
   -------------------------------*/
function setStep(targetStep) {
    // 1. Kiểm tra an toàn trước khi xử lý
    if (targetStep === 2 && !progress.step1Done) {
        showToast('Hãy hoàn thành Bước 1 (Kịch bản) trước nhé!', 'error');
        return;
    }
    if (targetStep === 3 && !progress.step2Done) {
        showToast('Hãy hoàn thành Bước 2 (Bộ khung) trước nhé!', 'error');
        return;
    }
    if (targetStep === 4 && !progress.step3Done) {
        showToast('Hãy phân tích nhân vật ở Bước 3 trước nhé!', 'error');
        return;
    }

    // 2. Nếu đã an toàn, mới tiến hành thay đổi giao diện
    // Xóa active của TẤT CẢ các bước
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.remove('active'));
    
    // Thêm active vào bước mục tiêu
    const targetEl = document.getElementById(`step-${targetStep}`);
    if (targetEl) {
        targetEl.classList.add('active');
    }

    // Cập nhật thêm cho phần Tab header (nếu bạn có danh sách tab trên đầu)
    document.querySelectorAll('.step-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`.step-item[data-step="${targetStep}"]`)?.classList.add('active');
}

/* -------------------------------
   Wizard Controls (Logic các nút)
   -------------------------------*/
// Khai báo trạng thái tiến trình (đặt ở đầu file hoặc cùng chỗ với biến state)
const progress = {
    step1Done: false, // Kịch bản
    step2Done: false, // Layout
    step3Done: false  // Nhân vật
};

function bindWizardControls() {
  // BƯỚC 1: XÁC NHẬN KỊCH BẢN
  $('#next1')?.addEventListener('click', async (e) => {
    if (!checkAuth()) return;
    const btn = e.target;
    state.scriptText = $('#scriptText').value.trim();
    
    if (!state.scriptText) {
        showToast('Vui lòng nhập hoặc tải file kịch bản!', 'error');
        return;
    }

    setButtonLoading(btn, true, 'Đang lưu dữ liệu...');
    await new Promise(r => setTimeout(r, 400)); 
    
    progress.step1Done = true; // Đánh dấu hoàn thành bước 1
    setButtonLoading(btn, false, 'Hoàn tất ✓');
    btn.style.background = 'var(--success)';
    showToast('Lưu kịch bản thành công!', 'success');
    
    setTimeout(() => {
      setStep(2);
      btn.textContent = 'Xác nhận & Phân tích kịch bản'; 
      btn.style.background = '';
    }, 800);
  });

  // BƯỚC 2: XÁC NHẬN BỘ KHUNG (LAYOUT)
  $('#next2')?.addEventListener('click', async (e) => {
    if (!checkAuth()) return;
    
    // Kiểm tra bước 1
    const raw = $('#layoutEditor').value.trim();
    if (!raw) {
        showToast('Vui lòng nhập hoặc tải file JSON bộ khung!', 'error');
        return; 
    }

    const btn = e.target;
    try {
      const raw = $('#layoutEditor').value.trim();
      state.layoutJson = raw ? JSON.parse(raw) : null;
    } catch (err) {
      showToast('Cấu trúc JSON không hợp lệ!', 'error');
      return; 
    }

    setButtonLoading(btn, true, 'Đang xác thực bộ khung...');
    await new Promise(r => setTimeout(r, 400));
    
    progress.step2Done = true; // Đánh dấu hoàn thành bước 2
    setButtonLoading(btn, false, 'Hoàn tất ✓');
    btn.style.background = 'var(--success)';
    showToast('Lưu bộ khung thành công!', 'success');
    
    setTimeout(() => {
      setStep(3);
      btn.textContent = 'Xác nhận & Lưu bộ khung';
      btn.style.background = '';
    }, 800);
  });

  // BƯỚC 3: PHÂN TÍCH API VÀ LƯU NHÂN VẬT VÀO CSDL
  $('#next3')?.addEventListener('click', async (e) => {
    if (!checkAuth()) return;

    // Kiểm tra mảng lưu trữ nhân vật trong state thay vì đếm trên giao diện
    if (!state.characters || state.characters.length === 0) {
        showToast('Bạn chưa tải ảnh nhân vật nào! Hãy tải lên ít nhất 1 ảnh.', 'error');
        return;
    }

    const btn = e.target;
    setButtonLoading(btn, true, 'AI đang phân tích...');
    
    // 1. Gọi phân tích kịch bản trước để Backend tạo truyện và cấp mã state.comic_id
    const ok = await analyzeScriptInStudio();
    
    if (ok && state.comic_id) {
        // Cập nhật trạng thái loading để user biết đang lưu dữ liệu vào MySQL
        setButtonLoading(btn, true, 'Đang lưu ảnh nhân vật vào cơ sở dữ liệu...');
        
        // 2. Tạo FormData để đóng gói danh sách file ảnh gửi lên API
        const formData = new FormData();
        formData.append('session_id', 'default');
        formData.append('comic_id', state.comic_id); // Truyền mã truyện vừa tạo để lưu đúng khóa ngoại
        
        state.characters.forEach(ch => {
            if (ch.file) {
                formData.append('files', ch.file); // Đẩy từng file ảnh vào mảng gửi đi
            }
        });

        try {
            // 3. Gọi API upload nhân vật thực tế để lưu đường dẫn vào bảng 'characters'
            const res = await fetch('/api/comic/upload-nhan-vat', {
                method: 'POST',
                headers: {
                  // THÊM DÒNG NÀY VÀO ĐỂ CÓ CHÌA KHÓA
                  'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                },
                body: formData // Không set Header Content-Type vì FormData tự động cấu hình multipart/form-data
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({detail: 'Máy chủ từ chối lưu trữ dữ liệu.'}));
                throw new Error('Máy chủ từ chối lưu trữ dữ liệu nhân vật.');
            }
            
            // Nếu cả phân tích kịch bản và lưu nhân vật đều thành công
            progress.step3Done = true; 
            setButtonLoading(btn, false, 'Hoàn tất ✓');
            btn.style.background = 'var(--success)';
            showToast('Phân tích kịch bản và lưu nhân vật thành công!', 'success');
            
            setTimeout(() => {
                setStep(4);
                btn.textContent = 'Xác nhận & Phân tích nhân vật';
                btn.style.background = '';
            }, 1000);

        } catch (err) {
            console.error('Upload character error:', err);
            showToast(`Lỗi đồng bộ Database: ${err.message}`, 'error');
            setButtonLoading(btn, false);
        }
    } else {
        setButtonLoading(btn, false);
    }
  });

// BƯỚC 4: RENDER
$('#renderBtn')?.addEventListener('click', async () => {
    if (!checkAuth()) return; 
    
    if (!progress.step3Done) {
        showToast('Khoan đã! Bạn cần hoàn thành Bước 3 (Phân tích kịch bản) trước khi yêu cầu AI vẽ ảnh nhé.', 'error');
        return;
    }

    // 1. Giao diện xoay xoay ở giữa
    startRenderingProcess();
    
    // 2. CẬP NHẬT TRẠNG THÁI GÓC TRÁI DƯỚI: Báo đang vẽ
    setStudioStatus('⏳ AI đang miệt mài vẽ tranh, bạn chờ một chút nhé...', false);
    
    try {
        const formattedPanels = (state.frames || []).map(frame => {
            const pData = frame.panelData || {};
            return {
                mo_ta_hinh_anh: frame.ImageDescription || pData.mo_ta_hinh_anh || "", 
                thoai_trai: pData.thoai_trai || "...",
                thoai_phai: pData.thoai_phai || "...",
                sfx: pData.sfx || "",
                aspect_ratio: pData.aspect_ratio || "1:1",
                image_size: pData.image_size || "1024x1024"
            };
        });

        // ---> QUAN TRỌNG: GỬI KÈM COMIC_ID XUỐNG SERVER <---
        const payload = {
            comic_id: state.comic_id, 
            session_id: "default",
            character_description: "", 
            panels: formattedPanels 
        };
        // ----------------------------------------------------

        const response = await fetch('/api/comic/san_xuat', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Lỗi kết nối tới máy chủ vẽ ảnh.');
        }
        
        const data = await response.json();
        
        renderResults(data.images || []); 
        showToast('Tuyệt vời! AI đã vẽ xong toàn bộ khung truyện.', 'success');

        // 3. CẬP NHẬT TRẠNG THÁI GÓC TRÁI DƯỚI: Báo thành công
        setStudioStatus('✅ Đã vẽ truyện thành công! Bạn có thể chọn ảnh để tải PDF.', false);

    } catch (err) {
        console.error('Render error:', err);
        showToast(`Sự cố khi vẽ: ${err.message}`, 'error');

        // 4. CẬP NHẬT TRẠNG THÁI GÓC TRÁI DƯỚI: Báo lỗi màu đỏ
        setStudioStatus('❌ Quá trình vẽ bị gián đoạn. Vui lòng thử lại!', true);

        document.getElementById('framesGrid').innerHTML = `
            <div style="padding: 30px; text-align: center; border: 2px dashed #ef4444; border-radius: 12px; background: #fef2f2;">
                <h3 style="color: #ef4444; margin-bottom: 10px;">Rất tiếc, quá trình vẽ ảnh gặp sự cố!</h3>
                <p style="color: #555;"><strong>Lý do:</strong> ${err.message}</p>
                <p style="color: #555; margin-top: 10px;">Bạn đừng lo, hệ thống đã lưu lại kịch bản. Hãy thử nhấn nút <strong>"Gửi tới AI để vẽ"</strong> lại một lần nữa nhé.</p>
            </div>
        `;
    }
});

  // CÁC NÚT QUAY LẠI (Giữ nguyên)
  $('#prev2')?.addEventListener('click', () => setStep(1));
  $('#prev3')?.addEventListener('click', () => setStep(2));
  $('#prev4')?.addEventListener('click', () => setStep(3));
}


async function analyzeScriptInStudio() {
  if (!state.scriptText || !state.scriptText.trim()) {
    showToast('Vui lòng nhập kịch bản trước khi phân tích.', 'error');
    return false;
  }
  
  // 1. Lấy token an toàn
  const token = localStorage.getItem('access_token');
  if (!token) {
    showToast('Bạn chưa đăng nhập. Vui lòng đăng nhập để tiếp tục!', 'warning');
    window.location.href = '/login.html';
    return false;
  }

  setStudioStatus('AI đang phân tích kịch bản...', false);
  
  try {
    const payload = { 
        text: state.scriptText, 
        frames: state.layoutJson && state.layoutJson.panels ? state.layoutJson.panels.length : 4, 
        character_description: '',
        layout_json: state.layoutJson ? JSON.stringify(state.layoutJson) : null 
    };
    
    // 2. Gọi API với headers chuẩn
    const res = await fetch('/api/comic/phan_tich_kich_ban', {
      method: 'POST', 
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      }, 
      body: JSON.stringify(payload)
    });
    
    // 3. Xử lý phản hồi
    if (res.status === 401 || res.status === 403) {
      showToast('Phiên đăng nhập hết hạn hoặc không có quyền. Vui lòng đăng nhập lại.', 'error');
      localStorage.removeItem('access_token'); // Xóa token hỏng
      window.location.href = '/login.html';
      return false;
    }

    const data = await res.json().catch(() => ({}));
    
    if (!res.ok) {
      showToast('Phân tích thất bại: ' + (data.detail || 'Lỗi server'), 'error');
      return false;
    }

    // 4. Cập nhật trạng thái thành công
    if (data.comic_id) state.comic_id = data.comic_id;
    
    const panels = Array.isArray(data.panels) ? data.panels : [];
    state.frames = panels.map((p, idx) => ({
      FrameOrder: idx + 1,
      ImageDescription: p.mo_ta_hinh_anh || '',
      GenerationStatus: 'Chưa render',
      GeneratedImageUrl: '',
      panelData: p,
    }));
    
    renderFrames();
    setStudioStatus('Phân tích hoàn tất!', false);
    return true;

  } catch (err) {
    console.error('Analyze error', err);
    showToast('Lỗi kết nối server.', 'error');
    return false;
  }
}

async function sendToBackendForRender() {
  const btn = $('#renderBtn');
  setButtonLoading(btn, true, 'AI đang vẽ...');
  setStudioStatus('Đang gửi yêu cầu sinh ảnh đến server...', false);

  const payload = {
    script: state.scriptText,
    layout: state.layoutJson,
    characters: state.characters.map(c => ({ name: c.name })),
  };

  try {
    const res = await fetch('/api/produce', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const j = await res.json().catch(()=>({ error: 'Server error' }));
      showToast('Lỗi từ server: ' + (j.error || JSON.stringify(j)), 'error');
      setStudioStatus('Render thất bại.', true);
      return;
    }
    
    const data = await res.json();
    state.frames = Array.isArray(data.frames) ? data.frames : [];
    renderFrames();
    setStudioStatus('Đã sinh khung truyện thành công! Bạn hãy đợi AI vẽ nhé....', false);
    showToast('Render ảnh thành công!', 'success');

  } catch (err) {
    console.error('Render error', err);
    setStudioStatus('Lỗi kết nối khi gọi backend.', true);
    showToast('Lỗi mạng. Vui lòng thử lại.', 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

async function exportProduction() {
  if (!state.frames || state.frames.length === 0) {
    showToast('Chưa có khung nào để xuất. Vui lòng tạo khung trước.', 'error');
    return;
  }
  
  const btn = $('#exportBtn');
  setButtonLoading(btn, true, 'Đang xuất...');
  setStudioStatus('Đang đóng gói và xuất xưởng truyện...', false);
  
  try {
    const panels = state.frames.map(f => ({
      mo_ta_hinh_anh: f.ImageDescription || '',
      thoai_trai: (f.panelData && f.panelData.thoai_trai) || '...',
      thoai_phai: (f.panelData && f.panelData.thoai_phai) || '...',
      sfx: (f.panelData && f.panelData.sfx) || '',
      aspect_ratio: (f.panelData && f.panelData.aspect_ratio) || '16:9',
      image_size: (f.panelData && f.panelData.image_size) || '2K',
    }));

    const res = await fetch('/api/comic/san_xuat', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ panels, character_description: '' })
    });
    
    const data = await res.json().catch(()=>({}));
    if (!res.ok) {
      setStudioStatus('Xuất xưởng thất bại: ' + (data.detail || 'Lỗi server'), true);
      showToast('Xuất xưởng thất bại!', 'error');
      return;
    }

    const results = document.getElementById('studioResults');
    if (results) {
        results.innerHTML = '';
        (data.images || []).forEach((url, idx) => {
          const div = document.createElement('div');
          div.innerHTML = `<img src="${url}" style="width:100%; border-radius:8px; margin-bottom:12px; box-shadow:var(--shadow-sm);" alt="Kết quả ${idx+1}" />`;
          results.appendChild(div);
        });
    }

    setStudioStatus(`Hoàn tất xuất xưởng ${data.images ? data.images.length : 0} trang truyện!`, false);
    showToast('Xuất xưởng thành công!', 'success');
  } catch (err) {
    console.error('Export error', err);
    setStudioStatus('Lỗi khi gọi API xuất xưởng.', true);
    showToast('Lỗi API xuất xưởng.', 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

/* -------------------------------
   Drag & Drop & File Handlers
   -------------------------------*/
function makeDropzone(container, options = {}) {
  if (!container) return;
  const input = container.querySelector('input[type="file"]');
  if (!input) return;

  const accept = container.dataset.accept || options.accept || '*/*';
  const multiple = container.dataset.multiple === 'true' || options.multiple || false;

  input.accept = accept;
  input.multiple = multiple;

  input.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    const nameSpan = container.querySelector('.no-file');
    if (nameSpan) {
      nameSpan.textContent = files.length === 0 ? 'Hoặc kéo thả vào đây' : (files.length === 1 ? files[0].name : `${files.length} file đã chọn`);
    }
    handleFiles(container, files);
    input.value = ''; 
  });

  ['dragenter', 'dragover'].forEach(evt => {
    container.addEventListener(evt, (e) => {
      e.preventDefault(); e.stopPropagation();
      container.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(evt => {
    container.addEventListener(evt, (e) => {
      e.preventDefault(); e.stopPropagation();
      container.classList.remove('drag-over');
    });
  });

  container.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (!dt) return;
    const files = Array.from(dt.files);
    const nameSpan = container.querySelector('.no-file');
    if (nameSpan) {
      nameSpan.textContent = files.length === 0 ? 'Hoặc kéo thả vào đây' : (files.length === 1 ? files[0].name : `${files.length} file đã chọn`);
    }
    handleFiles(container, files);
  });
}

function handleFiles(container, files) {
  if (container.id === 'scriptDrop') {
    const f = files[0];
    readFileAsText(f).then(txt => {
      const isJson = f.type === 'application/json' || f.name.toLowerCase().endsWith('.json');
      if (isJson) {
        try {
          const parsed = JSON.parse(txt);
          const candidate = parsed.script || parsed.text || parsed.content || parsed.body || null;
          $('#scriptText').value = (candidate && typeof candidate === 'string') ? candidate : JSON.stringify(parsed, null, 2);
        } catch (e) {
          $('#scriptText').value = txt;
        }
      } else {
        $('#scriptText').value = txt;
      }
      state.scriptText = $('#scriptText').value;
    }).catch(() => showToast('Không thể đọc file kịch bản.', 'error'));
    
  } else if (container.id === 'layoutDrop') {
    const f = files[0];
    readFileAsText(f).then(txt => {
      $('#layoutEditor').value = txt;
      try { state.layoutJson = JSON.parse(txt); } catch(e) { state.layoutJson = null; }
    }).catch(() => showToast('Không thể đọc file layout JSON.', 'error'));
    
  } else if (container.id === 'charactersDrop') {
    files.forEach(file => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        state.characters.push({
          id: Date.now() + Math.random(),
          name: file.name,
          file,
          thumb: ev.target.result,
        });
        renderCharacters();
      };
      reader.readAsDataURL(file);
    });
  }
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    if (!file) return reject('No file');
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file, 'utf-8');
  });
}

/* -------------------------------
   Renders (HTML)
   -------------------------------*/
function renderCharacters() {
  const grid = $('#charactersGrid');
  if (!grid) return;
  grid.innerHTML = '';
  if (state.characters.length === 0) {
    grid.innerHTML = '<div class="muted">Chưa có ảnh nhân vật nào.</div>';
    return;
  }
  state.characters.forEach(ch => {
    const el = document.createElement('div');
    el.className = 'character-card';
    el.style = 'width:120px; background:var(--muted-surface); border-radius:12px; padding:10px; display:flex; flex-direction:column; gap:8px; align-items:center; border: 1px solid var(--border);';
    el.innerHTML = `
      <img src="${ch.thumb}" alt="${escapeHtml(ch.name)}" style="width:100%; height:100px; object-fit:cover; border-radius:8px;" />
      <div style="font-size:12px; width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:center;">${escapeHtml(ch.name)}</div>
      <button class="btn small" style="width:100%; justify-content:center; color:var(--danger); border-color:var(--danger);" data-remove="${ch.id}">Xóa</button>
    `;
    grid.appendChild(el);
    el.querySelector('[data-remove]')?.addEventListener('click', () => {
      state.characters = state.characters.filter(x => x.id !== ch.id);
      renderCharacters();
    });
  });
}

function renderFrames() {
  const container = document.getElementById('framesGrid');
  if (!container) return;

  // Căn giữa nội dung và tạo khung đứt nét cho đẹp
  container.style.display = 'block';
  container.style.textAlign = 'center';
  
  // Hiển thị thông báo sẵn sàng thay vì vẽ các khung JSON
  container.innerHTML = `
    <div id="promptPlaceholder" style="padding: 40px; border: 2px dashed var(--border); border-radius: 16px; background: var(--muted-surface);">
        <h3 style="color: var(--text-main); margin-bottom: 10px;">✨ Phân tích hoàn tất! ✨</h3>
        <p class="muted" style="font-size: 1.1em;">AI đã nắm bắt kịch bản, bộ khung và nhân vật của bạn.</p>
        <p class="muted">Nhấn nút <strong>"Gửi tới AI để vẽ"</strong> bên dưới để bắt đầu quá trình tạo truyện ngay nhé.</p>
    </div>
    <div id="studioResults" class="result-grid" style="display: none; margin-top: 20px;"></div>
  `;
}

async function renderAccountArea() {
  const accountArea = document.querySelector('.account-area');
  if (!accountArea) return;
  
  const token = localStorage.getItem('access_token');
  if (!token) return; 

  try {
    const res = await fetch('/api/auth/me', { 
      headers: { 'Authorization': 'Bearer ' + token } 
    });
    if (!res.ok) return; 
    
    const data = await res.json();
    const name = data.fullname || data.username || data.email || 'User';
    const initials = name.split(/\s+/).map(s=>s[0]).slice(0,2).join('').toUpperCase();
    
    // Render nội dung
    accountArea.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-weight: 600; color: var(--text-main);">${escapeHtml(name)}</span>
        <button id="accountBtn" class="avatar-btn" title="Đăng xuất khỏi ${escapeHtml(name)}">
          <span class="avatar-initials">${initials}</span>
        </button>
      </div>
    `;
    
    // Gắn sự kiện mở Modal (chỉ gắn 1 lần)
    document.getElementById('accountBtn').onclick = () => {
        document.getElementById('logoutModal').style.display = 'flex';
    };

  } catch(err) { 
    console.error('Auth error', err); 
  }
}

// Đưa logic Modal ra ngoài hàm renderAccountArea để chỉ gắn 1 lần duy nhất
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('cancelLogout')?.addEventListener('click', () => {
        document.getElementById('logoutModal').style.display = 'none';
    });

    document.getElementById('confirmLogout')?.addEventListener('click', () => {
        localStorage.removeItem('access_token');
        window.location.reload();
    });
});

function escapeHtml(s=''){
  return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[ch]);
}

/* -------------------------------
   Initialization
   -------------------------------*/
function init() {
  setStep(1);
  bindWizardControls();
  
  $('#renderBtn')?.addEventListener('click', () => {
    if (!state.scriptText) { showToast('Vui lòng phân tích kịch bản trước khi Render.', 'error'); return; }
    sendToBackendForRender();
  });

  $('#exportBtn')?.addEventListener('click', exportProduction);

  makeDropzone($('#scriptDrop'));
  makeDropzone($('#layoutDrop'));
  makeDropzone($('#charactersDrop'));
  
  renderCharacters();
  renderFrames();
  renderAccountArea();

  const toggle = document.getElementById('toggleTheme');
  if (toggle) {
    toggle.addEventListener('click', () => {
      document.getElementById('app')?.classList.toggle('theme-dark');
      document.getElementById('app')?.classList.toggle('theme-light');
    });
  }
}

window.Studio = { init };
document.addEventListener('DOMContentLoaded', () => { 
    try { 
        window.Studio.init(); 
    } catch(e) { 
        console.error('Studio init error', e); 
    } 
});

// Thêm biến state để lưu ảnh được chọn
state.selectedImages = [];

// Hàm hiển thị kết quả cuối cùng với trạng thái Loading
function renderResults(imageUrls) {
    const grid = document.getElementById('framesGrid');
    
    // 1. Chuyển sang trạng thái kết quả
    grid.innerHTML = `
        <div id="resultsContainer" class="result-container" style="width: 100%;">
            <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 10px;">
                <button id="exportPdfBtn" class="btn primary" style="background: var(--success, #28a745); color: white; border: none;">Tải xuống PDF (các ảnh đã chọn)</button>
            </div>
            
            <div id="imageGallery" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; width: 100%; padding: 10px; align-items: start;"></div>
        </div>
    `;

    // 2. Chèn các ảnh vào lưới
    const gallery = document.getElementById('imageGallery');
    imageUrls.forEach((url) => {
        const div = document.createElement('div');
        div.className = 'result-image-wrapper';
        
        // Ghi đè toàn bộ CSS thừa (bỏ viền xanh, bỏ background) để khung ôm sát ảnh
        div.style = 'width: 100%; cursor: pointer; transition: all 0.2s ease; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.15); border: none !important; padding: 0 !important; background: transparent !important; margin: 0;';
        
        div.innerHTML = `
            <img src="${url}" alt="Comic Frame" style="width: 100%; height: auto; display: block; border-radius: 12px; transition: opacity 0.2s ease;" />
        `;
        
        // Hiệu ứng click: Bỏ viền đỏ, đổi sang làm ảnh hơi tối đi và lún xuống
        div.onclick = () => {
            div.classList.toggle('selected');
            const img = div.querySelector('img');
            if (div.classList.contains('selected')) {
                div.style.transform = 'scale(0.95)'; // Ảnh hơi lún xuống
                img.style.opacity = '0.6'; // Ảnh tối đi một chút để báo hiệu đã chọn
            } else {
                div.style.transform = 'scale(1)'; // Trở lại bình thường
                img.style.opacity = '1';
            }
        };
        gallery.appendChild(div);
    });

    // 3. Gắn sự kiện xuất PDF
    document.getElementById('exportPdfBtn').onclick = exportToPdf;
}

/// Hàm khởi tạo trạng thái Loading khi nhấn Render
function startRenderingProcess() {
    const grid = document.getElementById('framesGrid');
    grid.innerHTML = `
        <div class="loading-state" style="text-align: center; padding: 40px; background: var(--muted-surface); border-radius: 16px; border: 1px solid var(--border);">
            <div class="spinner"></div>
            <h3 style="margin-top: 20px; font-weight: 600; color: var(--text-main);">AI đang miệt mài vẽ tranh...</h3>
            <p style="color: var(--text-muted); margin-top: 10px; font-size: 0.95em;">
                Quá trình này có thể mất vài phút để hoàn thiện từng chi tiết của khung truyện.<br>
                Bạn có thể làm một tách cà phê nhưng <strong>đừng đóng tab này</strong> nhé!
            </p>
        </div>
    `;
}


async function exportToPdf() {
    const { jsPDF } = window.jspdf;
    // Chọn tất cả các ảnh có class 'selected' (ảnh bạn đã click chọn)
    const selectedImages = document.querySelectorAll('.result-image-wrapper.selected img');
    
    if (selectedImages.length === 0) {
        alert("Vui lòng chọn ít nhất một khung truyện để xuất PDF!");
        return;
    }

    const doc = new jsPDF('p', 'mm', 'a4');
    const pageWidth = 210; // Chiều rộng khổ A4 (mm)
    const pageHeight = 297; // Chiều cao khổ A4 (mm)

    for (let i = 0; i < selectedImages.length; i++) {
        const img = selectedImages[i];
        
        // Thêm trang mới nếu không phải là trang đầu tiên
        if (i > 0) doc.addPage();

        // Tính toán tỷ lệ ảnh để nằm giữa trang
        const imgWidth = 180; // Margin mỗi bên 15mm
        const imgHeight = (img.naturalHeight * imgWidth) / img.naturalWidth;
        const x = (pageWidth - imgWidth) / 2;
        const y = (pageHeight - imgHeight) / 2;

        doc.addImage(img.src, 'PNG', x, y, imgWidth, imgHeight);
        doc.text(`Trang ${i + 1}`, 105, 290, { align: 'center' });
    }

    doc.save("AuraComic_Story.pdf");
    showToast('Đã xuất file PDF thành công!', 'success');
}

function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        // Hiện khung yêu cầu đăng nhập đã làm ở bước trước
        const loginPrompt = document.getElementById('loginPrompt');
        if (loginPrompt) {
            loginPrompt.style.display = 'flex'; // Hiện lên
        }
        return false; // Chặn code phía sau không được chạy
    }
    return true; // Cho phép tiếp tục
}

// Hàm kiểm tra và cập nhật giao diện
function checkAuthAndShowUI() {
    const token = localStorage.getItem('access_token');
    const loginPrompt = document.getElementById('loginPrompt');
    
    if (!token) {
        // Chưa đăng nhập: Hiện khung thông báo
        if (loginPrompt) loginPrompt.style.display = 'flex';
        // Vô hiệu hóa nút
        document.querySelectorAll('.process-btn, #renderBtn').forEach(btn => btn.disabled = true);
    } else {
        // ĐÃ ĐĂNG NHẬP: Ẩn khung thông báo
        if (loginPrompt) loginPrompt.style.display = 'none';
        // Kích hoạt lại nút
        document.querySelectorAll('.process-btn, #renderBtn').forEach(btn => btn.disabled = false);
    }
}

// GỌI HÀM NÀY Ở ĐÂU?
// 1. Khi trang tải xong
document.addEventListener('DOMContentLoaded', checkAuthAndShowUI);

