import os
import cv2
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PATH_FONT_VIET = "C:\\Windows\\Fonts\\arialbd.ttf"


def _la_noi_dung_gia(text):
    if text is None:
        return True
    text = str(text).strip()
    if text == "":
        return True
    if text.replace(".", "").replace("…", "").strip() == "":
        return True
    return False


def _lay_font(size):
    danh_sach_font = [
        PATH_FONT_VIET,
        "C:\\Windows\\Fonts\\Arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\Arial.ttf",
    ]
    for font_path in danh_sach_font:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size=size)
        except:
            pass
    return ImageFont.load_default()


def _do_kich_thuoc_text(draw, noi_dung, font, stroke_width=0, spacing=6):
    bbox = draw.multiline_textbbox(
        (0, 0),
        noi_dung,
        font=font,
        align="center",
        spacing=spacing,
        stroke_width=stroke_width
    )
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _ve_text_truyen_tranh(draw, vi_tri, noi_dung, font, mau_chu="white", mau_vien="black"):
    co_chu = getattr(font, "size", 24)
    do_day_vien = max(2, co_chu // 12)
    x, y = vi_tri

    draw.multiline_text(
        (x, y),
        noi_dung,
        font=font,
        fill=mau_chu,
        align="center",
        anchor="mm",
        spacing=max(6, co_chu // 8),
        stroke_width=do_day_vien,
        stroke_fill=mau_vien
    )


def _lay_vung_an_toan(bong_thoai):
    x, y, w, h = bong_thoai["x"], bong_thoai["y"], bong_thoai["w"], bong_thoai["h"]

    # Vùng an toàn mô phỏng bóng thoại oval:
    # hẹp ngang hơn để tránh chữ chạm hai cạnh cong,
    # phía dưới chừa ít hơn trước để chữ không bị cảm giác tụt xuống.
    pad_x = int(w * 0.22)
    pad_top = int(h * 0.18)
    pad_bottom = int(h * 0.18)

    return {
        "x": x + pad_x,
        "y": y + pad_top,
        "w": max(20, w - pad_x * 2),
        "h": max(20, h - pad_top - pad_bottom)
    }


def _sap_xep_va_chon_2_bong(ds_bong, chieu_rong_anh):
    if not ds_bong:
        return []

    ds_bong = sorted(ds_bong, key=lambda b: (b["y"], b["x"]))

    nhom_tren = [b for b in ds_bong if b["y"] + b["h"] * 0.5 < max(item["y"] + item["h"] * 0.75 for item in ds_bong)]
    if len(nhom_tren) >= 2:
        ds_uu_tien = nhom_tren
    else:
        ds_uu_tien = ds_bong

    ben_trai = [b for b in ds_uu_tien if b["tam_x"] < chieu_rong_anh * 0.5]
    ben_phai = [b for b in ds_uu_tien if b["tam_x"] >= chieu_rong_anh * 0.5]

    ket_qua = []

    if ben_trai:
        ket_qua.append(sorted(ben_trai, key=lambda b: (b["y"], -b["dien_tich"]))[0])
    if ben_phai:
        ket_qua.append(sorted(ben_phai, key=lambda b: (b["y"], -b["dien_tich"]))[0])

    if len(ket_qua) < 2:
        ds_theo_do_tot = sorted(
            ds_uu_tien,
            key=lambda b: (
                b["y"],
                abs(b["tam_x"] - chieu_rong_anh * 0.25 if b["tam_x"] < chieu_rong_anh * 0.5 else b["tam_x"] - chieu_rong_anh * 0.75)
            )
        )
        for b in ds_theo_do_tot:
            if all(abs(b["tam_x"] - c["tam_x"]) > 40 for c in ket_qua):
                ket_qua.append(b)
            if len(ket_qua) == 2:
                break

    ket_qua = sorted(ket_qua[:2], key=lambda b: b["tam_x"])
    return ket_qua


def tim_bong_thoai_tu_dong(path_anh):
    """Dò 2 bóng thoại lớn phía trên ảnh, ưu tiên bóng trắng viền đen."""
    print("👁️ Đang quét ảnh để phát hiện bóng thoại...")

    img = cv2.imread(path_anh)
    if img is None:
        raise FileNotFoundError(f"Không đọc được ảnh: {path_anh}")

    chieu_cao, chieu_rong, _ = img.shape
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    _, mask_trang = cv2.threshold(blur, 225, 255, cv2.THRESH_BINARY)
    kernel_lon = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    kernel_nho = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_trang = cv2.morphologyEx(mask_trang, cv2.MORPH_CLOSE, kernel_lon, iterations=2)
    mask_trang = cv2.morphologyEx(mask_trang, cv2.MORPH_OPEN, kernel_nho, iterations=1)

    contours, _ = cv2.findContours(mask_trang, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    danh_sach_bong_thoai = []
    dien_tich_anh = chieu_cao * chieu_rong

    for cnt in contours:
        dien_tich = cv2.contourArea(cnt)
        if dien_tich < dien_tich_anh * 0.01 or dien_tich > dien_tich_anh * 0.24:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        if y > chieu_cao * 0.56:
            continue
        if w < chieu_rong * 0.12 or h < chieu_cao * 0.08:
            continue

        ty_le_w_h = w / h if h > 0 else 0
        do_dac = dien_tich / (w * h) if w * h > 0 else 0
        chu_vi = cv2.arcLength(cnt, True)
        do_tron = 4 * np.pi * dien_tich / (chu_vi * chu_vi) if chu_vi > 0 else 0

        hull = cv2.convexHull(cnt)
        dien_tich_hull = cv2.contourArea(hull)
        do_loi = dien_tich / dien_tich_hull if dien_tich_hull > 0 else 0

        if not (1.0 <= ty_le_w_h <= 3.8):
            continue
        if do_dac < 0.52:
            continue
        if do_tron < 0.30:
            continue
        if do_loi < 0.80:
            continue

        mask_rieng = np.zeros_like(gray)
        cv2.drawContours(mask_rieng, [cnt], -1, 255, -1)
        do_sang_tb = cv2.mean(gray, mask=mask_rieng)[0]
        if do_sang_tb < 228:
            continue

        M = cv2.moments(cnt)
        if M["m00"] != 0:
            tam_x = int(M["m10"] / M["m00"])
        else:
            tam_x = x + w // 2
        tam_y = y + int(h * 0.42)

        tam_x = max(x + 5, min(x + w - 5, tam_x))
        tam_y = max(y + 5, min(y + h - 5, tam_y))

        if gray[tam_y, tam_x] < 200:
            tam_x = x + w // 2
            tam_y = y + int(h * 0.42)

        danh_sach_bong_thoai.append({
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "tam_x": tam_x,
            "tam_y": tam_y,
            "dien_tich": dien_tich
        })

    if len(danh_sach_bong_thoai) < 2:
        edges = cv2.Canny(blur, 50, 150)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        contours_edge, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours_edge:
            dien_tich = cv2.contourArea(cnt)
            if dien_tich < dien_tich_anh * 0.015 or dien_tich > dien_tich_anh * 0.26:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            if y > chieu_cao * 0.56:
                continue
            if w < chieu_rong * 0.12 or h < chieu_cao * 0.08:
                continue

            ty_le_w_h = w / h if h > 0 else 0
            if not (1.0 <= ty_le_w_h <= 4.0):
                continue

            tam_x = x + w // 2
            tam_y = y + int(h * 0.42)

            da_co = False
            for b in danh_sach_bong_thoai:
                if abs(b["tam_x"] - tam_x) < 40 and abs(b["tam_y"] - tam_y) < 40:
                    da_co = True
                    break
            if da_co:
                continue

            danh_sach_bong_thoai.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "tam_x": tam_x,
                "tam_y": tam_y,
                "dien_tich": dien_tich
            })

    bong_thoai_chuan = _sap_xep_va_chon_2_bong(danh_sach_bong_thoai, chieu_rong)

    if len(bong_thoai_chuan) < 2:
        bong_thoai_chuan = [
            {
                "x": int(chieu_rong * 0.05),
                "y": int(chieu_cao * 0.05),
                "w": int(chieu_rong * 0.36),
                "h": int(chieu_cao * 0.23),
                "tam_x": int(chieu_rong * 0.23),
                "tam_y": int(chieu_cao * 0.15),
                "dien_tich": int(chieu_rong * chieu_cao * 0.08)
            },
            {
                "x": int(chieu_rong * 0.59),
                "y": int(chieu_cao * 0.05),
                "w": int(chieu_rong * 0.36),
                "h": int(chieu_cao * 0.23),
                "tam_x": int(chieu_rong * 0.77),
                "tam_y": int(chieu_cao * 0.15),
                "dien_tich": int(chieu_rong * chieu_cao * 0.08)
            }
        ]

    print(f"🎯 Đã khóa chính xác: {len(bong_thoai_chuan)} bóng thoại chuẩn!")
    return bong_thoai_chuan


def tu_dong_co_gian_chu(draw, text, max_w, max_h):
    """
    Tự co giãn cỡ chữ để chữ to, đậm, gọn trong vùng an toàn của bóng thoại.
    """
    text = str(text).strip()
    if _la_noi_dung_gia(text):
        return "", _lay_font(20)

    tu_list = text.split()
    if not tu_list:
        return "", _lay_font(20)

    for font_size in range(52, 17, -2):
        font = _lay_font(font_size)
        stroke_width = max(2, font_size // 12)
        spacing = max(6, font_size // 8)

        max_ky_tu_moi_dong = max(8, int(max_w / max(font_size * 0.55, 1)))
        ds_do_rong = [
            max_ky_tu_moi_dong,
            max(6, max_ky_tu_moi_dong - 2),
            max(5, max_ky_tu_moi_dong - 4)
        ]

        for do_rong_wrap in ds_do_rong:
            cac_dong = textwrap.wrap(text, width=do_rong_wrap, break_long_words=False, break_on_hyphens=False)
            if not cac_dong:
                continue
            if len(cac_dong) > 4:
                continue

            noi_dung = "\n".join(cac_dong)
            w_text, h_text = _do_kich_thuoc_text(draw, noi_dung, font, stroke_width=stroke_width, spacing=spacing)

            if w_text <= max_w and h_text <= max_h:
                return noi_dung, font

    font = _lay_font(18)
    noi_dung = textwrap.fill(text, width=12)
    return noi_dung, font


def auto_vietsub(path_anh_goc, path_anh_xuat, danh_sach_text, sfx=""):
    """Chèn thoại kiểu comic rõ, gọn, ưu tiên 2 bóng thoại trên cùng và bỏ qua thoại '...'."""
    bong_thoais = tim_bong_thoai_tu_dong(path_anh_goc)

    if not bong_thoais:
        print("❌ LỖI: Mắt thần không thấy bóng thoại.")
        return

    try:
        img = Image.open(path_anh_goc).convert("RGB")
        draw = ImageDraw.Draw(img)

        if not _la_noi_dung_gia(sfx):
            sfx_text = str(sfx).strip()
            co_sfx = max(26, min(img.width // 14, img.height // 10, 64))
            try:
                font_sfx = _lay_font(co_sfx)
            except:
                font_sfx = ImageFont.load_default()

            draw.text(
                (img.width / 2, img.height * 0.12),
                sfx_text,
                font=font_sfx,
                fill="#FFD400",
                stroke_width=max(2, getattr(font_sfx, "size", 32) // 12),
                stroke_fill="black",
                anchor="mm"
            )

        for i, bong_thoai in enumerate(bong_thoais):
            if i >= len(danh_sach_text):
                continue

            noi_dung = danh_sach_text[i]
            if _la_noi_dung_gia(noi_dung):
                print(f"⏭️ Bỏ qua thoại placeholder ở bóng {i + 1}: '{noi_dung}'")
                continue

            vung_an_toan = _lay_vung_an_toan(bong_thoai)

            chu_hoan_hao, font_hoan_hao = tu_dong_co_gian_chu(
                draw,
                str(noi_dung).strip(),
                vung_an_toan["w"],
                vung_an_toan["h"]
            )

            if not chu_hoan_hao.strip():
                continue

            tam_y_can_chinh = bong_thoai["tam_y"] - max(4, int(bong_thoai["h"] * 0.06))

            _ve_text_truyen_tranh(
                draw,
                (bong_thoai["tam_x"], tam_y_can_chinh),
                chu_hoan_hao,
                font_hoan_hao
            )
            print(f"✅ Đã chèn thành công thoại: '{noi_dung}'")

        img.save(path_anh_xuat)
        img.close()
        print(f"🎉 Hoàn tất chèn chữ. File được lưu tại: {path_anh_xuat}")

    except Exception as e:
        print(f"❌ Lỗi xử lý ảnh: {e}")


if __name__ == "__main__":
    anh_goc = os.path.join("workspace", "outputs", "panel_1_raw.jpg")
    anh_hoan_thanh = os.path.join("workspace", "outputs", "panel_1_done.jpg")
    kich_ban_thoai = [
        "Biển đẹp quá trời luôn!",
        "Nhanh lên, mình đi check-in nào!"
    ]
    auto_vietsub(anh_goc, anh_hoan_thanh, kich_ban_thoai, sfx="VÙAÀO...")