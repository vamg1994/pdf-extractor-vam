import numpy as np
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
import io

def preprocess_image(image):
    """
    Preprocess image to improve OCR accuracy using PIL instead of OpenCV
    
    Args:
        image: PIL Image object
        
    Returns:
        Preprocessed PIL Image
    """
    # Ensure we have a PIL Image
    if not isinstance(image, Image.Image):
        try:
            image = Image.fromarray(image)
        except Exception as e:
            print(f"Error converting to PIL Image: {e}")
            return image
    
    # Convert to grayscale
    img_gray = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img_gray)
    img_contrast = enhancer.enhance(2.0)  # Increase contrast
    
    # Apply slight blur to reduce noise
    img_blur = img_contrast.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Apply threshold to make it more black and white
    # This is a simple threshold - not as good as adaptive threshold in OpenCV
    # but will work for basic OCR
    fn = lambda x : 255 if x > 150 else 0
    img_threshold = img_blur.point(fn, mode='1')
    
    return img_threshold

def extract_text_from_image(image):
    """
    Extract text from an image using OCR
    
    Args:
        image: PIL Image object
        
    Returns:
        Extracted text as string
    """
    try:
        # Preprocess the image
        processed_img = preprocess_image(image)
        
        # Apply OCR
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        
        return text
    except Exception as e:
        print(f"OCR Error: {e}")
        return "OCR processing failed."
