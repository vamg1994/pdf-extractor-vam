import PyPDF2
import pdf2image
import io
from PIL import Image
from ocr_processor import extract_text_from_image

def get_page_count(pdf_path):
    """Get the total number of pages in a PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception as e:
        print(f"Error getting page count: {e}")
        return 0

def process_pdf(pdf_path):
    """
    Process a PDF file, extracting both images and text
    
    Returns:
    - list of PIL Image objects (one per page)
    - list of extracted text (one string per page)
    """
    pdf_images = []
    extracted_texts = []
    
    try:
        # Convert PDF pages to images
        images = pdf2image.convert_from_path(pdf_path)
        pdf_images = images
        
        # Try to extract text directly from PDF
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                
                # If text extraction yields little or no text, use OCR
                if text and len(text.strip()) > 100:  # Arbitrary threshold
                    extracted_texts.append(text)
                else:
                    # Use OCR on the page image
                    ocr_text = extract_text_from_image(images[i])
                    extracted_texts.append(ocr_text)
        
        return pdf_images, extracted_texts
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return [], []

def extract_text_from_pdf_file(pdf_file):
    """Extract text from a PDF file object"""
    text_content = []
    
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text_content.append(page.extract_text())
        
        return text_content
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return []
