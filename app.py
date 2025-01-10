from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from typing import Dict, Optional
import json
from datetime import datetime

# Import the agents
from exctractv2 import EnhancedElementorExtractionAgent
from transformv2 import EnhancedContentTransformationAgent
from replacev2 import ElementorReplacementAgent

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xml'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ElementorOrchestrator:
    def __init__(self, openai_api_key: str):
        self.extraction_agent = EnhancedElementorExtractionAgent()
        self.transformation_agent = EnhancedContentTransformationAgent(openai_api_key)
        self.replacement_agent = ElementorReplacementAgent()
        
    def process_wordpress_export(self, 
                               input_xml_path: str,
                               style_description: str) -> Dict:
        """
        Process WordPress export file through all agents
        """
        try:
            # Create temporary file paths
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = os.path.join(app.config['UPLOAD_FOLDER'], timestamp)
            os.makedirs(base_dir, exist_ok=True)
            
            extracted_path = os.path.join(base_dir, 'elementor_structured_content.json')
            transformed_path = os.path.join(base_dir, 'transformed_structured_content.json')
            output_xml_path = os.path.join(base_dir, 'modified_wordpress_export.xml')
            
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
                'output_xml_path': output_xml_path
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
            # Read the output XML file
            with open(result['output_xml_path'], 'r', encoding='utf-8') as f:
                xml_content = f.read()
                
            # Clean up temporary files
            os.remove(file_path)
            os.remove(result['output_xml_path'])
            
            return jsonify({
                'status': 'success',
                'transformed_content': result['transformed_content'],
                'xml_content': xml_content
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error processing file: {str(e)}'
        }), 500

@app.route('/api/extract-content', methods=['POST'])
def extract_content():
    """Extract content from WordPress export file"""
    if 'file' not in request.files:
        return jsonify({
            'status': 'error',
            'message': 'No file uploaded'
        }), 400
        
    file = request.files['file']
    
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
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'extracted_content.json')
        file.save(file_path)
        
        # Extract content
        orchestrator.extraction_agent.extract_content(
            xml_path=file_path,
            rag_output_path=output_path
        )
        
        # Read the results
        with open(output_path, 'r') as f:
            extracted_content = json.load(f)
            
        # Clean up
        os.remove(file_path)
        os.remove(output_path)
        
        return jsonify({
            'status': 'success',
            'extracted_content': extracted_content
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error extracting content: {str(e)}'
        }), 500

@app.route('/api/transform-content', methods=['POST'])
def transform_content():
    """Transform extracted content"""
    data = request.get_json()
    
    if not data or 'extracted_content' not in data or 'style_description' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing required fields'
        }), 400
    
    try:
        # Save extracted content to temporary file
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_extracted.json')
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_transformed.json')
        
        with open(input_path, 'w') as f:
            json.dump(data['extracted_content'], f)
        
        # Transform content
        orchestrator.transformation_agent.transform_content(
            rag_input_path=input_path,
            transformed_output_path=output_path,
            style_description=data['style_description']
        )
        
        # Read results
        with open(output_path, 'r') as f:
            transformed_content = json.load(f)
            
        # Clean up
        os.remove(input_path)
        os.remove(output_path)
        
        return jsonify({
            'status': 'success',
            'transformed_content': transformed_content
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error transforming content: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)