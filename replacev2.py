import json
import xml.etree.ElementTree as ET
import os

def replace_text_and_colors(xml_file_path, json_file_path, output_file_path):
    # Register the namespace to ensure the output uses 'wp' instead of 'ns0'
    ET.register_namespace('wp', 'http://wordpress.org/export/1.2/')
    
    # Check if the input files exist
    if not os.path.exists(xml_file_path):
        raise FileNotFoundError(f"XML file '{xml_file_path}' not found.")
    
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file '{json_file_path}' not found.")
    
    # Load the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Load the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # Extract text transformations and color palette
    text_transformations = data.get("text_transformations", [])
    original_colors = data["color_palette"]["original_colors"]
    new_colors = data["color_palette"]["new_colors"]

    # Create a color mapping dictionary
    color_map = dict(zip(original_colors, new_colors))

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

    # Replace colors in the XML (find-and-replace method)
    for elem in root.iter():
        if elem.attrib:
            for attr_key, attr_value in elem.attrib.items():
                for original_color, new_color in color_map.items():
                    if original_color in attr_value:
                        elem.attrib[attr_key] = attr_value.replace(original_color, new_color)

        # Also check for text content inside the element (in case the color appears in text)
        if elem.text:
            for original_color, new_color in color_map.items():
                if original_color in elem.text:
                    elem.text = elem.text.replace(original_color, new_color)
        
        # Check for tail content as well
        if elem.tail:
            for original_color, new_color in color_map.items():
                if original_color in elem.tail:
                    elem.tail = elem.tail.replace(original_color, new_color)

    # Write the updated XML to a new file
    tree.write(output_file_path, encoding='utf-8', xml_declaration=True)
    print(f"Updated XML has been saved to {output_file_path}")

# Paths to the input files
xml_file_path = "input/gbptheme.WordPress.2024-11-13.xml"  
json_file_path = "data/transformed_content.json"  
output_file_path = "output/modified_wordpress_export2.xml"  

# Run the transformation
try:
    replace_text_and_colors(xml_file_path, json_file_path, output_file_path)
except Exception as e:
    print(f"Error: {e}")
