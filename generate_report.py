import os
import uuid
from fpdf import FPDF
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_report(detections, detected_image_path, location=None, latitude=None, longitude=None):
    """
    Generate a PDF report for pothole detections.
    
    Args:
        detections: List of detection results
        detected_image_path: Path to the image with detections
        location: Optional location string
        latitude: Optional latitude coordinate
        longitude: Optional longitude coordinate
    
    Returns:
        Path to the generated PDF report or None if failed
    """
    logger.info(f"Starting report generation for image: {detected_image_path}")
    
    try:
        # Validate input parameters
        if not detected_image_path:
            logger.error("No image path provided")
            return None
            
        if not isinstance(detections, list):
            logger.error(f"Invalid detections format. Expected list, got {type(detections)}")
            return None

        # Verify image file exists and is accessible
        if not os.path.exists(detected_image_path):
            logger.error(f"Detection image not found at: {detected_image_path}")
            return None
            
        if not os.access(detected_image_path, os.R_OK):
            logger.error(f"No read permission for image at: {detected_image_path}")
            return None

        # Verify reports directory exists and is writable
        project_root = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(project_root, "reports")
        
        if not os.path.exists(reports_dir):
            try:
                os.makedirs(reports_dir)
                logger.info(f"Created reports directory at: {reports_dir}")
            except Exception as e:
                logger.error(f"Failed to create reports directory: {str(e)}")
                return None

        if not os.access(reports_dir, os.W_OK):
            logger.error(f"No write permission for reports directory: {reports_dir}")
            return None

        # Generate report filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"report_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        report_path = os.path.join(reports_dir, report_filename)
        logger.debug(f"Report will be saved as: {report_path}")
        
        # Initialize PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Add copyright symbol in top left
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(128, 128, 128)  # Gray color for copyright
        pdf.set_xy(20, 10)  # Position at top left with small margin
        pdf.cell(0, 10, "© " + str(datetime.now().year), 0, 1, 'L')
        
        # Set document properties
        pdf.set_title("Pothole Detection Report")
        pdf.set_author("Pothole Detection System")
        
        # Add header with a line underneath
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(31, 73, 125)  # Professional blue color
        pdf.cell(0, 15, "Pothole Detection Report", 0, 1, 'C')
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(10)
        
        # Add generation timestamp with improved formatting
        pdf.set_font("Arial", 'I', 12)
        pdf.set_text_color(128, 128, 128)  # Gray color for metadata
        pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 0, 1)
        pdf.ln(5)
        
        # Add location information if available with better formatting
        if any([location, latitude, longitude]):
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(31, 73, 125)
            pdf.cell(0, 12, "Location Information", 0, 1)
            pdf.set_draw_color(200, 200, 200)  # Light gray for lines
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.set_font("Arial", '', 12)
            pdf.set_text_color(0, 0, 0)  # Back to black for content
            
            if location:
                pdf.ln(5)
                pdf.cell(0, 10, f"Address: {location}", 0, 1)
            if latitude and longitude:
                pdf.cell(0, 10, f"Coordinates: {latitude}, {longitude}", 0, 1)
                maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
                pdf.set_text_color(0, 0, 255)  # Blue for hyperlink
                pdf.cell(0, 10, f"View on Google Maps: {maps_url}", 0, 1)
            pdf.ln(10)
        
        # Add detection results section with improved styling
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(31, 73, 125)
        pdf.cell(0, 12, "Detection Results", 0, 1)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.set_font("Arial", '', 12)
        pdf.set_text_color(0, 0, 0)
        
        if detections and len(detections) > 0:
            pdf.ln(5)
            pdf.cell(0, 10, f"Total Potholes Detected: {len(detections)}", 0, 1)
            for i, detection in enumerate(detections, 1):
                try:
                    box = detection['box']
                    conf = detection['confidence']
                    class_name = detection['class']
                    pdf.set_fill_color(245, 245, 245)  # Light gray background
                    pdf.cell(0, 12, f"Pothole {i}: Type: {class_name} | Confidence: {conf:.1%} | Location: {box}", 1, 1, fill=True)
                except Exception as e:
                    logger.error(f"Error processing detection {i}: {str(e)}")
                    pdf.cell(0, 10, f"Pothole {i}: Details unavailable", 0, 1)
        else:
            pdf.ln(5)
            pdf.cell(0, 10, "No potholes detected in the image.", 0, 1)
        
        pdf.ln(10)
        
        # Add detected image with better error handling
        try:
            if not os.path.isfile(detected_image_path):
                raise FileNotFoundError(f"Image file not found: {detected_image_path}")
                
            # Check if image file is readable
            with open(detected_image_path, 'rb') as f:
                pass
                
            img_width = 180
            x_pos = (210 - img_width) / 2
            
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 10, "Detection Result:", 0, 1, 'C')
            
            logger.debug(f"Adding image to PDF from: {detected_image_path}")
            pdf.image(detected_image_path, x=x_pos, y=None, w=img_width)
            pdf.ln(5)
            
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {str(e)}")
            pdf.cell(0, 10, "[Image file not found]", 0, 1)
        except PermissionError as e:
            logger.error(f"Permission denied accessing image: {str(e)}")
            pdf.cell(0, 10, "[Cannot access image file]", 0, 1)
        except Exception as e:
            logger.error(f"Error adding image to PDF: {str(e)}")
            logger.error(f"Image path attempted: {detected_image_path}")
            pdf.cell(0, 10, "[Image could not be included in report]", 0, 1)
        
        # Add footer with improved styling
        pdf.set_y(-20)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 15, "Generated by Pothole Detection System", 0, 0, 'C')
        
        # Save the PDF with better error handling
        try:
            # Create a temporary file first to verify write permissions
            temp_path = os.path.join(reports_dir, f"temp_{uuid.uuid4().hex[:8]}.txt")
            try:
                with open(temp_path, 'w') as f:
                    f.write('test')
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Write permission test failed: {str(e)}")
                return None

            # Save the PDF
            pdf.output(report_path)
            logger.info(f"Report saved successfully at: {report_path}")
            
            # Verify the file was created
            if not os.path.exists(report_path):
                raise FileNotFoundError("PDF file was not created")
                
            # Return web-accessible path
            web_path = f'/reports/{report_filename}'
            logger.debug(f"Returning web path: {web_path}")
            return web_path
            
        except PermissionError as e:
            logger.error(f"Permission denied when saving PDF: {str(e)}")
            return None
        except FileNotFoundError as e:
            logger.error(f"Failed to create PDF file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error saving PDF: {str(e)}")
            logger.error(f"Attempted to save to: {report_path}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None