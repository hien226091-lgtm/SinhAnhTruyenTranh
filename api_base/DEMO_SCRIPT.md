# SCRIPT DEMO PIPELINE (cap nhat theo code hien tai)

## Muc tieu
Tai lieu nay mo ta dung luong chay cua pipeline CLI trong file `ingestion/pipeline.py`:
- Doc `layout.json` + `script.json`
- Sinh anh theo tung khung bang Gemini
- Luu danh sach anh vao `anh_manifest.json`

Luu y:
- Pipeline hien tai KHONG ghep thanh trang manga.
- Pipeline hien tai KHONG chay auto vietsub bang module local.
- Noi dung thoai/SFX duoc render truc tiep trong prompt Gemini.

---

## Cac file tham gia truc tiep

1. `api_base/ingestion/pipeline.py`
- Entry point CLI (`main`)
- Dieu phoi luong doc input, sinh anh, ghi manifest

2. `api_base/chatbot/services/ai_generator.py`
- Goi Gemini API de sinh anh
- Nap anh tham chieu theo `session_id`

3. `api_base/app/config.py`
- Khai bao `workspace/inputs`, `workspace/outputs`
- Doc bien moi truong (API key, model, image size)

4. `api_base/app/constants/image_options.py`
- Chuan hoa aspect ratio va image size

5. `api_base/app/utils/comic_postprocess.py`
- Su dung ham `write_image_manifest(...)`

6. `api_base/app/utils/helpers.py`
- Su dung `sanitize_filename(...)` trong luong xu ly session image

---

## Input

1. `layout.json`
- Chua thong tin bo cuc tung khung (so khung, aspect ratio, image size)

2. `script.json`
- Chua noi dung moi khung:
  - `mo_ta_hinh_anh`
  - `thoai_trai`
  - `thoai_phai`
  - `sfx`

3. Thu muc anh tham chieu (neu co)
- `api_base/workspace/inputs/sessions/<session_id>/*.png|jpg|jpeg|webp`

---

## Luong xu ly thuc te

1. Parse tham so CLI: `--layout`, `--script`, `--output`
2. Doc va validate 2 file JSON input
3. Lap qua tung khung trong script/layout
4. Goi `tao_anh_truyen_tranh(...)` de sinh anh `Anh_<n>.jpg`
5. Ghi metadata output vao `anh_manifest.json`
6. In log tong ket thoi gian xu ly

Co co che delay nho giua cac khung de giam nguy co rate limit.

---

## Lenh chay dung (tu root repo)

```bash
python api_base/ingestion/pipeline.py \
  --layout api_base/workspace/inputs/layout.json \
  --script api_base/workspace/inputs/script.json \
  --output api_base/workspace/outputs
```

Neu chay trong thu muc `api_base`, co the dung:

```bash
python ingestion/pipeline.py \
  --layout workspace/inputs/layout.json \
  --script workspace/inputs/script.json \
  --output workspace/outputs
```

---

## Output

Thu muc output:

```text
api_base/workspace/outputs/
├── Anh_1.jpg
├── Anh_2.jpg
├── ...
└── anh_manifest.json
```

`anh_manifest.json` gom:
- `filename`
- `url`
- `aspect_ratio_key`
- `aspect_ratio_label`

Luu y moi:
- Khong con sinh file `*_raw.jpg`.

---

## Vi du log terminal (rut gon)

```text
[YYYY-MM-DD HH:MM:SS] INFO - Pipeline bat dau
[YYYY-MM-DD HH:MM:SS] INFO - Doc thanh cong: ...layout.json
[YYYY-MM-DD HH:MM:SS] INFO - Doc thanh cong: ...script.json
[YYYY-MM-DD HH:MM:SS] INFO - Bat dau xu ly N khung hinh
[YYYY-MM-DD HH:MM:SS] INFO - Bat dau ve Khung 1: 16:9 @ 2K
[YYYY-MM-DD HH:MM:SS] INFO - Khung 1 hoan tat
...
[YYYY-MM-DD HH:MM:SS] INFO - Tong thoi gian: ...s (... phut)
```

Log chi tiet duoc ghi vao:
- `api_base/pipeline.log`

---

## Script demo noi voi giang vien (goi y ngan)

"Pipeline cua em la luong batch sinh anh theo khung.

- Dau vao la `layout.json` va `script.json`.
- Moi khung duoc goi Gemini de ve truc tiep anh final `Anh_n.jpg`.
- He thong ghi `anh_manifest.json` de frontend map dung thu tu anh va ti le khung.
- Co logging + validation + retry/handling de pipeline on dinh hon khi gap loi mang/quota.

Ban hien tai tap trung vao sinh anh theo khung; chua gom buoc ghep thanh trang manga trong CLI pipeline nay." 

---

## Ghi chu dong bo tai lieu

Neu can mo rong them:
- PDF export dang nam o luong API (`/api/comic/xuat-pdf`), khong nam trong `ingestion/pipeline.py`.
- One-shot prompt CLI dang nam o `ingestion/pipeline_prompt.py` (luong rieng, khong phai batch layout+script).
