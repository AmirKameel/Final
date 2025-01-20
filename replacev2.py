import json
import xml.etree.ElementTree as ET
import os
from typing import Dict

class ContentApplicationAgent:
    """Agent responsible for applying transformed content back to WordPress XML"""

    def __init__(self):
        # Register namespaces
        self.namespaces = {'wp': 'http://wordpress.org/export/1.2/'}
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

    def replace_text_and_colors(self, xml_file_path, json_file_path, output_file_path):
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
        
        # Extract color map from JSON data
        color_map = data.get('color_map', {})
        
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

    def validate_output(self, output_xml_path: str) -> bool:
        """Validate the output XML file."""
        try:
            tree = ET.parse(output_xml_path)
            root = tree.getroot()

            required_elements = [".//item", ".//wp:postmeta", ".//content:encoded"]

            for element in required_elements:
                elements = root.findall(element, namespaces=self.namespaces)
                if not elements:
                    print(f"Warning: Missing element {element}, but continuing validation")

            items = root.findall(".//item", namespaces=self.namespaces)
            if not items:
                print("Error: No item elements found in the XML")
                return False

            return True

        except ET.ParseError as e:
            print(f"XML validation failed: {e}")
            return False
        except Exception as e:
            print(f"Validation error: {e}")
            return False


if __name__ == '__main__':
    applicator = ContentApplicationAgent()

    try:
        # Replace text and colors
        applicator.replace_text_and_colors(
            xml_file_path='input/gbptheme.WordPress.2024-11-13.xml',
            json_file_path='data/transformed_content.json',
            output_file_path='output/modified_wordpress_export.xml'
        )

    except Exception as e:
        print(f"Error in transformation process: {e}")
