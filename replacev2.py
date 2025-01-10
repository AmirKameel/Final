import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
import copy
import re

class ElementorReplacementAgent:
    """Agent responsible for replacing original content with transformed content in WordPress XML"""
    
    def __init__(self):
        self.namespaces = {
            'wp': 'http://wordpress.org/export/1.2/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'excerpt': 'http://wordpress.org/export/1.2/excerpt/'
        }
        
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

    def replace_content(self, 
                       xml_path: str, 
                       transformed_content_path: str, 
                       output_xml_path: str) -> None:
        """
        Replace original content with transformed content in WordPress XML
        
        Args:
            xml_path: Path to original WordPress XML
            transformed_content_path: Path to transformed content JSON
            output_xml_path: Path to save modified XML
        """
        try:
            # Load transformed content
            with open(transformed_content_path, 'r', encoding='utf-8') as f:
                transformed_data = json.load(f)

            # Parse XML
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Process each page
            for page_slug, page_data in transformed_data['pages'].items():
                # Find corresponding post in XML
                post = root.find(
                    f".//item[wp:post_name='{page_slug}']",
                    namespaces=self.namespaces
                )
                
                if post is None:
                    print(f"Warning: Could not find post with slug: {page_slug}")
                    continue

                # Get Elementor data
                elementor_meta = post.find(
                    ".//wp:postmeta[wp:meta_key='_elementor_data']",
                    namespaces=self.namespaces
                )
                
                if elementor_meta is None:
                    print(f"Warning: No Elementor data found for post: {page_slug}")
                    continue

                meta_value = elementor_meta.find('wp:meta_value', namespaces=self.namespaces)
                if meta_value is not None and meta_value.text:
                    try:
                        # Parse Elementor data
                        elementor_data = json.loads(meta_value.text)
                        
                        # Replace content
                        modified_data = self._replace_elementor_content(
                            elementor_data,
                            page_data['transformed_texts'],
                            page_data['transformed_colors']
                        )
                        
                        # Update XML with modified data
                        meta_value.text = json.dumps(modified_data)
                        
                        print(f"Successfully updated content for page: {page_slug}")
                        
                    except json.JSONDecodeError as e:
                        print(f"Error parsing Elementor data for page {page_slug}: {e}")
                        continue

            # Save modified XML
            tree.write(output_xml_path, encoding='utf-8', xml_declaration=True)
            print(f"Successfully saved modified XML to: {output_xml_path}")
            
        except Exception as e:
            print(f"Error in replace_content: {e}")
            raise

    def _replace_elementor_content(self, 
                                 elementor_data: Any,
                                 transformed_texts: List[Dict],
                                 transformed_colors: List[Dict]) -> Any:
        """Replace content in Elementor data structure"""
        
        def replace_recursive(element: Any, section_name: str = "") -> None:
            """Recursively process Elementor elements"""
            if isinstance(element, dict):
                # Get element identifiers
                element_type = element.get('elType', '')
                widget_type = element.get('widgetType', '')
                element_id = element.get('id', '')
                
                # Update section name if applicable
                if element_type == 'section':
                    settings = element.get('settings', {})
                    if isinstance(settings, dict):
                        section_name = settings.get('section_label', f"section_{element_id}")
                
                # Replace text content
                if 'settings' in element and isinstance(element['settings'], dict):
                    settings = element['settings']
                    
                    # Replace text content
                    for transform in transformed_texts:
                        if (transform['widget_id'] == element_id and
                            transform['section_name'] == section_name):
                            
                            # Extract the key from the label
                            content_key = transform['label'].split('_')[-1]
                            if content_key in settings:
                                settings[content_key] = transform['transformed_content']
                    
                    # Replace colors
                    for transform in transformed_colors:
                        if (transform['widget_id'] == element_id and
                            transform['section_name'] == section_name):
                            
                            # Extract the key from the variable name
                            color_key = transform['variable_name'].split('_', 1)[-1]
                            if color_key in settings:
                                settings[color_key] = transform['transformed_color']
                
                # Process child elements
                if 'elements' in element:
                    for child in element['elements']:
                        replace_recursive(child, section_name)
            
            elif isinstance(element, list):
                for item in element:
                    replace_recursive(item, section_name)

        # Create a deep copy to avoid modifying the original data
        modified_data = copy.deepcopy(elementor_data)
        
        # Process the entire structure
        if isinstance(modified_data, list):
            for element in modified_data:
                replace_recursive(element)
        else:
            replace_recursive(modified_data)
            
        return modified_data

    def _verify_replacement(self, 
                          elementor_data: Any, 
                          transformed_texts: List[Dict],
                          transformed_colors: List[Dict]) -> None:
        """Verify that content was replaced correctly"""
        replaced_texts = set()
        replaced_colors = set()
        
        def verify_recursive(element: Any, section_name: str = "") -> None:
            if isinstance(element, dict):
                element_id = element.get('id', '')
                
                if element.get('elType') == 'section':
                    settings = element.get('settings', {})
                    if isinstance(settings, dict):
                        section_name = settings.get('section_label', f"section_{element_id}")
                
                settings = element.get('settings', {})
                if isinstance(settings, dict):
                    # Check text replacements
                    for transform in transformed_texts:
                        if (transform['widget_id'] == element_id and
                            transform['section_name'] == section_name):
                            content_key = transform['label'].split('_')[-1]
                            if content_key in settings:
                                if settings[content_key] == transform['transformed_content']:
                                    replaced_texts.add(
                                        (transform['widget_id'], transform['label'])
                                    )
                    
                    # Check color replacements
                    for transform in transformed_colors:
                        if (transform['widget_id'] == element_id and
                            transform['section_name'] == section_name):
                            color_key = transform['variable_name'].split('_', 1)[-1]
                            if color_key in settings:
                                if settings[color_key] == transform['transformed_color']:
                                    replaced_colors.add(
                                        (transform['widget_id'], transform['variable_name'])
                                    )
                
                # Process child elements
                if 'elements' in element:
                    for child in element['elements']:
                        verify_recursive(child, section_name)
            
            elif isinstance(element, list):
                for item in element:
                    verify_recursive(item, section_name)

        # Perform verification
        if isinstance(elementor_data, list):
            for element in elementor_data:
                verify_recursive(element)
        else:
            verify_recursive(elementor_data)
        
        # Report results
        total_texts = len(transformed_texts)
        total_colors = len(transformed_colors)
        replaced_text_count = len(replaced_texts)
        replaced_color_count = len(replaced_colors)
        
        print(f"\nReplacement Verification Results:")
        print(f"- Texts replaced: {replaced_text_count}/{total_texts}")
        print(f"- Colors replaced: {replaced_color_count}/{total_colors}")
        
        if replaced_text_count < total_texts:
            print("Warning: Some texts were not replaced")
        if replaced_color_count < total_colors:
            print("Warning: Some colors were not replaced")

    def _clean_elementor_data(self, data: Any) -> Any:
        """Clean and validate Elementor data"""
        if isinstance(data, dict):
            # Remove any invalid or empty values
            cleaned = {}
            for key, value in data.items():
                if value is not None:
                    cleaned[key] = self._clean_elementor_data(value)
            return cleaned
        
        elif isinstance(data, list):
            # Clean each item in the list
            return [self._clean_elementor_data(item) for item in data if item is not None]
        
        elif isinstance(data, str):
            # Clean string values
            return data.strip()
        
        return data

if __name__ == '__main__':
    replacer = ElementorReplacementAgent()
    replacer.replace_content(
        xml_path='input/gbptheme.WordPress.2024-11-13.xml',
        transformed_content_path='data/transformed_structured_content.json',
        output_xml_path='output/modified_wordpress_export.xml'
    )