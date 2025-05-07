import numpy as np
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import io
import re

def preprocess_image(image, method="standard"):
    """
    Preprocess image to improve OCR accuracy using PIL
    
    Args:
        image: PIL Image object
        method: Preprocessing method to use (standard, high_contrast, document)
        
    Returns:
        Preprocessed PIL Image
    """
    # Ensure we have a PIL Image
    if not isinstance(image, Image.Image):
        try:
            image = Image.fromarray(np.array(image))
        except Exception as e:
            print(f"Error converting to PIL Image: {e}")
            return image
    
    if method == "high_contrast":
        # High contrast method for poor quality scans
        img_gray = image.convert('L')
        img_contrast = ImageEnhance.Contrast(img_gray).enhance(2.5)
        img_bright = ImageEnhance.Brightness(img_contrast).enhance(1.2)
        img_sharp = ImageEnhance.Sharpness(img_bright).enhance(2.0)
        return img_sharp
        
    elif method == "document":
        # Specialized for document text
        img_gray = image.convert('L')
        # Increase size for better OCR
        w, h = img_gray.size
        img_resized = img_gray.resize((int(w*1.5), int(h*1.5)), Image.LANCZOS)
        # Deskew if needed
        img_deskewed = img_resized  # In a full implementation, add deskewing logic here
        return img_deskewed
    
    else:  # standard method
        # Convert to grayscale
        img_gray = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(img_gray)
        img_contrast = enhancer.enhance(2.0)
        
        # Apply slight blur to reduce noise
        img_blur = img_contrast.filter(ImageFilter.GaussianBlur(radius=0.8))
        
        # Sharpen to improve text edges
        img_sharp = img_blur.filter(ImageFilter.SHARPEN)
        
        # Apply adaptive-like thresholding (as close as we can get with PIL)
        threshold = 180  # This could be dynamically calculated based on image histogram
        fn = lambda x : 255 if x > threshold else 0
        img_threshold = img_sharp.point(fn, mode='1')
        
        return img_threshold

def extract_text_from_image(image):
    """
    Extract text from an image using OCR with multiple attempts for reliability
    
    Args:
        image: PIL Image object
        
    Returns:
        Extracted text as string
    """
    all_results = []
    
    try:
        # Try multiple preprocessing methods and configurations
        preprocessing_methods = ["standard", "high_contrast", "document"]
        psm_modes = [6, 3, 4]  # Different page segmentation modes
        
        for method in preprocessing_methods:
            processed_img = preprocess_image(image, method=method)
            
            for psm in psm_modes:
                try:
                    custom_config = f'--oem 3 --psm {psm}'
                    text = pytesseract.image_to_string(processed_img, config=custom_config)
                    
                    # Only keep results that actually have content
                    if text and len(text.strip()) > 10:
                        all_results.append(text)
                except Exception as inner_e:
                    print(f"OCR attempt failed with method {method}, psm {psm}: {inner_e}")
                    continue
        
        if all_results:
            # Get the result with the most content (usually the best one)
            best_result = max(all_results, key=lambda x: len(x.strip()))
            return best_result
        else:
            # If all attempts failed, try one last bare-bones attempt
            return pytesseract.image_to_string(image)
            
    except Exception as e:
        print(f"OCR Error: {e}")
        return "OCR processing failed."

def enhance_text_extraction(pdf_text, ocr_text):
    """
    Combines and enhances text from multiple extraction methods
    
    Args:
        pdf_text: Text extracted directly from PDF
        ocr_text: Text extracted via OCR
        
    Returns:
        Enhanced combined text
    """
    # If either input is empty, return the other
    if not pdf_text.strip():
        return ocr_text
    if not ocr_text.strip():
        return pdf_text
        
    # Simple combination - take the longer text but check for content
    pdf_words = set(re.findall(r'\b\w+\b', pdf_text.lower()))
    ocr_words = set(re.findall(r'\b\w+\b', ocr_text.lower()))
    
    # If OCR found significantly more unique words
    if len(ocr_words - pdf_words) > len(pdf_words) * 0.3:
        base_text = ocr_text
    else:
        base_text = pdf_text
    
    # Clean up common OCR errors
    cleaned_text = base_text
    cleaned_text = re.sub(r'[|]', 'I', cleaned_text)  # Common OCR errors
    cleaned_text = re.sub(r'(\d)[oO](\d)', r'\10\2', cleaned_text)  # Fix numbers
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()  # Clean whitespace
    
    return cleaned_text
