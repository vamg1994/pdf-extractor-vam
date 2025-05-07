import streamlit as st
import os
import tempfile
from pdf_processor import process_pdf, get_page_count
from ocr_processor import extract_text_from_image
import io
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="PDF Reader with OCR",
    page_icon="📑",
    layout="wide"
)

# App title and description
st.title("PDF Reader with OCR")
st.markdown("Upload PDFs or images to extract and view text content. Navigate through pages easily.")

# Initialize session state variables if they don't exist
if 'pdf_pages' not in st.session_state:
    st.session_state.pdf_pages = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = []
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 0
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False
if 'file_name' not in st.session_state:
    st.session_state.file_name = ""
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Text"  # Default to text view

def handle_file_upload():
    """Process uploaded file (PDF or image)"""
    uploaded_file = st.file_uploader("Upload a PDF or image file", type=["pdf", "png", "jpg", "jpeg", "tiff"])

    if uploaded_file is not None:
        # Reset session state for new upload
        if st.session_state.file_name != uploaded_file.name:
            st.session_state.pdf_pages = []
            st.session_state.extracted_text = []
            st.session_state.current_page = 0
            st.session_state.total_pages = 0
            st.session_state.search_results = []
            st.session_state.file_processed = False
            st.session_state.file_name = uploaded_file.name

        if not st.session_state.file_processed:
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            with st.spinner("Processing file..."):
                if file_extension == '.pdf':
                    # Create a temporary file to store the uploaded PDF
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        temp_file_path = temp_file.name
                    
                    # Process PDF file
                    st.session_state.pdf_pages, st.session_state.extracted_text = process_pdf(temp_file_path)
                    st.session_state.total_pages = len(st.session_state.pdf_pages)
                    
                    # Remove temporary file
                    os.unlink(temp_file_path)
                
                else:  # Image file
                    # Process image file
                    image = Image.open(uploaded_file)
                    st.session_state.pdf_pages = [image]
                    
                    # Use OCR to extract text
                    extracted_text = extract_text_from_image(image)
                    st.session_state.extracted_text = [extracted_text]
                    st.session_state.total_pages = 1
                
                st.session_state.file_processed = True
                st.success(f"File processed successfully! Total pages: {st.session_state.total_pages}")

def display_navigation_controls():
    """Display navigation controls for multi-page documents"""
    if st.session_state.total_pages > 0:
        col1, col2, col3, col4 = st.columns([1, 3, 3, 1])
        
        with col1:
            if st.button("⏪ First"):
                st.session_state.current_page = 0
                st.rerun()
            
        with col2:
            if st.button("◀️ Previous"):
                if st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
                    st.rerun()
                    
        with col3:
            if st.button("Next ▶️"):
                if st.session_state.current_page < st.session_state.total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
                    
        with col4:
            if st.button("Last ⏩"):
                st.session_state.current_page = st.session_state.total_pages - 1
                st.rerun()
        
        # Page number indicator and selector
        col_slider, col_indicator = st.columns([3, 1])
        
        with col_slider:
            new_page = st.slider("Page Navigation", 1, max(1, st.session_state.total_pages), 
                                 st.session_state.current_page + 1) - 1
            if new_page != st.session_state.current_page:
                st.session_state.current_page = new_page
                st.rerun()
                
        with col_indicator:
            st.markdown(f"**Page {st.session_state.current_page + 1} of {st.session_state.total_pages}**")

def display_search_functionality():
    """Implement search functionality for extracted text"""
    if len(st.session_state.extracted_text) > 0:
        search_term = st.text_input("Search in document", value=st.session_state.search_term)
        
        if search_term != st.session_state.search_term:
            st.session_state.search_term = search_term
            
            if search_term:
                # Search for the term in all pages
                search_results = []
                for page_num, text in enumerate(st.session_state.extracted_text):
                    if search_term.lower() in text.lower():
                        search_results.append(page_num)
                
                st.session_state.search_results = search_results
                
                if search_results:
                    st.success(f"Found matches on {len(search_results)} pages")
                    # Jump to the first result page
                    if st.button("Go to first result"):
                        st.session_state.current_page = search_results[0]
                        st.rerun()
                else:
                    st.warning("No matches found")
            else:
                st.session_state.search_results = []

def display_content():
    """Display the current page content based on view mode"""
    if st.session_state.total_pages > 0 and st.session_state.current_page < st.session_state.total_pages:
        # View mode toggle
        col1, col2 = st.columns([1, 7])
        with col1:
            view_options = ["Text", "Original"]
            view_mode = st.radio("View Mode", view_options, 
                                 index=view_options.index(st.session_state.view_mode))
            
            if view_mode != st.session_state.view_mode:
                st.session_state.view_mode = view_mode
                st.rerun()
        
        # Container for displaying content
        content_container = st.container()
        
        with content_container:
            current_page = st.session_state.current_page
            
            # Highlight the page number if it's in search results
            if current_page in st.session_state.search_results and st.session_state.search_term:
                st.markdown(f"<p style='background-color: #FFFF00;'>Page {current_page + 1} (Match found)</p>", 
                           unsafe_allow_html=True)
            
            if st.session_state.view_mode == "Text":
                # Display the extracted text with search term highlighted
                if current_page < len(st.session_state.extracted_text):
                    text = st.session_state.extracted_text[current_page]
                    
                    # Highlight search term if present
                    if st.session_state.search_term and text:
                        highlighted_text = text.replace(
                            st.session_state.search_term, 
                            f"**{st.session_state.search_term}**"
                        )
                        st.markdown(highlighted_text)
                    else:
                        st.text_area("Extracted Text", text, height=400)
                else:
                    st.warning("No text content available for this page.")
            
            else:  # Original view
                if current_page < len(st.session_state.pdf_pages):
                    image = st.session_state.pdf_pages[current_page]
                    st.image(image, caption=f"Page {current_page + 1}", use_container_width=True)
                else:
                    st.warning("No image content available for this page.")

def main():
    """Main application function"""
    # File upload section
    handle_file_upload()
    
    # If file is processed, show navigation, search and content
    if st.session_state.file_processed:
        st.markdown("---")
        display_navigation_controls()
        
        st.markdown("---")
        display_search_functionality()
        
        st.markdown("---")
        display_content()
    
    # Show instruction message if no file is uploaded
    else:
        st.info("Please upload a PDF or image file to get started.")
        st.markdown("""
        ### Features:
        - Extract text from PDF documents
        - Use OCR for image-based content
        - Navigate through pages easily
        - Search for specific text
        - Toggle between text and original view
        """)

if __name__ == "__main__":
    main()
