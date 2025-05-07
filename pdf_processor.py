import PyPDF2
import pdf2image
import io
import re
from PIL import Image
from ocr_processor import extract_text_from_image, enhance_text_extraction
import streamlit as st

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

def process_pdf(pdf_path):
    """
    Process a PDF file, extracting both images and text.
    Ensures that the number of text entries matches the number of page images.
    
    Returns:
    - list of PIL Image objects (one per page image)
    - list of extracted text (one string per page image)
    """
    pdf_images_pil = []
    extracted_texts = []
    
    try:
        # Convert PDF pages to PIL Image objects
        # This determines the number of pages we will process
        page_images = pdf2image.convert_from_path(pdf_path)
        pdf_images_pil = page_images # these are PIL Images

        # Attempt to read text using PyPDF2 for pages that correspond to images
        pypdf2_texts_map = {}
        try:
            with open(pdf_path, 'rb') as file_stream:
                pdf_reader = PyPDF2.PdfReader(file_stream)
                # Store PyPDF2 extracted text in a dictionary for quick lookup
                # Only read up to the number of images we have, or pages PyPDF2 has, whichever is smaller
                # to avoid issues if PyPDF2 sees more pages than pdf2image rendered.
                for i, page_obj in enumerate(pdf_reader.pages):
                    if i < len(page_images): # Ensure we don't try to map text beyond available images
                        pypdf2_texts_map[i] = page_obj.extract_text()
                    else:
                        break # Stop if PyPDF2 has more pages than images from pdf2image
        except Exception as e_pypdf:
            print(f"Could not read PDF with PyPDF2 for direct text extraction: {e_pypdf}")
            # Continue with OCR for all pages if PyPDF2 fails

        # Iterate through each image obtained from pdf2image
        for i, image_obj in enumerate(page_images):
            text_from_pypdf2 = pypdf2_texts_map.get(i, "") # Get text for current image index if available
            
            # If text extraction from PyPDF2 yields little or no text, use OCR on the image
            if text_from_pypdf2 and len(text_from_pypdf2.strip()) > 100: # Arbitrary threshold for "good" text
                extracted_texts.append(text_from_pypdf2)
            else:
                # Use OCR on the current page image
                # The image_obj is already a PIL Image
                ocr_text = extract_text_from_image(image_obj) 
                extracted_texts.append(ocr_text)
        
        # At this point, len(pdf_images_pil) should be equal to len(extracted_texts)
        return pdf_images_pil, extracted_texts
        
    except pdf2image.exceptions.PDFInfoNotInstalledError:
        print("Poppler not installed or not in PATH. pdf2image cannot function.")
        st.error("PDF processing error: Poppler utilities are not installed. Please check server configuration.")
        return [], []
    except Exception as e:
        # General error catching during PDF processing
        print(f"Error processing PDF: {e}")
        # Optionally, provide a user-friendly message via Streamlit if appropriate here,
        # or let the caller (app.py) handle it.
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
