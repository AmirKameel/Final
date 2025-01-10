import os
import json
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Any, Optional, Union
from html import unescape
from dataclasses import dataclass, asdict

@dataclass
class ElementorText:
    page_name: str
    section_name: str
    element_type: str
    label: str
    content: str
    widget_id: str

@dataclass
class ElementorColor:
    page_name: str
    section_name: str
    element_type: str
    variable_name: str
    color_value: str
    widget_id: str

class EnhancedElementorExtractionAgent:
    """Enhanced agent for extracting structured content from WordPress XML exports"""
    
    def __init__(self):
        self.namespaces = {
            'wp': 'http://wordpress.org/export/1.2/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
        }
        
        self.text_label_mapping = {
            'heading': ['title', 'heading', 'title_text'],
            'description': ['description', 'description_text', 'editor', 'text'],
            'button': ['button_text', 'text'],
            'testimonial': ['testimonial_name', 'testimonial_job', 'testimonial_content'],
            'tab': ['tab_title', 'tab_content'],
            'list': ['list_title', 'list_description']
        }
        
        self.color_variable_mapping = {
            'background': ['_background_color', 'background_color', 'bg_color'],
            'text': ['color', 'text_color', 'title_color'],
            'hover': ['hover_color', '_hover_color', 'hover_bg_color'],
            'border': ['border_color', '_border_color'],
            'overlay': ['overlay_color', '_overlay_color']
        }
        
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

    def extract_content(self, xml_path: str, rag_output_path: str) -> None:
        """Extract Elementor content with page structure"""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        extracted_data = {
            'pages': {}
        }

        # Find all posts with Elementor data
        posts = root.findall(".//item", namespaces=self.namespaces)
        
        for post in posts:
            # Get page title and slug
            title_elem = post.find('title')
            post_name_elem = post.find('wp:post_name', namespaces=self.namespaces)
            
            if title_elem is None or post_name_elem is None:
                continue
                
            title = title_elem.text
            post_name = post_name_elem.text
            
            elementor_meta = post.find(
                ".//wp:postmeta[wp:meta_key='_elementor_data']",
                namespaces=self.namespaces
            )
            
            if elementor_meta is not None:
                meta_value = elementor_meta.find('wp:meta_value', namespaces=self.namespaces)
                if meta_value is not None and meta_value.text:
                    try:
                        elementor_data = json.loads(meta_value.text)
                        page_data = self._extract_page_data(elementor_data, title, post_name)
                        extracted_data['pages'][post_name] = page_data
                        print(f"Processed page: {title}")
                        
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse Elementor data for page {title}: {e}")

        # Save to RAG file
        self._save_to_rag(extracted_data, rag_output_path)
        print(f"Successfully extracted content from {len(extracted_data['pages'])} pages to {rag_output_path}")

    def _extract_page_data(self, elementor_data: Union[List, Dict], page_title: str, page_slug: str) -> Dict:
        """Extract structured data for a single page"""
        page_data = {
            'title': page_title,
            'slug': page_slug,
            'sections': [],
            'texts': [],
            'colors': []
        }
        
        def process_element(element: Union[List, Dict], section_name: str = "") -> None:
            """Process individual elements, handling both lists and dictionaries"""
            if isinstance(element, list):
                for item in element:
                    process_element(item, section_name)
                return
                
            if not isinstance(element, dict):
                return
                
            element_type = element.get('elType', '')
            widget_type = element.get('widgetType', '')
            element_id = element.get('id', '')
            
            # Process section name
            if element_type == 'section':
                settings = element.get('settings', {})
                if isinstance(settings, dict):
                    section_name = settings.get('section_label', f"section_{element_id}")
            
            # Extract texts
            texts = self._extract_labeled_texts(
                element, 
                page_title, 
                section_name,
                element_type or widget_type,
                element_id
            )
            page_data['texts'].extend(texts)
            
            # Extract colors
            colors = self._extract_labeled_colors(
                element,
                page_title,
                section_name,
                element_type or widget_type,
                element_id
            )
            page_data['colors'].extend(colors)
            
            # Process child elements
            if 'elements' in element:
                child_elements = element['elements']
                if isinstance(child_elements, (list, dict)):
                    process_element(child_elements, section_name)
            
            # Add section data
            if element_type == 'section':
                page_data['sections'].append({
                    'name': section_name,
                    'id': element_id,
                    'type': element_type
                })
        
        # Start processing from the root element(s)
        process_element(elementor_data)
        return page_data

    def _extract_labeled_texts(
        self, 
        element: Dict, 
        page_name: str,
        section_name: str,
        element_type: str,
        widget_id: str
    ) -> List[Dict]:
        """Extract texts with their labels"""
        texts = []
        settings = element.get('settings', {})
        
        if not isinstance(settings, dict):
            return texts
            
        for label_category, keys in self.text_label_mapping.items():
            for key in keys:
                if key in settings:
                    content = settings[key]
                    if isinstance(content, str):
                        cleaned_text = self._clean_html_content(content)
                        if cleaned_text:
                            text = ElementorText(
                                page_name=page_name,
                                section_name=section_name,
                                element_type=element_type,
                                label=f"{label_category}_{key}",
                                content=cleaned_text,
                                widget_id=widget_id
                            )
                            texts.append(asdict(text))
        
        return texts

    def _extract_labeled_colors(
        self,
        element: Dict,
        page_name: str,
        section_name: str,
        element_type: str,
        widget_id: str
    ) -> List[Dict]:
        """Extract colors with their variable names"""
        colors = []
        settings = element.get('settings', {})
        
        if not isinstance(settings, dict):
            return colors
            
        for color_type, keys in self.color_variable_mapping.items():
            for key in keys:
                if key in settings:
                    color_value = settings[key]
                    if isinstance(color_value, str) and re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_value):
                        color = ElementorColor(
                            page_name=page_name,
                            section_name=section_name,
                            element_type=element_type,
                            variable_name=f"{color_type}_{key}",
                            color_value=color_value,
                            widget_id=widget_id
                        )
                        colors.append(asdict(color))
        
        return colors

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content by removing tags and normalizing whitespace"""
        text = re.sub(r'</?p>', '', html_content)
        text = re.sub(r'<[^>]+>', '', text)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _save_to_rag(self, data: Dict, output_path: str) -> None:
        """Save extracted data to RAG storage file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    extractor = EnhancedElementorExtractionAgent()
    extractor.extract_content(
        xml_path='input/gbptheme.WordPress.2024-11-13.xml',
        rag_output_path='data/elementor_structured_content.json'
    )