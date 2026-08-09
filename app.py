import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance
from streamlit_cropper import st_cropper
from rembg import remove
import io

def enhance_image(img, brightness, contrast, sharpness):
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness)
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(sharpness)
    
    return img

def remove_background(img, bg_color):
    # Convert image to bytes for rembg processing
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    
    # Remove background using AI
    result_bytes = remove(img_byte_arr.getvalue())
    img_no_bg = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    
    # Create a new image with the selected solid background color
    new_bg = Image.new("RGBA", img_no_bg.size, bg_color)
    new_bg.paste(img_no_bg, (0, 0), mask=img_no_bg)
    
    # Convert back to RGB format (removes alpha channel for JPEG saving)
    return new_bg.convert("RGB")

def create_passport_sheet(image, cols=6, rows=7):
    # A4 Size sheet at 300 DPI (2480 x 3508)
    a4_width, a4_height = 2480, 3508
    sheet = Image.new('RGB', (a4_width, a4_height), 'white')
    
    # Standard Passport Size at 300 DPI (413 x 531 pixels)
    pp_width, pp_height = 413, 531
    img_resized = image.resize((pp_width, pp_height), Image.LANCZOS)
    
    # Add a simple black stroke/border
    draw = ImageDraw.Draw(img_resized)
    draw.rectangle([0, 0, pp_width-1, pp_height-1], outline="black", width=3)
    
    # Calculate margins to center the grid
    margin_x = (a4_width - (cols * pp_width)) // (cols + 1)
    margin_y = (a4_height - (rows * pp_height)) // (rows + 1)
    
    for row in range(rows):
        for col in range(cols):
            x = margin_x + col * (pp_width + margin_x)
            y = margin_y + row * (pp_height + margin_y)
            sheet.paste(img_resized, (x, y))
            
    return sheet

st.set_page_config(page_title="Pro Passport Photo Maker", layout="wide")
st.title("📸 Pro Passport Photo Auto-Generator")
st.write("Ab AI Background Removal ke saath!")

uploaded_file = st.file_uploader("Upload your photo (JPG/PNG)", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # Load and maintain state for the original image
    original_image = Image.open(uploaded_file).convert("RGB")
    
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    
    with col1:
        st.subheader("1. Crop Image")
        # Ensure facial consistency by accurately cropping the face first
        cropped_img = st_cropper(original_image, aspect_ratio=(3.5, 4.5), box_color='blue')
        
    with col2:
        st.subheader("2. AI Background")
        remove_bg_toggle = st.checkbox("Remove Background")
        bg_color_choice = st.color_picker("Pick Background Color", "#FFFFFF") # Default White
        
    with col3:
        st.subheader("3. Image Enhancements")
        brightness = st.slider("Brightness", 0.5, 1.5, 1.0, 0.1)
        contrast = st.slider("Contrast", 0.5, 1.5, 1.0, 0.1)
        sharpness = st.slider("Sharpness", 0.0, 2.0, 1.0, 0.1)
        
    st.markdown("---")
    
    # Processing Pipeline
    processed_img = cropped_img
    
    if remove_bg_toggle:
        with st.spinner("AI is removing the background..."):
            processed_img = remove_background(processed_img, bg_color_choice)
            
    # Apply Enhancements
    final_img = enhance_image(processed_img, brightness, contrast, sharpness)
    
    st.subheader("Final Preview")
    st.image(final_img, caption="Processed Photo Ready for Print", width=250)
    
    if st.button("Generate A4 Print Sheet", type="primary"):
        with st.spinner("Creating your print sheet..."):
            result_sheet = create_passport_sheet(final_img)
            
            st.success("Print Sheet Ready!")
            st.image(result_sheet, caption="A4 Print Sheet Preview", use_container_width=True)
            
            result_sheet.save("final_print_sheet.jpg", format="JPEG", quality=95)
            with open("final_print_sheet.jpg", "rb") as file:
                st.download_button(
                    label="⬇️ Download A4 Print Sheet",
                    data=file,
                    file_name="passport_a4_sheet.jpg",
                    mime="image/jpeg"
                )