import PyPDF2
import pdf2image
import io
import re
from PIL import Image
from ocr_processor import extract_text_from_image, enhance_text_extraction

def get_page_count(pdf_path):
    """Get the total number of pages in a PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception as e:
        print(f"Error getting page count: {e}")
        return 0

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""
        
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Fix common OCR errors
    text = text.replace('|', 'I').replace('0', 'O')
    return text

def process_pdf(pdf_path, dpi=300):
    """
    Process a PDF file, extracting both images and text using multiple methods
    for improved reliability
    
    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for image conversion (higher = better quality but slower)
        
    Returns:
    - list of PIL Image objects (one per page)
    - list of extracted text (one string per page)
    """
    pdf_images = []
    extracted_texts = []
    
    try:
        # Convert PDF pages to images with specified DPI for better OCR results
        images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
        pdf_images = images
        
        # Process each page with multiple extraction methods
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for i, page in enumerate(pdf_reader.pages):
                # Method 1: Extract text directly from PDF
                pdf_text = page.extract_text() or ""
                pdf_text = clean_text(pdf_text)
                
                # Method 2: Use OCR on the page image
                ocr_text = ""
                if i < len(images):  # Ensure we have the corresponding image
                    # Get quality setting from session state if available
                    import streamlit as st
                    quality_level = "standard"
                    if hasattr(st, "session_state") and hasattr(st.session_state, "ocr_quality"):
                        quality_level = st.session_state.ocr_quality
                    
                    ocr_text = extract_text_from_image(images[i], quality_level=quality_level)
                    ocr_text = clean_text(ocr_text)
                
                # Choose the best result or combine them
                if len(pdf_text) > len(ocr_text) * 1.5:
                    # PDF extraction gave significantly more text
                    final_text = pdf_text
                elif len(ocr_text) > len(pdf_text) * 1.2:
                    # OCR gave significantly more text
                    final_text = ocr_text
                else:
                    # Try to get the best of both worlds by enhancing
                    final_text = enhance_text_extraction(pdf_text, ocr_text)
                
                extracted_texts.append(final_text)
        
        return pdf_images, extracted_texts
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        # Try fallback methods if main process failed
        try:
            fallback_images = []
            fallback_texts = []
            
            # Fallback method 1: Try to extract just text directly
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text = page.extract_text() or "Text extraction failed"
                    fallback_texts.append(text)
                    
            # If we got text but no images, try to at least get blank images
            # to maintain the page structure
            if fallback_texts and not fallback_images:
                page_count = len(fallback_texts)
                for _ in range(page_count):
                    # Create a blank white image
                    blank = Image.new('RGB', (800, 1100), (255, 255, 255))
                    fallback_images.append(blank)
                    
            if fallback_images and fallback_texts:
                print("Used fallback method for PDF processing")
                return fallback_images, fallback_texts
                
        except Exception as fallback_error:
            print(f"Fallback processing also failed: {fallback_error}")
        
        return [], []

def extract_text_from_pdf_file(pdf_file):
    """Extract text from a PDF file object with enhanced reliability"""
    text_content = []
    
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text = page.extract_text() or ""
            text = clean_text(text)
            text_content.append(text)
        
        # If all pages returned empty text, something likely went wrong
        if all(not text for text in text_content):
            # Convert to images and try OCR as fallback
            pdf_bytes = pdf_file.read()
            with open("temp_file.pdf", "wb") as f:
                f.write(pdf_bytes)
            
            images = pdf2image.convert_from_path("temp_file.pdf")
            text_content = [extract_text_from_image(img) for img in images]
            import os
            os.remove("temp_file.pdf")
        
        return text_content
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return []
