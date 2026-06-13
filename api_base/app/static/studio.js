// AuraComic Studio — Main Application Logic

// ============================================================
// State
// ============================================================
const state = {
  comic_id: null,
  step: 1,
  totalSteps: 4,
  comicTitle: '',
  scriptText: '',
  layoutJson: null,
  characters: [],
  frames: [],
};

const progress = { step1Done: false, step2Done: false, step3Done: false };

// ============================================================
// DOM Shortcuts
// ============================================================
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

// ============================================================
// Plan / Quota
// ============================================================
let planCache = null;

async function fetchPlanStatus() {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch('/api/comic/plan-status', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    planCache = await res.json();
    return planCache;
  } catch { return null; }
}

function renderPlanBadge(plan) {
  if (!plan) return '';
  if (plan.is_pro) return '<span style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700">PRO</span>';
  const pct = plan.limit > 0 ? Math.round((plan.used / plan.limit) * 100) : 0;
  const color = pct >= 80 ? 'var(--danger)' : pct >= 50 ? 'var(--warning)' : 'var(--success)';
  return `<span style="background:${color};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600">${plan.remaining}/${plan.limit}</span>`;
}

// ============================================================
// Token / Auth
// ============================================================
function getToken() { return localStorage.getItem('access_token'); }

function checkAuth() {
  if (getToken()) return true;
  const el = document.getElementById('loginPrompt');
  if (el) el.classList.add('show');
  showToast('Vui lòng đăng nhập trước!', 'warning');
  return false;
}

function checkAuthAndShowUI() {
  const ok = !!getToken();
  const prompt = document.getElementById('loginPrompt');
  if (prompt) prompt.classList.toggle('show', !ok);
  $$('.process-btn, #renderBtn').forEach(b => b.disabled = !ok);
  $$('.dd-area').forEach(d => d.style.opacity = ok ? '1' : '0.5');
}

document.addEventListener('DOMContentLoaded', checkAuthAndShowUI);

// ============================================================
// Toast Notifications
// ============================================================
function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  toast.innerHTML = `<span style="font-size:16px;font-weight:700">${icons[type] || 'ℹ'}</span><span>${message}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

function setStatus(message, type = 'info') {
  const el = document.getElementById('studioStatus');
  if (!el) return;
  const icons = { info: 'ℹ', error: '✕', success: '✓' };
  el.innerHTML = message ? `<span>${icons[type] || ''}</span><span>${message}</span>` : '';
  el.className = `status-bar ${type}`;
}

// ============================================================
// Button Loading State
// ============================================================
function setButtonLoading(btnEl, loading, text) {
  if (!btnEl) return;
  if (loading) {
    btnEl._origText = btnEl.textContent;
    btnEl.textContent = text || 'Đang xử lý...';
    btnEl.disabled = true;
  } else {
    btnEl.textContent = btnEl._origText || btnEl.textContent;
    btnEl.disabled = false;
  }
}

// ============================================================
// Step Navigation
// ============================================================
function setStep(target) {
  if (target === 2 && !progress.step1Done) { showToast('Hoàn thành Bước 1 trước!', 'warning'); return; }
  if (target === 3 && !progress.step2Done) { showToast('Hoàn thành Bước 2 trước!', 'warning'); return; }
  if (target === 4 && !progress.step3Done) { showToast('Phân tích kịch bản ở Bước 3 trước!', 'warning'); return; }
  state.step = target;
  $$('.wizard-step').forEach(el => el.classList.remove('active'));
  const targetEl = document.getElementById(`step-${target}`);
  if (targetEl) targetEl.classList.add('active');
  $$('.step-item').forEach(el => el.classList.remove('active'));
  const si = document.querySelector(`.step-item[data-step="${target}"]`);
  if (si) si.classList.add('active');
}

// ============================================================
// Drag & Drop / File Handling
// ============================================================
function makeDropzone(container) {
  if (!container) return;
  const input = container.querySelector('input[type="file"]');
  if (!input) return;
  input.addEventListener('change', (e) => {
    if (!checkAuth()) { e.target.value = ''; return; }
    const files = Array.from(e.target.files);
    updateDropLabel(container, files);
    handleFiles(container, files);
    input.value = '';
  });
  ['dragenter', 'dragover'].forEach(evt => {
    container.addEventListener(evt, (e) => {
      if (!getToken()) { e.preventDefault(); return; }
      e.preventDefault(); container.classList.add('drag-over');
    });
  });
  ['dragleave', 'drop'].forEach(evt => {
    container.addEventListener(evt, (e) => { e.preventDefault(); container.classList.remove('drag-over'); });
  });
  container.addEventListener('drop', (e) => {
    if (!checkAuth()) return;
    const files = Array.from(e.dataTransfer?.files || []);
    updateDropLabel(container, files);
    handleFiles(container, files);
  });
}

function updateDropLabel(container, files) {
  const span = container.querySelector('.no-file');
  if (!span) return;
  if (files.length === 0) span.textContent = 'hoặc kéo thả vào đây';
  else if (files.length === 1) span.textContent = files[0].name;
  else span.textContent = `${files.length} file đã chọn`;
}

function handleFiles(container, files) {
  const id = container.id;
  if (id === 'scriptDrop') {
    const f = files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const txt = e.target.result;
      const isJson = f.name.toLowerCase().endsWith('.json');
      if (isJson) {
        try {
          const parsed = JSON.parse(txt);
          const candidate = parsed.script || parsed.text || parsed.content || null;
          $('#scriptText').value = candidate && typeof candidate === 'string' ? candidate : JSON.stringify(parsed, null, 2);
        } catch { $('#scriptText').value = txt; }
      } else {
        $('#scriptText').value = txt;
      }
      state.scriptText = $('#scriptText').value;
    };
    reader.readAsText(f, 'utf-8');
  } else if (id === 'layoutDrop') {
    const f = files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const txt = e.target.result;
      $('#layoutEditor').value = txt;
      try { state.layoutJson = JSON.parse(txt); } catch { state.layoutJson = null; }
    };
    reader.readAsText(f, 'utf-8');
  } else if (id === 'charactersDrop') {
    files.forEach(file => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        state.characters.push({ id: Date.now() + Math.random(), name: file.name, file, thumb: ev.target.result });
        renderCharacters();
      };
      reader.readAsDataURL(file);
    });
  }
}

// ============================================================
// Render: Characters
// ============================================================
function renderCharacters() {
  const grid = document.getElementById('charactersGrid');
  if (!grid) return;
  grid.innerHTML = '';
  if (state.characters.length === 0) {
    grid.innerHTML = '<div class="muted" style="padding:12px 0">Chưa có ảnh nhân vật nào.</div>';
    return;
  }
  state.characters.forEach(ch => {
    const el = document.createElement('div');
    el.className = 'character-card';
    el.innerHTML = `
      <img src="${escHtml(ch.thumb)}" alt="${escHtml(ch.name)}" />
      <div class="name">${escHtml(ch.name)}</div>
      <button class="btn btn-sm btn-danger" style="width:100%;justify-content:center" data-remove="${ch.id}">Xóa</button>`;
    grid.appendChild(el);
    el.querySelector('[data-remove]')?.addEventListener('click', () => {
      state.characters = state.characters.filter(x => x.id !== ch.id);
      renderCharacters();
    });
  });
}

// ============================================================
// Render: Frames
// ============================================================
function renderFrames() {
  const grid = document.getElementById('framesGrid');
  if (!grid) return;
  if (!state.frames.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🎨</div>
        <p>Chưa có khung truyện. Hãy phân tích kịch bản trước.</p>
      </div>`;
    return;
  }
  const html = state.frames.map((f, i) => {
    const pd = f.panelData || {};
    return `
      <div class="frame-card" data-idx="${i}">
        <div class="frame-header">
          <span>Khung #${i + 1}</span>
          <span class="badge" style="background:var(--primary-light);color:var(--primary);padding:2px 10px;border-radius:20px;font-size:11px">${pd.aspect_ratio || '16:9'}</span>
        </div>
        <div class="frame-body">
          <textarea class="frame-desc" rows="2" placeholder="Mô tả hình ảnh...">${escHtml(f.ImageDescription || pd.mo_ta_hinh_anh || '')}</textarea>
          <div style="display:flex;gap:8px;margin-top:8px">
            <input class="form-input" style="flex:1;font-size:12px;padding:6px 10px" value="${escHtml(pd.thoai_trai || '...')}" placeholder="Thoại trái" data-field="thoai_trai" />
            <input class="form-input" style="flex:1;font-size:12px;padding:6px 10px" value="${escHtml(pd.thoai_phai || '...')}" placeholder="Thoại phải" data-field="thoai_phai" />
          </div>
          <input class="form-input" style="margin-top:8px;font-size:12px;padding:6px 10px" value="${escHtml(pd.sfx || '')}" placeholder="SFX (hiệu ứng âm thanh)" data-field="sfx" />
        </div>
      </div>`;
  }).join('');
  grid.innerHTML = `<div class="frame-list">${html}</div>`;
}

// ============================================================
// Render: Account Area
// ============================================================
async function renderAccountArea() {
  const area = document.querySelector('.account-area');
  if (!area) return;
  const token = getToken();
  if (!token) return;
  try {
    const [userRes, plan] = await Promise.all([
      fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } }),
      fetchPlanStatus(),
    ]);
    if (!userRes.ok) return;
    const data = await userRes.json();
    const name = data.fullname || data.username || data.email || 'User';
    const initials = name.split(/\s+/).map(s => s[0]).slice(0, 2).join('').toUpperCase();
    const planBadge = renderPlanBadge(plan);
    const upgradeBtn = plan && !plan.is_pro
      ? `<button id="upgradeBtn" class="btn btn-sm" style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;font-weight:700;border:none;font-size:11px;padding:4px 12px;border-radius:20px;cursor:pointer">⬆ Pro</button>`
      : '';
    area.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        ${planBadge}
        ${upgradeBtn}
        ${data.is_admin ? '<a href="/admin" style="color:var(--primary);font-size:16px" title="Admin">⚙</a>' : ''}
        <span class="user-name">${escHtml(name)}</span>
        <button id="logoutBtn" class="avatar-btn" title="Đăng xuất">
          <span>${initials}</span>
        </button>
      </div>`;
    document.getElementById('upgradeBtn')?.addEventListener('click', () => document.getElementById('upgradeModal').classList.add('show'));
    document.getElementById('logoutBtn').onclick = () => {
      document.getElementById('logoutModal').classList.add('show');
    };
  } catch { /* ignore */ }
}

// ============================================================
// Results Gallery & Export
// ============================================================
function renderResults(imageUrls) {
  const grid = document.getElementById('framesGrid');
  if (!grid) return;
  grid.innerHTML = `
    <div class="result-container">
      <div class="gallery-actions">
        <button id="selectAllBtn" class="btn btn-sm btn-outline">Chọn tất cả</button>
        <button id="deselectAllBtn" class="btn btn-sm btn-outline">Bỏ chọn</button>
        <button id="exportPdfBtn" class="btn btn-sm btn-primary">📥 Xuất PDF</button>
        <button id="exportPageBtn" class="btn btn-sm btn-primary">📄 Ghép trang</button>
      </div>
      <div id="imageGallery" class="image-gallery"></div>
    </div>`;
  const gallery = document.getElementById('imageGallery');
  imageUrls.forEach((url) => {
    const div = document.createElement('div');
    div.className = 'result-image-wrapper';
    div.innerHTML = `<img src="${url}" alt="Comic Frame" loading="lazy" />`;
    div.onclick = () => div.classList.toggle('selected');
    gallery.appendChild(div);
  });
  document.getElementById('selectAllBtn').onclick = () => $$('.result-image-wrapper', gallery).forEach(w => w.classList.add('selected'));
  document.getElementById('deselectAllBtn').onclick = () => $$('.result-image-wrapper', gallery).forEach(w => w.classList.remove('selected'));
  document.getElementById('exportPdfBtn').onclick = exportToPdf;
  document.getElementById('exportPageBtn').onclick = exportToPage;
}

function getSelectedUrls() {
  return $$('.result-image-wrapper.selected img').map(img => img.src);
}

async function exportToPdf() {
  const urls = getSelectedUrls();
  if (!urls.length) { showToast('Chọn ít nhất một ảnh!', 'warning'); return; }
  try {
    const payload = { images: urls.map(u => new URL(u).pathname) };
    const res = await fetch('/api/comic/xuat-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Export failed');
    const data = await res.json();
    window.open(data.pdf_url, '_blank');
    showToast('Đã xuất PDF thành công!', 'success');
  } catch (e) {
    showToast('Lỗi xuất PDF: ' + e.message, 'error');
  }
}

async function exportToPage() {
  const urls = getSelectedUrls();
  if (!urls.length) { showToast('Chọn ít nhất một ảnh!', 'warning'); return; }
  if (urls.length > 8) { showToast('Tối đa 8 ảnh/trang!', 'warning'); return; }
  try {
    const payload = { images: urls.map(u => new URL(u).pathname) };
    const res = await fetch('/api/comic/xuat-trang', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Compose failed');
    const data = await res.json();
    const img = document.createElement('img');
    img.src = data.page_url;
    img.style.cssText = 'max-width:100%;border-radius:12px;margin-top:16px;box-shadow:0 8px 24px rgba(0,0,0,0.12)';
    const gallery = document.getElementById('imageGallery');
    if (gallery) { gallery.innerHTML = ''; gallery.parentElement?.prepend(img); }
    showToast('Đã ghép trang thành công!', 'success');
  } catch (e) {
    showToast('Lỗi ghép trang: ' + e.message, 'error');
  }
}

function startRenderingProcess() {
  const grid = document.getElementById('framesGrid');
  grid.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <h3>AI đang miệt mài vẽ tranh...</h3>
      <p>Quá trình này có thể mất vài phút.<br><strong>Đừng đóng tab này</strong> nhé!</p>
    </div>`;
}

// ============================================================
// API: Analyze Script
// ============================================================
async function analyzeScriptInStudio() {
  if (!state.scriptText?.trim()) {
    showToast('Nhập kịch bản trước!', 'warning');
    return false;
  }
  const token = getToken();
  if (!token) { showToast('Chưa đăng nhập!', 'warning'); return false; }
  setStatus('AI đang phân tích kịch bản...', 'info');
  try {
    const framesCount = state.layoutJson?.panels?.length || 4;
    const res = await fetch('/api/comic/phan_tich_kich_ban', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        text: state.scriptText,
        frames: framesCount,
        character_description: '',
        layout_json: state.layoutJson ? JSON.stringify(state.layoutJson) : null,
        title: state.comicTitle.trim() || undefined,
      }),
    });
    if (res.status === 401 || res.status === 403) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      return false;
    }
    const data = await res.json();
    if (!res.ok) { showToast('Phân tích thất bại: ' + (data.detail || 'Lỗi server'), 'error'); return false; }
    state.comic_id = data.comic_id || null;
    const panels = Array.isArray(data.panels) ? data.panels : [];
    state.frames = panels.map((p, i) => ({ FrameOrder: i + 1, ImageDescription: p.mo_ta_hinh_anh || '', GenerationStatus: 'Chưa render', GeneratedImageUrl: '', panelData: p }));
    renderFrames();
    setStatus('Phân tích hoàn tất!', 'success');
    return true;
  } catch (err) {
    showToast('Lỗi kết nối server!', 'error');
    setStatus('Kết nối thất bại', 'error');
    return false;
  }
}

// ============================================================
// Bind Wizard Controls
// ============================================================
function bindWizardControls() {
  // Step 1 → 2
  $('#next1')?.addEventListener('click', async (e) => {
    if (!checkAuth()) return;
    const btn = e.target;
    state.scriptText = $('#scriptText').value.trim();
    state.comicTitle = $('#comicTitle')?.value?.trim() || '';
    if (!state.scriptText) { showToast('Nhập hoặc tải file kịch bản!', 'warning'); return; }
    setButtonLoading(btn, true, 'Đang lưu...');
    await new Promise(r => setTimeout(r, 300));
    progress.step1Done = true;
    setButtonLoading(btn, false, 'Hoàn tất ✓');
    showToast('Lưu kịch bản thành công!', 'success');
    setTimeout(() => { setStep(2); btn.textContent = 'Xác nhận & Phân tích kịch bản'; }, 600);
  });

  // Step 2 → 3
  $('#next2')?.addEventListener('click', async (e) => {
    if (!checkAuth()) return;
    const btn = e.target;
    const raw = $('#layoutEditor').value.trim();
    if (!raw) { showToast('Nhập hoặc tải file JSON!', 'warning'); return; }
    try { state.layoutJson = JSON.parse(raw); } catch { showToast('JSON không hợp lệ!', 'error'); return; }
    setButtonLoading(btn, true, 'Đang xác thực...');
    await new Promise(r => setTimeout(r, 300));
    progress.step2Done = true;
    setButtonLoading(btn, false, 'Hoàn tất ✓');
    showToast('Lưu bộ khung thành công!', 'success');
    setTimeout(() => { setStep(3); btn.textContent = 'Xác nhận & Lưu bộ khung'; }, 600);
  });

  // Step 3 → 4 (Analyze + Upload Characters)
  $('#next3')?.addEventListener('click', async (e) => {
    if (!checkAuth()) return;
    if (!state.characters.length) { showToast('Tải lên ít nhất 1 ảnh nhân vật!', 'warning'); return; }
    const btn = e.target;
    setButtonLoading(btn, true, 'AI đang phân tích...');
    const ok = await analyzeScriptInStudio();
    if (ok && state.comic_id) {
      setButtonLoading(btn, true, 'Đang lưu vào Database...');
      const formData = new FormData();
      formData.append('session_id', 'default');
      formData.append('comic_id', state.comic_id);
      state.characters.forEach(ch => { if (ch.file) formData.append('files', ch.file); });
      try {
        const res = await fetch('/api/comic/upload-nhan-vat', {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: formData,
        });
        if (!res.ok) throw new Error('Upload thất bại');
        progress.step3Done = true;
        setButtonLoading(btn, false, 'Hoàn tất ✓');
        showToast('Phân tích & lưu thành công!', 'success');
        setTimeout(() => { setStep(4); btn.textContent = 'Xác nhận & Phân tích nhân vật'; }, 600);
      } catch (err) {
        showToast('Lỗi lưu Database: ' + err.message, 'error');
        setButtonLoading(btn, false);
      }
    } else {
      setButtonLoading(btn, false);
    }
  });

  // Step 4: Render
  $('#renderBtn')?.addEventListener('click', async () => {
    if (!checkAuth()) return;
    if (!progress.step3Done) { showToast('Hoàn thành Bước 3 trước!', 'warning'); return; }
    startRenderingProcess();
    setStatus('AI đang miệt mài vẽ tranh...', 'info');
    try {
      const formattedPanels = state.frames.map(frame => {
        const pd = frame.panelData || {};
        return {
          mo_ta_hinh_anh: pd.mo_ta_hinh_anh || '',
          thoai_trai: pd.thoai_trai || '...',
          thoai_phai: pd.thoai_phai || '...',
          sfx: pd.sfx || '',
          aspect_ratio: pd.aspect_ratio || '1:1',
          image_size: pd.image_size || '1024x1024',
        };
      });
      const res = await fetch('/api/comic/san_xuat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ comic_id: state.comic_id, session_id: 'default', character_description: '', panels: formattedPanels }),
      });
      if (!res.ok) {
        if (res.status === 402) {
          const errData = await res.json();
          showToast('⚠ ' + (errData.detail || 'Hết quota!'), 'warning');
          setStatus(errData.detail || 'Hết lượt sinh ảnh. Nâng cấp lên Pro!', 'error');
          const grid = document.getElementById('framesGrid');
          grid.innerHTML = `
            <div class="empty-state" style="border:2px dashed var(--warning);border-radius:var(--radius-lg);padding:40px;background:rgba(245,158,11,0.05)">
              <div class="empty-icon" style="opacity:1;font-size:56px">💎</div>
              <h3 style="color:var(--warning);margin-bottom:8px">Bạn đã hết lượt sinh ảnh!</h3>
              <p style="color:var(--text-secondary);max-width:400px;margin:0 auto">${errData.detail || 'Nâng cấp lên gói Pro để sinh không giới hạn.'}</p>
              <div style="margin-top:16px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
                <span style="background:var(--primary-light);padding:8px 16px;border-radius:var(--radius-md);font-size:13px">Gói Free: 20 ảnh</span>
                <span style="background:linear-gradient(135deg,#fef3c7,#fde68a);padding:8px 16px;border-radius:var(--radius-md);font-size:13px;font-weight:600">Gói Pro: Không giới hạn</span>
              </div>
              <button id="upgradeFromQuota" class="btn" style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;font-weight:700;border:none;margin-top:16px;padding:8px 24px;border-radius:var(--radius-md);cursor:pointer;font-size:14px">⬆ Nâng cấp lên Pro ngay</button>
              <p style="font-size:13px;color:var(--text-secondary);margin-top:8px">Hoặc liên hệ Admin để được hỗ trợ.</p>
            </div>`;
          document.getElementById('upgradeFromQuota')?.addEventListener('click', () => document.getElementById('upgradeModal').classList.add('show'));
          return;
        }
        const errData = await res.json();
        throw new Error(errData.detail || 'Lỗi server');
      }
      const data = await res.json();
      renderResults(data.images || []);
      showToast('AI đã vẽ xong!', 'success');
      setStatus('Đã vẽ thành công! Chọn ảnh để xuất PDF.', 'success');
    } catch (err) {
      showToast('Lỗi: ' + err.message, 'error');
      setStatus('Vẽ thất bại: ' + err.message, 'error');
      const grid = document.getElementById('framesGrid');
      grid.innerHTML = `<div class="empty-state" style="border:2px dashed var(--danger);border-radius:var(--radius-lg);padding:40px;background:rgba(239,68,68,0.04)">
        <div class="empty-icon" style="opacity:1">❌</div>
        <h3 style="color:var(--danger);margin-bottom:8px">Rất tiếc, quá trình vẽ gặp sự cố!</h3>
        <p style="color:var(--text-secondary)">${err.message}</p>
        <p class="mt-8">Hãy thử nhấn <strong>"Gửi tới AI để vẽ"</strong> lại.</p>
      </div>`;
    }
  });

  // Back buttons
  $('#prev2')?.addEventListener('click', () => setStep(1));
  $('#prev3')?.addEventListener('click', () => setStep(2));
  $('#prev4')?.addEventListener('click', () => setStep(3));
}

// ============================================================
// Utility
// ============================================================
function escHtml(s = '') {
  return String(s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
}

// ============================================================
// Init
// ============================================================
function init() {
  // Handle OAuth token from URL
  const params = new URLSearchParams(window.location.search);
  const tokenParam = params.get('token');
  if (tokenParam) {
    localStorage.setItem('access_token', tokenParam);
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  setStep(1);
  bindWizardControls();
  makeDropzone(document.getElementById('scriptDrop'));
  makeDropzone(document.getElementById('layoutDrop'));
  makeDropzone(document.getElementById('charactersDrop'));
  renderCharacters();
  renderFrames();
  renderAccountArea();
  // Logout modal
  document.getElementById('cancelLogout')?.addEventListener('click', () => document.getElementById('logoutModal').classList.remove('show'));
  document.getElementById('confirmLogout')?.addEventListener('click', () => { localStorage.removeItem('access_token'); window.location.reload(); });
  // Upgrade modal
  document.getElementById('closeUpgrade')?.addEventListener('click', () => document.getElementById('upgradeModal').classList.remove('show'));
  document.getElementById('upgradeModal')?.addEventListener('click', (e) => { if (e.target === e.currentTarget) e.currentTarget.classList.remove('show'); });
  document.getElementById('showUpgradeFormBtn')?.addEventListener('click', () => {
    document.getElementById('showUpgradeFormBtn').style.display = 'none';
    document.getElementById('upgradeConfirmSection').style.display = 'block';
  });
  document.getElementById('confirmUpgradeBtn')?.addEventListener('click', async () => {
    const ref = document.getElementById('transactionRefInput').value.trim();
    const btn = document.getElementById('confirmUpgradeBtn');
    btn.disabled = true; btn.textContent = 'Đang xử lý...';
    try {
      const res = await fetch('/api/comic/self-upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ transaction_ref: ref }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Lỗi');
      showToast(data.message || '🎉 Nâng cấp thành công!', 'success');
      document.getElementById('upgradeModal').classList.remove('show');
      planCache = null;
      renderAccountArea();
    } catch (e) {
      showToast('Lỗi: ' + e.message, 'error');
    } finally {
      btn.disabled = false; btn.textContent = 'Xác nhận đã chuyển khoản & Kích hoạt Pro ngay';
    }
  });
  // Auth prompt close
  document.getElementById('closeLoginPrompt')?.addEventListener('click', () => document.getElementById('loginPrompt').classList.remove('show'));
  // Prevent form submit from reloading
  document.querySelectorAll('form').forEach(f => f.addEventListener('submit', e => e.preventDefault()));
}

document.addEventListener('DOMContentLoaded', init);
