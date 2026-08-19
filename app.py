import os
# CRITICAL FIX: Restrict CPU threads to prevent server crash on Streamlit Cloud
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance
from streamlit_cropper import st_cropper
from rembg import remove, new_session
import io
import cv2
import numpy as np

# --- 1. India Document Specifications (300 DPI) ---
INDIA_DOC_SIZES = {
    "Passport Seva (3.5 x 4.5 cm) - Auto Spacing": {"width": 413, "height": 531, "ratio": (3.5, 4.5), "mode": "auto"},
    "Passport Seva (42 Photos on A4 - Fixed Grid)": {"width": 390, "height": 501, "ratio": (3.5, 4.5), "mode": "fixed_42"},
    "India Visa / OCI (2 x 2 inch / 51 x 51 mm)": {"width": 600, "height": 600, "ratio": (1, 1), "mode": "auto"},
    "PAN Card (2.5 x 3.5 cm)": {"width": 295, "height": 413, "ratio": (2.5, 3.5), "mode": "auto"},
    "Stamp Size (2.0 x 2.5 cm)": {"width": 236, "height": 295, "ratio": (2.0, 2.5), "mode": "auto"}
}

# --- 2. Memory-Safe Background Removal ---
@st.cache_resource
def get_rembg_session():
    return new_session("u2netp")

def remove_background(img, bg_color):
    # CRITICAL FIX: Image ko chota karein taaki RAM crash na ho
    # Passport ke liye 600 pixels se zyada ki zaroorat nahi hoti
    safe_img = img.copy()
    safe_img.thumbnail((600, 600), Image.LANCZOS) 
    
    img_byte_arr = io.BytesIO()
    safe_img.save(img_byte_arr, format='PNG')
    
    session = get_rembg_session()
    result_bytes = remove(img_byte_arr.getvalue(), session=session)
    img_no_bg = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    
    new_bg = Image.new("RGBA", img_no_bg.size, bg_color)
    new_bg.paste(img_no_bg, (0, 0), mask=img_no_bg)
    return new_bg.convert("RGB")

# --- 3. Face Beautification & Enhancements ---
def apply_beautification(img, intensity):
    if intensity <= 0:
        return img
    img_np = np.array(img)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    # Bilateral filter maintains facial edges while smoothing skin texture
    sigma = int(intensity * 15)
    smooth_bgr = cv2.bilateralFilter(img_bgr, d=15, sigmaColor=sigma, sigmaSpace=sigma)
    smooth_rgb = cv2.cvtColor(smooth_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(smooth_rgb)

def enhance_image(img, brightness, contrast, sharpness):
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(sharpness)
    return img

# --- 4. A4 Sheet Grid Generation ---
def create_passport_sheet(image, doc_specs):
    # A4 Sheet Dimensions at 300 DPI
    a4_width, a4_height = 2480, 3508
    sheet = Image.new('RGB', (a4_width, a4_height), 'white')
    
    doc_width = doc_specs["width"]
    doc_height = doc_specs["height"]
    mode = doc_specs["mode"]
    
    img_resized = image.resize((doc_width, doc_height), Image.LANCZOS)
    
    # Add subtle black border
    draw = ImageDraw.Draw(img_resized)
    draw.rectangle([0, 0, doc_width - 1, doc_height - 1], outline="black", width=3)
    
    total_photos = 0
    
    if mode == "fixed_42":
        cols, rows = 6, 7
        gap_x = (a4_width - (cols * doc_width)) // (cols + 1)
        gap_y = (a4_height - (rows * doc_height)) // (rows + 1)
        
        for row in range(rows):
            for col in range(cols):
                x = gap_x + col * (doc_width + gap_x)
                y = gap_y + row * (doc_height + gap_y)
                sheet.paste(img_resized, (x, y))
                total_photos += 1
    else:
        gap = 20
        cols = a4_width // (doc_width + gap)
        rows = a4_height // (doc_height + gap)
        
        margin_x = (a4_width - (cols * doc_width) - ((cols - 1) * gap)) // 2
        margin_y = (a4_height - (rows * doc_height) - ((rows - 1) * gap)) // 2
        
        for row in range(rows):
            for col in range(cols):
                x = margin_x + col * (doc_width + gap)
                y = margin_y + row * (doc_height + gap)
                sheet.paste(img_resized, (x, y))
                total_photos += 1
                
    return sheet, total_photos

# --- 5. Streamlit App Interface ---
st.set_page_config(page_title="Pro India Document Photo Maker", layout="wide")
st.title("🇮🇳 Pro India Document Photo Auto-Generator")

selected_format = st.selectbox("Select Document Type / Format:", list(INDIA_DOC_SIZES.keys()))
doc_specs = INDIA_DOC_SIZES[selected_format]

uploaded_file = st.file_uploader("Upload your photo (JPG/PNG)", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file).convert("RGB")
    
    col1, col2, col3 = st.columns([1.3, 1, 1.2])
    
    with col1:
        st.subheader("1. Crop Image")
        cropped_img = st_cropper(original_image, aspect_ratio=doc_specs["ratio"], box_color='blue')
        
    with col2:
        st.subheader("2. AI Background")
        remove_bg_toggle = st.checkbox("Remove Background", value=True)
        bg_color_choice = st.color_picker("Pick Background Color", "#FFFFFF")
        
    with col3:
        st.subheader("3. Enhancements")
        st.write("**✨ Face Beautification**")
        auto_beautify = st.checkbox("Auto Beautify", value=True, help="Optimizes skin smoothness and lighting while keeping facial structure natural.")
        
        with st.expander("Manual Adjustments"):
            smooth_intensity = st.slider("Skin Smoothing", 0, 10, 0, 1)
            brightness = st.slider("Brightness", 0.5, 1.5, 1.0, 0.1)
            contrast = st.slider("Contrast", 0.5, 1.5, 1.0, 0.1)
            sharpness = st.slider("Sharpness", 0.0, 2.0, 1.0, 0.1)
        
    st.markdown("---")
    
    # --- Processing Execution ---
    processed_img = cropped_img
    
    if remove_bg_toggle:
        with st.spinner("Removing background safely..."):
            processed_img = remove_background(processed_img, bg_color_choice)
            
    if auto_beautify:
        processed_img = apply_beautification(processed_img, 3)
        final_img = enhance_image(processed_img, 1.05, 1.05, 1.1)
    else:
        if smooth_intensity > 0:
            processed_img = apply_beautification(processed_img, smooth_intensity)
        final_img = enhance_image(processed_img, brightness, contrast, sharpness)
    
    st.subheader("Final Preview")
    st.image(final_img, caption="Ready for Print", width=250)
    
    if st.button("Generate A4 Print Sheet", type="primary"):
        with st.spinner("Generating A4 print layout..."):
            result_sheet, photo_count = create_passport_sheet(final_img, doc_specs)
            
            st.success(f"Success! {photo_count} photos arranged on A4 sheet.")
            st.image(result_sheet, caption=f"A4 Print Sheet Preview ({selected_format})", use_container_width=True)
            
            # Save to buffer for clean download
            buf = io.BytesIO()
            result_sheet.save(buf, format="JPEG", quality=95)
            byte_data = buf.getvalue()
            
            st.download_button(
                label="⬇️ Download A4 Print Sheet",
                data=byte_data,
                file_name=f"{selected_format.replace(' ', '_').replace('/', '_')}_A4.jpg",
                mime="image/jpeg"
            )
