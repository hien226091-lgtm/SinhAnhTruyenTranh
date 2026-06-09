// studio.js (ES module)

const state = {
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

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = 'toast';
  if (type === 'error') toast.style.background = '#dc2626'; 
  
  toast.innerHTML = `
    <span style="font-size: 18px;">${type === 'success' ? '✓' : '⚠'}</span>
    <span>${message}</span>
  `;
  
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

/* -------------------------------
   Progress UI (Chuyển bước)
   -------------------------------*/
function setStep(step) {
  state.step = Math.max(1, Math.min(state.totalSteps, step));
  
  $$('.wizard-step').forEach(el => {
    const s = Number(el.getAttribute('data-step') || el.id.split('-')[1]);
    if (s === state.step) {
      el.classList.add('active');
      el.setAttribute('aria-hidden', 'false');
    } else {
      el.classList.remove('active');
      el.setAttribute('aria-hidden', 'true');
    }
  });

  $$('.step-item').forEach(item => {
    item.classList.toggle('active', Number(item.dataset.step) <= state.step);
  });
}

/* -------------------------------
   Wizard Controls (Logic các nút)
   -------------------------------*/
function bindWizardControls() {
  // BƯỚC 1: XÁC NHẬN KỊCH BẢN
  $('#next1')?.addEventListener('click', async (e) => {
    const btn = e.target;
    state.scriptText = $('#scriptText').value.trim();
    
    if (!state.scriptText) {
        showToast('Vui lòng nhập hoặc tải file kịch bản!', 'error');
        return;
    }

    setButtonLoading(btn, true, 'Đang lưu dữ liệu...');
    await new Promise(r => setTimeout(r, 400)); 
    
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
    const btn = e.target;
    try {
      const raw = $('#layoutEditor').value.trim();
      state.layoutJson = raw ? JSON.parse(raw) : null;
    } catch (err) {
      showToast('Cấu trúc JSON không hợp lệ. Vui lòng kiểm tra lại!', 'error');
      return; 
    }

    setButtonLoading(btn, true, 'Đang xác thực bộ khung...');
    await new Promise(r => setTimeout(r, 400));
    
    setButtonLoading(btn, false, 'Hoàn tất ✓');
    btn.style.background = 'var(--success)';
    showToast('Lưu bộ khung thành công!', 'success');
    
    setTimeout(() => {
      setStep(3);
      btn.textContent = 'Xác nhận & Lưu bộ khung';
      btn.style.background = '';
    }, 800);
  });

  // BƯỚC 3: PHÂN TÍCH API THỰC TẾ
  $('#next3')?.addEventListener('click', async (e) => {
    const btn = e.target;
    setButtonLoading(btn, true, 'AI đang phân tích kịch bản & nhân vật...');
    
    const ok = await analyzeScriptInStudio();
    
    if (ok) {
      setButtonLoading(btn, false, 'Hoàn tất ✓');
      btn.style.background = 'var(--success)';
      showToast('Phân tích thành công! Đang chuyển sang xem khung truyện...', 'success');
      
      setTimeout(() => {
        setStep(4);
        btn.textContent = 'Xác nhận & Phân tích nhân vật';
        btn.style.background = '';
      }, 1000);
    } else {
      setButtonLoading(btn, false);
    }
  });

  $('#prev2')?.addEventListener('click', () => setStep(1));
  $('#prev3')?.addEventListener('click', () => setStep(2));
  $('#prev4')?.addEventListener('click', () => setStep(3));
}

/* -------------------------------
   API Calls
   -------------------------------*/
async function analyzeScriptInStudio() {
  if (!state.scriptText || !state.scriptText.trim()) {
    showToast('Vui lòng nhập kịch bản trước khi phân tích.', 'error');
    return false;
  }
  setStudioStatus('AI đang phân tích kịch bản...', false);
  
  try {
    const payload = { 
        text: state.scriptText, 
        frames: state.layoutJson && state.layoutJson.panels ? state.layoutJson.panels.length : 4, 
        character_description: '' 
    };
    
    const res = await fetch('/api/comic/phan_tich_kich_ban', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify(payload)
    });
    
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showToast('Phân tích thất bại: ' + (data.detail || 'Lỗi server'), 'error');
      return false;
    }
    
    const panels = Array.isArray(data.panels) ? data.panels : [];
    state.frames = panels.map((p, idx) => ({
      FrameOrder: idx + 1,
      ImageDescription: p.mo_ta_hinh_anh || '',
      GenerationStatus: 'Chưa render',
      GeneratedImageUrl: '',
      panelData: p,
    }));
    
    renderFrames();
    setStudioStatus('Phân tích hoàn tất. Kiểm tra khung và nhấn "Gửi tới AI để vẽ".', false);
    return true;
  } catch (err) {
    console.error('Analyze error', err);
    showToast('Lỗi kết nối khi gọi API phân tích.', 'error');
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
    setStudioStatus('Đã sinh khung truyện thành công!', false);
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
  const container = $('#framesGrid');
  if (!container) return;
  container.innerHTML = '';
  
  if (!state.frames || state.frames.length === 0) {
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.justifyContent = 'center';
    container.innerHTML = '<div class="muted" style="width:100%; text-align:center;">Grid khung truyện sẽ hiển thị ở đây sau khi phân tích AI...</div>';
    return;
  }

  container.style.display = ''; 
  container.style.alignItems = '';
  container.style.justifyContent = '';

  state.frames.forEach((f, idx) => {
    const card = document.createElement('div');
    card.className = 'frame-card';
    card.style = 'background:var(--muted-surface); border-radius:12px; padding:16px; display:flex; flex-direction:column; gap:12px; border: 1px solid var(--border);';
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong>Khung ${idx+1}</strong>
        <span style="font-size:12px; padding:4px 8px; background:var(--surface); border-radius:4px; border:1px solid var(--border);">${f.GenerationStatus}</span>
      </div>
      <div style="width:100%; height:200px; background:var(--surface); border-radius:8px; display:flex; align-items:center; justify-content:center; border:1px dashed var(--border); overflow:hidden;">
         ${f.GeneratedImageUrl ? `<img src="${f.GeneratedImageUrl}" style="width:100%; height:100%; object-fit:cover;" />` : '<span style="color:var(--text-muted); font-size:24px;">🖼️</span>'}
      </div>
      <textarea class="monospace" style="min-height:80px; padding:8px;" readonly>${escapeHtml(f.ImageDescription)}</textarea>
    `;
    container.appendChild(card);
  });
}

async function renderAccountArea() {
  const accountArea = document.querySelector('.account-area');
  if (!accountArea) return;
  
  const token = localStorage.getItem('access_token');
  if (!token) return; 

  try {
    const res = await fetch('/api/auth/me', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!res.ok) return; 
    
    const data = await res.json();
    const name = data.fullname || data.username || data.email || 'User';
    const initials = name.split(/\s+/).map(s=>s[0]).slice(0,2).join('').toUpperCase();
    
    accountArea.innerHTML = `
      <button id="accountBtn" class="avatar-btn" title="${name}">
        <span class="avatar-initials">${initials}</span>
      </button>
    `;
    
    document.getElementById('accountBtn')?.addEventListener('click', () => {
      if(confirm('Bạn có muốn đăng xuất khỏi AuraComic Studio?')){ 
        localStorage.removeItem('access_token'); 
        window.location.reload(); 
      }
    });
  } catch(err) { 
    console.error('Auth error', err); 
  }
}

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