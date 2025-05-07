import numpy as np
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import io
import re
import os
import sys

# Ensure tesseract can be found - fix for missing language files
if sys.platform.startswith('linux'):
    # Set the correct path to tesseract in the Replit environment
    os.environ['PATH'] = f"{os.environ.get('PATH')}:/nix/store/44vcjbcy1p2yhc974bcw250k2r5x5cpa-tesseract-5.3.4/bin"
    # Set the tessdata directory
    os.environ['TESSDATA_PREFIX'] = "/nix/store/44vcjbcy1p2yhc974bcw250k2r5x5cpa-tesseract-5.3.4/share/tessdata"

def preprocess_image(image, method="standard"):
    """
    Preprocess image to improve OCR accuracy using PIL
    
    Args:
        image: PIL Image object
        method: Preprocessing method to use (standard, high_contrast, document, advanced)
        
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
        # Deskew if possible
        try:
            img_deskewed = deskew_image(img_resized)
            return img_deskewed
        except:
            return img_resized
            
    elif method == "advanced":
        # Advanced preprocessing for difficult documents
        # Convert to grayscale and increase size
        img_gray = image.convert('L')
        w, h = img_gray.size
        img_resized = img_gray.resize((int(w*1.5), int(h*1.5)), Image.LANCZOS)
        
        # Apply multiple enhancements
        img_contrast = ImageEnhance.Contrast(img_resized).enhance(2.0)
        img_sharp = ImageEnhance.Sharpness(img_contrast).enhance(1.5)
        
        # Apply denoising
        img_denoised = img_sharp.filter(ImageFilter.MedianFilter(size=3))
        
        # Create binarized version with adaptive-like thresholding
        # Calculate dynamic threshold based on image statistics
        img_array = np.array(img_denoised)
        threshold = np.mean(img_array) - 10  # Slightly lower than mean for better text retention
        fn = lambda x: 255 if x > threshold else 0
        img_binary = img_denoised.point(fn, mode='1')
        
        # Try to deskew
        try:
            img_deskewed = deskew_image(img_binary)
            return img_deskewed
        except:
            return img_binary
    
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

def deskew_image(image):
    """
    Attempt to deskew an image by detecting the angle of text lines
    This is a simple implementation that works for many documents
    
    Args:
        image: PIL Image to deskew
        
    Returns:
        Deskewed PIL Image
    """
    # Convert to numpy array for processing
    img_array = np.array(image)
    
    # Simple method: find lines and calculate dominant angle
    # This is a simplified version that uses horizontal projection
    # For a real implementation, use Hough Transform
    
    # Get a rough estimate of skew angle based on horizontal projections
    # Sum pixel values horizontally to find text lines
    h_projection = np.sum(img_array, axis=1)
    
    # Calculate differences between adjacent rows to find line edges
    diff = np.diff(h_projection)
    
    # Find peaks in the difference array (line starts and ends)
    peaks = np.where(np.abs(diff) > np.std(diff))[0]
    
    if len(peaks) < 2:
        # Not enough information to determine skew
        return image
    
    # Simplistic approach: assume skew is under 15 degrees
    # and test a few angles to see which gives most horizontal alignment
    best_angle = 0
    
    # Test angles from -15 to 15 degrees in 1 degree increments
    for angle in range(-15, 16):
        # Rotate image to test angle
        test_img = image.rotate(angle, resample=Image.BICUBIC, expand=False)
        
        # Calculate horizontal projection of rotated image
        test_array = np.array(test_img)
        h_proj = np.sum(test_array, axis=1)
        
        # Measure how "peaky" the projection is (more peaky = better aligned)
        peakiness = np.std(h_proj)
        
        # Update best angle if this one is better
        if angle == -15 or peakiness > np.std(h_projection):
            best_angle = angle
            h_projection = h_proj
    
    # Return the deskewed image using best angle
    return image.rotate(best_angle, resample=Image.BICUBIC, expand=False)

def extract_text_from_image(image, quality_level="standard"):
    """
    Extract text from an image using OCR with multiple attempts for reliability
    
    Args:
        image: PIL Image object
        quality_level: Quality level for extraction (fast, standard, high)
        
    Returns:
        Extracted text as string
    """
    # Quick fallback for development environments where tesseract might not be properly configured
    try:
        pytesseract.get_tesseract_version()
    except Exception as e:
        print(f"Tesseract not properly configured: {e}")
        return "OCR extraction failed: Tesseract OCR engine not available on this system."
    all_results = []
    # Reduce processing time to make app more responsive
    processing_time_limit = 30  # Seconds
    
    # Resize large images for faster processing
    if hasattr(image, 'width') and hasattr(image, 'height'):
        if image.width > 2000 or image.height > 2000:
            # Resize to a more reasonable size for faster processing
            ratio = min(2000/image.width, 2000/image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)
    
    try:
        # Adjust methods based on quality level
        if quality_level == "fast":
            preprocessing_methods = ["standard"]
            psm_modes = [6]  # Single uniform block of text
        elif quality_level == "high":
            preprocessing_methods = ["standard", "high_contrast", "document", "advanced"]
            psm_modes = [6, 3, 4, 11, 12]  # Add more segmentation modes
        else:  # standard
            preprocessing_methods = ["standard", "high_contrast", "document"]
            psm_modes = [6, 3, 4]  # Different page segmentation modes
        
        # Language detection and configuration
        # Simplify to just use English for now since other language files aren't available
        languages = "eng"  # Default to English
        
        # Only use language specification if it's English
        # This avoids errors with missing language files
        lang_param = " -l eng"
        
        # Test Tesseract is working
        try:
            # Simple test with basic settings to check connectivity
            test_result = pytesseract.image_to_string(
                preprocess_image(image, method="standard"), 
                config='--psm 6 -l eng'
            )
            # If we get here, tesseract is working
        except Exception as test_error:
            print(f"Tesseract test error: {test_error}")
            return "OCR processing unavailable. Tesseract initialization failed."
        
        # Process with each method and PSM mode
        for method in preprocessing_methods:
            processed_img = preprocess_image(image, method=method)
            
            for psm in psm_modes:
                try:
                    # Configure OCR with language and specialized settings
                    custom_config = f'--oem 3 --psm {psm}{lang_param}'
                    
                    # Document mode needs special settings but avoid tessdata_dir
                    # which seems to cause problems
                    if method == "document":
                        # For document mode, optimize for printed text
                        custom_config += ' -c preserve_interword_spaces=1'
                    
                    text = pytesseract.image_to_string(processed_img, config=custom_config)
                    
                    # Only keep results that actually have content
                    if text and len(text.strip()) > 10:
                        # Perform basic text cleanup
                        text = clean_ocr_text(text)
                        all_results.append(text)
                        
                except Exception as inner_e:
                    print(f"OCR attempt failed with method {method}, psm {psm}: {inner_e}")
                    continue
        
        if all_results:
            # Advanced selection: instead of just longest text, 
            # look at word count, character clarity, and content
            best_result = select_best_ocr_result(all_results)
            return best_result
        else:
            # If all attempts failed, try one last approach with very basic settings
            # Sometimes simpler is better for difficult images
            try:
                text = pytesseract.image_to_string(image, config='-l eng --psm 6')
                return clean_ocr_text(text) if text else "No text was detected."
            except:
                return "OCR processing failed."
            
    except Exception as e:
        print(f"OCR Error: {e}")
        return "OCR processing failed."

def clean_ocr_text(text):
    """
    Clean and normalize OCR text to improve readability
    
    Args:
        text: Raw OCR text
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
        
    # Replace common OCR errors
    text = re.sub(r'[|]', 'I', text)  # Pipe to I
    text = re.sub(r'[\u201C\u201D]', '"', text)  # Fancy quotes to standard quotes
    text = re.sub(r'[\u2018\u2019]', "'", text)  # Fancy apostrophes
    
    # Fix spacing issues
    text = re.sub(r'(\w)- (\w)', r'\1\2', text)  # Remove hyphenation
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)  # Single newlines to spaces
    text = re.sub(r'\n{2,}', '\n\n', text)  # Multiple newlines to double newlines
    
    # Fix number/letter confusion (using simpler approach to avoid regex reference issues)
    text = text.replace('O0', '00').replace('0O', '00')
    text = text.replace('l1', '11').replace('1l', '11')
    text = text.replace('I1', '11').replace('1I', '11')
    
    # Remove garbage characters
    text = re.sub(r'[^\w\s\.\,\;\:\'\"\!\?\-\(\)\[\]\{\}\$\@\#\%\&\*\+\=\/\\]', '', text)
    
    # Fix whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def select_best_ocr_result(results):
    """
    Select the best OCR result from multiple attempts
    
    Args:
        results: List of OCR text results
    
    Returns:
        Best result based on quality heuristics
    """
    if not results:
        return ""
    if len(results) == 1:
        return results[0]
    
    # Score each result on multiple factors
    scores = []
    
    for text in results:
        score = 0
        
        # 1. Length score - longer text often has more content
        score += len(text.strip()) * 0.01
        
        # 2. Word count score - more words is usually better
        words = re.findall(r'\b\w+\b', text.lower())
        score += len(words) * 0.5
        
        # 3. Average word length - if too short, might be garbage
        avg_word_len = sum(len(w) for w in words) / max(1, len(words))
        if 3 <= avg_word_len <= 10:  # Reasonable word length range
            score += 10
        
        # 4. Proportion of garbage characters - lower is better
        garbage_count = len(re.findall(r'[^\w\s\.\,\;\:\'\"\!\?\-\(\)\[\]\{\}\$\@\#\%\&\*\+\=\/\\]', text))
        garbage_ratio = garbage_count / max(1, len(text))
        score -= garbage_ratio * 100
        
        # 5. Sentence-like patterns - text with proper sentences is likely better
        sentence_like = len(re.findall(r'[A-Z][^\.!?]*[\.!?]', text))
        score += sentence_like * 5
        
        scores.append(score)
    
    # Return the result with the highest score
    best_index = scores.index(max(scores))
    return results[best_index]

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
    # Use simpler approach than regex backreferences
    cleaned_text = cleaned_text.replace('O0', '00').replace('0O', '00')
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()  # Clean whitespace
    
    return cleaned_text
