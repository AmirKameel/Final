import json
import openai
import re
from typing import Dict, List
import os

class ContentTransformationAgent:
    """Agent responsible for transforming extracted content using GPT-4"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key

    def transform_content(self, rag_input_path: str, 
                         transformed_output_path: str, 
                         style_description: str) -> None:
        """
        Transform content based on style description
        """
        try:
            # Load extracted content
            with open(rag_input_path, 'r', encoding='utf-8') as f:
                extracted_content = json.load(f)

            print(f"Loaded {len(extracted_content['texts'])} texts and {len(extracted_content['colors'])} colors")

            # Transform content in smaller batches to avoid token limits
            batch_size = 5
            transformed_texts = []
            for i in range(0, len(extracted_content['texts']), batch_size):
                batch_texts = extracted_content['texts'][i:i + batch_size]
                batch_result = self._generate_transformed_content(
                    batch_texts,
                    extracted_content['colors'],
                    style_description
                )
                transformed_texts.extend(batch_result['text_transformations'])
            
            # Generate final color palette
            final_color_result = self._generate_color_palette(
                extracted_content['colors'],
                style_description
            )

            transformed_data = {
                'text_transformations': transformed_texts,
                'color_palette': final_color_result['color_palette'],
                'transformation_notes': final_color_result['transformation_notes']
            }

            # Verify transformations
            self._verify_transformations(transformed_data, len(extracted_content['texts']), len(extracted_content['colors']))

            # Save transformed content with proper formatting
            os.makedirs(os.path.dirname(transformed_output_path), exist_ok=True)
            with open(transformed_output_path, 'w', encoding='utf-8') as f:
                # Clean the content before dumping into JSON to remove unwanted escape characters
                cleaned_transformed_data = self._clean_transformed_data(transformed_data)
                json.dump(cleaned_transformed_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error in transform_content: {e}")
            raise

    def _clean_transformed_data(self, data: Dict) -> Dict:
        """Clean transformed data to remove unwanted escape characters."""
        cleaned_data = data.copy()
        
        # Clean text transformations
        for item in cleaned_data['text_transformations']:
            # Clean both original and transformed texts
            if isinstance(item.get('original'), str):
                item['original'] = self._remove_escape_characters(item['original'])
            if isinstance(item.get('transformed'), str):
                item['transformed'] = self._remove_escape_characters(item['transformed'])

        # Clean color palette notes
        if isinstance(cleaned_data.get('transformation_notes'), str):
            cleaned_data['transformation_notes'] = self._remove_escape_characters(cleaned_data['transformation_notes'])
        
        return cleaned_data
    
    def _remove_escape_characters(self, text: str) -> str:
        """Remove escape characters and clean up text.
        
        This improved version:
        1. Removes unnecessary backslashes
        2. Handles quoted strings properly
        3. Removes redundant quotes at start/end
        """
        if not text:
            return text
            
        # First, handle the case where the entire string is wrapped in quotes
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            # Remove outer quotes
            text = text[1:-1]
            
        # Remove unnecessary backslashes before quotes
        text = text.replace(r'\"', '"')
        text = text.replace(r'\\', '\\')
        
        # Remove any remaining unnecessary backslashes
        text = text.replace(r'\n', '\n')  # Preserve actual newlines
        text = re.sub(r'\\(?!["\\/])', '', text)  # Remove standalone backslashes
        
        # Clean up any doubled-up quotes
        text = re.sub(r'"{2,}', '"', text)
        
        return text


    def _generate_transformed_content(self, 
                                    current_texts: List[str],
                                    current_colors: List[str],
                                    style_description: str) -> Dict:
        """Generate new content using GPT-4 with improved prompt"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a WordPress theme content transformer. Transform each text to match the requested style while:
                    1. Preserving the core meaning and key information
                    2. Maintaining appropriate length and structure
                    3. Ensuring professional and coherent output
                    4. Never returning text unchanged unless explicitly requested
                    5. Make the content length close to the given not much bigger or smaller
                    6. You are taking the original text and this for the content for last desing needs your mission os to transform this content to new one based on user needs
                    Format each transformation exactly as: 'ORIGINAL: [text] 
                    NEW: [transformed text]'"""
                },
                {
                    "role": "user",
                    "content": f"""Transform these WordPress theme texts to match this user needs: {style_description}
                    so you change the each original text to new content based on user style

                    Original texts:
                    {json.dumps(current_texts, indent=2)}

                    Required format for each text:
                    ORIGINAL: [original text]
                    NEW: [transformed text]"""
                }
            ]

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            
            return self._parse_text_transformations(response.choices[0].message.content, current_texts)
            
        except Exception as e:
            print(f"Error in content generation: {e}")
            return self._generate_fallback_content(current_texts, current_colors)
    
    def _generate_fallback_content(self, current_texts: List[str], current_colors: List[str]) -> Dict:

        """Generate fallback content when GPT transformation fails"""
        return {
        "text_transformations": [
            {
                "original": text,
                "transformed": text  # Return original text as fallback
            }
            for text in current_texts
        ],
        "transformation_notes": "Fallback content generated due to transformation error"
    } 


    def _generate_color_palette(self, current_colors: List[str], style_description: str) -> Dict:
        """Generate new color palette using GPT-4"""
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[{
                    "role": "system",
                    "content": """You are a color palette generator for WordPress themes.
                    Generate new hex colors that match the requested style.
                    Always provide completely different colors than the original.
                    And generate diffrent range of the wanted colors not just generate red for all replacement if the user want red no generate red and diffrent range of the red colors
                    Return ONLY the new colors in the exact same format as the input, preserving case.
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                    Generate a new color palette matching this style: {style_description}
                    Replace these colors with new ones that match the style:
                    {json.dumps(current_colors, indent=2)}
                    
                    Return only the list of new colors in the same format, maintaining letter case.
                    Example format:
                    === COLOR PALETTE ===
                    NEW COLORS: [list of new hex codes]
                    === NOTES ===
                    [Explain your color choices]
                    """
                }],
                temperature=0.7
            )
            
            # Parse the GPT response
            response_text = response.choices[0].message.content
            
            # Extract new colors
            color_section = re.search(r'NEW COLORS:(.+?)(?===|$)', response_text, re.DOTALL)
            new_colors = []
            if color_section:
                # Extract hex colors while preserving their original case
                new_colors = re.findall(r'#[0-9a-fA-F]{3,6}', color_section.group(1))
            
            # Extract notes
            notes_section = re.search(r'=== NOTES ===(.+?)(?===|$)', response_text, re.DOTALL)
            transformation_notes = ""
            if notes_section:
                transformation_notes = notes_section.group(1).strip()
            
            # Ensure we have enough colors
            while len(new_colors) < len(current_colors):
                # If we don't have enough colors, copy from the ones we have
                new_colors.append(new_colors[len(new_colors) % len(new_colors)] if new_colors else "#000000")
            
            return {
                "color_palette": {
                    "original_colors": current_colors,
                    "new_colors": new_colors[:len(current_colors)]  # Trim to match original length
                },
                "transformation_notes": transformation_notes or "Color transformation complete"
            }
            
        except Exception as e:
            print(f"Error in color generation: {e}")
            return {
                "color_palette": {
                    "original_colors": current_colors,
                    "new_colors": current_colors  # Return original colors as fallback
                },
                "transformation_notes": f"Error in color transformation: {str(e)}"
            }

    def _parse_text_transformations(self, response_text: str, original_texts: List[str]) -> Dict:
        """Parse GPT response text into structured format"""
        text_transformations = []
        
        # Split into individual transformations
        transformations = re.split(r'ORIGINAL:', response_text)[1:]  # Skip first split
        
        for i, trans in enumerate(transformations):
            parts = trans.split('NEW:', 1)
            if len(parts) == 2:
                original = parts[0].strip()
                transformed = parts[1].strip()
                
                # Clean up any remaining formatting
                transformed = re.sub(r'ORIGINAL:.*', '', transformed).strip()
                transformed = re.sub(r'===.*===', '', transformed).strip()
                
                text_transformations.append({
                    "original": original,
                    "transformed": transformed
                })
        
        # Ensure we have a transformation for each original text
        if len(text_transformations) < len(original_texts):
            print(f"Warning: Missing transformations. Got {len(text_transformations)}, expected {len(original_texts)}")
            for text in original_texts[len(text_transformations):]:
                text_transformations.append({
                    "original": text,
                    "transformed": text
                })
        
        return {
            "text_transformations": text_transformations,
            "transformation_notes": "Text transformations completed"
        }

    def _parse_color_palette(self, response_text: str, original_colors: List[str]) -> Dict:
        """Parse color palette response"""
        new_colors = []
        transformation_notes = ""
        
        # Extract new colors
        color_section = re.search(r'NEW COLORS:(.+?)(?===|$)', response_text, re.DOTALL)
        if color_section:
            new_colors = re.findall(r'#[0-9a-fA-F]{3,6}', color_section.group(1))
        
        # Extract notes
        notes_section = re.search(r'=== NOTES ===(.+?)(?===|$)', response_text, re.DOTALL)
        if notes_section:
            transformation_notes = notes_section.group(1).strip()
        
        # Ensure we have enough colors
        while len(new_colors) < len(original_colors):
            new_colors.append(original_colors[len(new_colors)])
        
        return {
            "color_palette": {
                "original_colors": original_colors,
                "new_colors": new_colors[:len(original_colors)]  # Trim excess colors
            },
            "transformation_notes": transformation_notes or "Color transformation complete"
        }

    def _verify_transformations(self, transformed_data: Dict, original_text_count: int, original_color_count: int) -> None:
        """Verify and print transformation results"""
        text_count = len(transformed_data['text_transformations'])
        unchanged_count = sum(
            1 for item in transformed_data['text_transformations']
            if item['original'] == item['transformed']
        )
        new_color_count = len(transformed_data['color_palette']['new_colors'])
        
        print(f"\nTransformation Results:")
        print(f"- Original texts: {original_text_count}")
        print(f"- Transformed texts: {text_count}")
        print(f"- Modified texts: {text_count - unchanged_count}")
        print(f"- Original colors: {original_color_count}")
        print(f"- New colors: {new_color_count}")
        
        # Add color transformation verification
        unchanged_colors = sum(
            1 for orig, new in zip(
                transformed_data['color_palette']['original_colors'],
                transformed_data['color_palette']['new_colors']
            )
            if orig.lower() == new.lower()
        )
        print(f"- Modified colors: {original_color_count - unchanged_colors}")
        
        if unchanged_count == text_count:
            print("Warning: No texts were modified in transformation")
        if unchanged_colors == original_color_count:
            print("Warning: No colors were modified in transformation")

