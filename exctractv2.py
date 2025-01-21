import os
import json
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Any
from html import unescape

class ElementorExtractionAgent:
    """Agent responsible for extracting content and colors from WordPress XML exports"""
    
    def __init__(self):
        self.namespaces = {
            'wp': 'http://wordpress.org/export/1.2/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
        }
        
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

    def extract_content(self, xml_path: str, rag_output_path: str) -> None:
        """
        Extract Elementor content and save to RAG storage
        
        Args:
            xml_path: Path to WordPress XML export
            rag_output_path: Path to save extracted data
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        extracted_data = {
            'texts': [],
            'colors': [],
            'elementor_data': []
        }

        elementor_metas = root.findall(".//wp:postmeta[wp:meta_key='_elementor_data']", 
                                     namespaces=self.namespaces)

        for meta in elementor_metas:
            meta_value = meta.find('wp:meta_value', namespaces=self.namespaces)
            if meta_value is not None and meta_value.text:
                try:
                    elementor_data = json.loads(meta_value.text)
                    extracted_data['elementor_data'].append(elementor_data)
                    
                    texts = self._extract_texts(elementor_data)
                    extracted_data['texts'].extend(texts)
                    
                    colors = self._extract_colors(elementor_data)
                    extracted_data['colors'].extend(colors)
                    
                except json.JSONDecodeError as e:
                    print(f"Failed to parse Elementor data: {e}")

        # Save to RAG file
        self._save_to_rag(extracted_data, rag_output_path)
        print(f"Successfully extracted {len(extracted_data['texts'])} texts and {len(extracted_data['colors'])} colors to {rag_output_path}")

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content by removing tags and normalizing whitespace"""
        # Remove <p> and </p> tags
        text = re.sub(r'</?p>', '', html_content)
        # Remove any other HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Unescape HTML entities
        text = unescape(text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_texts(self, data: Any) -> List[str]:
        """Extract text content from Elementor data"""
        texts = []
        
        def extract_recursive(item):
            if isinstance(item, dict):
                text_keys = [
                    'title', 'description', 'content', 'text',
                    'heading', 'subtitle', 'caption', 'testimonial_name',
                    'testimonial_job', 'title_text', 'description_text',
                    'editor', 'testimonial_content', 'content',
                    'description_text_a', 'tab_title', 'tab_content'
                ]
                
                for key in text_keys:
                    if key in item and isinstance(item[key], str):
                        cleaned_text = (
                            self._clean_html_content(item[key]) 
                            if key in ['editor', 'testimonial_content', 'tab_content'] 
                            else re.sub(r'\s+', ' ', item[key]).strip()
                        )
                        if cleaned_text and len(cleaned_text) > 3:
                            texts.append(cleaned_text)
                
                for value in item.values():
                    if isinstance(value, (dict, list)):
                        extract_recursive(value)
            
            elif isinstance(item, list):
                for element in item:
                    extract_recursive(element)

        extract_recursive(data)
        return texts

    def _extract_colors(self, data: Any) -> List[str]:
        """Extract color codes from Elementor data"""
        colors = []
        
        def extract_recursive(item):
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, str):
                        hex_matches = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', value)
                        colors.extend(hex_matches)
                    elif isinstance(value, (dict, list)):
                        extract_recursive(value)
            elif isinstance(item, list):
                for element in item:
                    extract_recursive(element)

        extract_recursive(data)
        return colors

    def _save_to_rag(self, data: Dict, output_path: str) -> None:
        """Save extracted data to RAG storage file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

