import json
import xml.etree.ElementTree as ET
import os

def scan_background_colors(elementor_data):
    """Scan and store original background colors"""
    bg_colors = {}
    
    def scan_element(element):
        if isinstance(element, dict):
            if 'id' in element and 'settings' in element:
                element_id = element['id']
                settings = element['settings']
                
                # Background color keys to preserve
                bg_keys = [
                    'background_color',
                    'background_overlay_color',
                    '_background_color',
                    '_background_background',
                    'background_overlay_background'
                ]
                
                # Store original colors
                for key in bg_keys:
                    if key in settings and settings[key]:
                        if element_id not in bg_colors:
                            bg_colors[element_id] = {}
                        bg_colors[element_id][key] = settings[key]
            
            if 'elements' in element:
                for child in element['elements']:
                    scan_element(child)
    
    if isinstance(elementor_data, list):
        for item in elementor_data:
            scan_element(item)
    else:
        scan_element(elementor_data)
    
    return bg_colors

def process_elementor_data(elementor_data, color_map, original_bg_colors):
    """Process colors while preserving backgrounds"""
    
    def process_element(element):
        if isinstance(element, dict):
            if 'settings' in element and 'id' in element:
                settings = element['settings']
                element_id = element['id']
                
                # Restore original background colors
                if element_id in original_bg_colors:
                    for key, value in original_bg_colors[element_id].items():
                        settings[key] = value
                
                # Replace other colors in settings
                if isinstance(settings, dict):  # Add type check
                    for setting_key in list(settings.keys()):  # Convert to list to avoid runtime modification
                        value = settings[setting_key]
                        if isinstance(value, str):
                            # Skip background-related keys
                            if not any(bg in setting_key.lower() for bg in ['background', 'bg_']):
                                for orig_color in color_map:
                                    if orig_color in value:
                                        settings[setting_key] = value.replace(orig_color, color_map[orig_color])
            
            # Process nested elements
            if 'elements' in element and isinstance(element['elements'], list):
                for child in element['elements']:
                    process_element(child)
                    
    # Handle both list and dict input
    if isinstance(elementor_data, list):
        for item in elementor_data:
            process_element(item)
    else:
        process_element(elementor_data)
    
    return elementor_data

def replace_text_and_colors(xml_file_path, json_file_path, output_file_path):
    ET.register_namespace('wp', 'http://wordpress.org/export/1.2/')
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    
    text_transformations = data.get("text_transformations", [])
    color_map = dict(zip(
        data["color_palette"]["original_colors"],
        data["color_palette"]["new_colors"]
    ))

    # Replace text in the XML (based on your provided method)
    for transformation in text_transformations:
        original_text = transformation["original"]
        transformed_text = transformation["transformed"]
        for elem in root.iter():
            if elem.text and original_text in elem.text:
                elem.text = elem.text.replace(original_text, transformed_text)
            if elem.tail and original_text in elem.tail:
                elem.tail = elem.tail.replace(original_text, transformed_text)
            if elem.attrib:
                for attr_key, attr_value in elem.attrib.items():
                    if original_text in attr_value:
                        elem.attrib[attr_key] = attr_value.replace(original_text, transformed_text)

    
    # Store original background colors
    original_colors = {}
    for item in root.findall('.//wp:meta_value', {'wp': 'http://wordpress.org/export/1.2/'}):
        if item.text and '[{' in item.text:
            try:
                elementor_data = json.loads(item.text)
                page_colors = scan_background_colors(elementor_data)
                original_colors.update(page_colors)
            except json.JSONDecodeError:
                continue
    
    # Process XML with preserved backgrounds
    for item in root.findall('.//wp:meta_value', {'wp': 'http://wordpress.org/export/1.2/'}):
        if item.text and '[{' in item.text:
            try:
                elementor_data = json.loads(item.text)
                modified_data = process_elementor_data(elementor_data, color_map, original_colors)
                item.text = json.dumps(modified_data)
            except json.JSONDecodeError:
                continue
    
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    tree.write(output_file_path, encoding='utf-8', xml_declaration=True)

