import os
from openai import OpenAI
import json
from typing import Dict, List, Any
from dataclasses import dataclass
import os

@dataclass
class TransformedText:
    page_name: str
    section_name: str
    element_type: str
    label: str
    original_content: str
    transformed_content: str
    widget_id: str
    transformation_notes: str = ""

@dataclass
class TransformedColor:
    page_name: str
    section_name: str
    element_type: str
    variable_name: str
    original_color: str
    transformed_color: str
    widget_id: str
    transformation_notes: str = ""

class EnhancedContentTransformationAgent:
    """Enhanced agent for transforming extracted Elementor content using GPT"""
    
    def __init__(self, api_key: str):
        

    def transform_content(self, 
                         rag_input_path: str, 
                         transformed_output_path: str, 
                         style_description: str) -> None:
        """Transform content based on style description"""
        try:
            # Load extracted content
            with open(rag_input_path, 'r', encoding='utf-8') as f:
                extracted_content = json.load(f)

            transformed_data = {
                'pages': {}
            }

            # Process each page
            for page_slug, page_data in extracted_content['pages'].items():
                print(f"Transforming content for page: {page_data['title']}")
                
                # Transform texts in batches
                transformed_texts = []
                batch_size = 5
                texts = page_data['texts']
                
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_result = self._transform_text_batch(batch_texts, style_description)
                    transformed_texts.extend(batch_result)

                # Transform colors
                transformed_colors = self._transform_colors(
                    page_data['colors'],
                    style_description
                )

                # Store transformed data for the page
                transformed_data['pages'][page_slug] = {
                    'title': page_data['title'],
                    'slug': page_slug,
                    'sections': page_data['sections'],
                    'transformed_texts': transformed_texts,
                    'transformed_colors': transformed_colors
                }

            # Save transformed content
            os.makedirs(os.path.dirname(transformed_output_path), exist_ok=True)
            with open(transformed_output_path, 'w', encoding='utf-8') as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)
            
            print(f"Transformation complete. Results saved to {transformed_output_path}")
            
        except Exception as e:
            print(f"Error in transform_content: {e}")
            raise

    def _transform_text_batch(self, texts: List[Dict], style_description: str) -> List[Dict]:
        """Transform a batch of texts using GPT"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert content creator specializing in e-commerce and marketing content. Your task is to:

1. Generate unique, engaging content for each text while considering:
   - The element's label (heading, paragraph, button, etc.)
   - The section name and context
   - The overall page purpose
   - The specified style requirements

2. Follow these specific guidelines:
   - For headings: Create compelling, SEO-friendly titles
   - For paragraphs: Write detailed, informative content relevant to the section
   - For buttons: Create action-oriented, engaging call-to-action text
   - For product descriptions: Include specific features, benefits, and emotional appeals
   - When encountering "Lorem ipsum": Generate completely new, relevant content based on the context

3. Maintain consistency while ensuring each piece is unique and purposeful
4. Match the original text's approximate length and structure
5. Keep the tone professional and persuasive

Format: Return a JSON array where each object maintains the original structure but with transformed content."""
                },
                {
                    "role": "user",
                    "content": f"""Style Requirements: {style_description}

Context for content generation:
- Page Name: {texts[0]['page_name']}
- label Purpose: {texts[0]['label']}

Original texts to transform:
{json.dumps(texts, indent=2)}

Generate unique, contextual content for each text element while preserving the metadata structure."""
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            
            transformed_texts = []
            
            # Parse the response and create TransformedText objects
            try:
                response_data = json.loads(response.choices[0].message.content)
                for original, transformed in zip(texts, response_data):
                    transformed_text = TransformedText(
                        page_name=original['page_name'],
                        section_name=original['section_name'],
                        element_type=original['element_type'],
                        label=original['label'],
                        original_content=original['content'],
                        transformed_content=transformed['content'],
                        widget_id=original['widget_id'],
                        transformation_notes="Transformed based on style requirements"
                    )
                    transformed_texts.append(vars(transformed_text))
            except json.JSONDecodeError:
                # Fallback parsing for non-JSON responses
                parts = response.choices[0].message.content.split('\n\n')
                for original, part in zip(texts, parts):
                    transformed_content = part.strip()
                    transformed_text = TransformedText(
                        page_name=original['page_name'],
                        section_name=original['section_name'],
                        element_type=original['element_type'],
                        label=original['label'],
                        original_content=original['content'],
                        transformed_content=transformed_content,
                        widget_id=original['widget_id'],
                        transformation_notes="Transformed using fallback parsing"
                    )
                    transformed_texts.append(vars(transformed_text))
            
            return transformed_texts
            
        except Exception as e:
            print(f"Error in text transformation: {e}")
            return [vars(TransformedText(
                page_name=text['page_name'],
                section_name=text['section_name'],
                element_type=text['element_type'],
                label=text['label'],
                original_content=text['content'],
                transformed_content=text['content'],
                widget_id=text['widget_id'],
                transformation_notes=f"Error during transformation: {str(e)}"
            )) for text in texts]

    def _transform_colors(self, colors: List[Dict], style_description: str) -> List[Dict]:
        """Transform colors using GPT"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[{
                    "role": "system",
                    "content": """Generate new color palettes while:
                    1. Maintaining consistent color schemes
                    2. Ensuring sufficient contrast
                    3. Following design principles
                    4. Preserving semantic meaning (e.g., error colors stay red-ish)
                    Format: Return hex colors matching the input structure."""
                },
                {
                    "role": "user",
                    "content": f"""Transform these colors to match: {style_description}

                   
                    Original colors:
                    {json.dumps(colors, indent=2)}

                    Return new colors in the same structure, preserving metadata."""
                }],
                temperature=0.7,
                max_tokens=2048
            )
            
            transformed_colors = []
            
            try:
                response_data = json.loads(response.choices[0].message.content)
                for original, transformed in zip(colors, response_data):
                    transformed_color = TransformedColor(
                        page_name=original['page_name'],
                        section_name=original['section_name'],
                        element_type=original['element_type'],
                        variable_name=original['variable_name'],
                        original_color=original['color_value'],
                        transformed_color=transformed['color_value'],
                        widget_id=original['widget_id'],
                        transformation_notes="Color transformed based on style"
                    )
                    transformed_colors.append(vars(transformed_color))
            except json.JSONDecodeError:
                # Generate new colors algorithmically as fallback
                for color in colors:
                    # Simple color shift as fallback
                    original_hex = color['color_value'].lstrip('#')
                    shifted_hex = f"#{original_hex[2:] + original_hex[:2]}"
                    
                    transformed_color = TransformedColor(
                        page_name=color['page_name'],
                        section_name=color['section_name'],
                        element_type=color['element_type'],
                        variable_name=color['variable_name'],
                        original_color=color['color_value'],
                        transformed_color=shifted_hex,
                        widget_id=color['widget_id'],
                        transformation_notes="Color transformed using fallback method"
                    )
                    transformed_colors.append(vars(transformed_color))
            
            return transformed_colors
            
        except Exception as e:
            print(f"Error in color transformation: {e}")
            return [vars(TransformedColor(
                page_name=color['page_name'],
                section_name=color['section_name'],
                element_type=color['element_type'],
                variable_name=color['variable_name'],
                original_color=color['color_value'],
                transformed_color=color['color_value'],
                widget_id=color['widget_id'],
                transformation_notes=f"Error during transformation: {str(e)}"
            )) for color in colors]

    def _clean_color_value(self, color: str) -> str:
        """Clean and validate color hex values"""
        if not color.startswith('#'):
            color = f'#{color}'
        
        # Ensure 6-digit hex
        if len(color) == 4:  # 3-digit hex
            color = f'#{color[1]*2}{color[2]*2}{color[3]*2}'
            
        return color.upper()
