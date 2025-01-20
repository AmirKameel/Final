from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from typing import Dict, Optional
import json
from datetime import datetime

# Import the agents
from exctractv2 import ElementorExtractionAgent
from transformv2 import ContentTransformationAgent
from replacev2 import ContentApplicationAgent

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'elementor_uploads')
ALLOWED_EXTENSIONS = {'xml'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ElementorOrchestrator:
    def __init__(self, openai_api_key: str):
        self.extraction_agent = ElementorExtractionAgent()
        self.transformation_agent = ContentTransformationAgent(openai_api_key)
        self.replacement_agent = ContentApplicationAgent()
        
    def process_wordpress_export(self, 
                               input_xml_path: str,
                               style_description: str) -> Dict:
        """
        Process WordPress export file through all agents
        """
        try:
            # Create temporary file paths with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = os.path.join(app.config['UPLOAD_FOLDER'], timestamp)
            os.makedirs(base_dir, exist_ok=True)
            
            extracted_path = os.path.join(base_dir, 'elementor_structured_content.json')
            transformed_path = os.path.join(base_dir, 'transformed_structured_content.json')
            output_xml_path = os.path.join(base_dir, f'modified_wordpress_export_{timestamp}.xml')
            
            # Step 1: Extract content
            self.extraction_agent.extract_content(
                xml_path=input_xml_path,
                rag_output_path=extracted_path
            )
            
            # Step 2: Transform content
            self.transformation_agent.transform_content(
                rag_input_path=extracted_path,
                transformed_output_path=transformed_path,
                style_description=style_description
            )
            
            # Step 3: Replace content in XML
            self.replacement_agent.replace_content(
                xml_path=input_xml_path,
                transformed_content_path=transformed_path,
                output_xml_path=output_xml_path
            )
            
            # Read the results
            with open(transformed_path, 'r') as f:
                transformation_results = json.load(f)
            
            return {
                'status': 'success',
                'message': 'WordPress export processed successfully',
                'transformed_content': transformation_results,
                'output_xml_path': output_xml_path,
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error processing WordPress export: {str(e)}'
            }

# Initialize orchestrator with environment variable
orchestrator = ElementorOrchestrator(os.getenv('OPENAI_API_KEY'))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/process-wordpress', methods=['POST'])
def process_wordpress():
    """Process WordPress export file"""
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({
            'status': 'error',
            'message': 'No file uploaded'
        }), 400
        
    file = request.files['file']
    style_description = request.form.get('style_description', '')
    
    if file.filename == '':
        return jsonify({
            'status': 'error',
            'message': 'No file selected'
        }), 400
        
    if not allowed_file(file.filename):
        return jsonify({
            'status': 'error',
            'message': 'Invalid file type. Only XML files are allowed.'
        }), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the file
        result = orchestrator.process_wordpress_export(
            input_xml_path=file_path,
            style_description=style_description
        )
        
        if result['status'] == 'success':
            # Generate download URL
            timestamp = result['timestamp']
            download_url = f"/api/download/{timestamp}"
            
            return jsonify({
                'status': 'success',
                'transformed_content': result['transformed_content'],
                'download_url': download_url,
                'message': 'Content transformed successfully. Use the download_url to get the modified XML file.'
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error processing file: {str(e)}'
        }), 500

@app.route('/api/download/<timestamp>', methods=['GET'])
def download_file(timestamp):
    """Download the generated XML file"""
    try:
        # Find the XML file in the timestamp directory
        base_dir = os.path.join(app.config['UPLOAD_FOLDER'], timestamp)
        xml_files = list(Path(base_dir).glob('modified_wordpress_export_*.xml'))
        
        if not xml_files:
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 404
            
        xml_file = xml_files[0]
        
        return send_file(
            xml_file,
            as_attachment=True,
            download_name=f'modified_wordpress_export_{timestamp}.xml',
            mimetype='application/xml'
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error downloading file: {str(e)}'
        }), 500

@app.route('/api/cleanup/<timestamp>', methods=['DELETE'])
def cleanup_files(timestamp):
    """Clean up temporary files for a specific process"""
    try:
        base_dir = os.path.join(app.config['UPLOAD_FOLDER'], timestamp)
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
            return jsonify({
                'status': 'success',
                'message': f'Cleaned up files for timestamp: {timestamp}'
            })
        return jsonify({
            'status': 'error',
            'message': 'Directory not found'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error cleaning up files: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
