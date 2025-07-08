# Description: This script uses the OpenAI API to translate LaTeX documents from one
#     language to another with intelligent chunking that preserves LaTeX structure.
#     The script handles large files by splitting them at appropriate LaTeX boundaries.
# Author: Michaël Launay (modified)
# Date: 2025-07-07

import openai
import os
import re
from dotenv import load_dotenv
import argparse
from typing import Tuple, List
import json

MAX_TOKENS = 12000
MAX_CONTENT_SIZE = 9999
GPT_MODEL = "gpt-4o-mini"

# Load environment variables from the .env file
load_dotenv()

# Get the API key from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')

# Create an instance of the OpenAI API
openai_client = openai.OpenAI()

def find_latex_break_points(text: str) -> List[int]:
    """
    Find good break points in LaTeX text for chunking.
    Returns a list of positions where we can safely split the text.
    """
    break_points = []
    
    # Patterns for good break points (in order of preference)
    patterns = [
        r'\\chapter\{[^}]*\}',           # Chapter boundaries
        r'\\section\{[^}]*\}',           # Section boundaries
        r'\\subsection\{[^}]*\}',        # Subsection boundaries
        r'\\subsubsection\{[^}]*\}',     # Subsubsection boundaries
        r'\\begin\{[^}]*\}',             # Environment starts
        r'\\end\{[^}]*\}',               # Environment ends
        r'\n\n+',                        # Multiple newlines (paragraph breaks)
        r'\\item\s',                     # List items
        r'\\\\',                         # Line breaks
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            break_points.append(match.start())
    
    # Sort and remove duplicates
    break_points = sorted(list(set(break_points)))
    return break_points

def smart_truncate_latex(text: str, max_size: int) -> Tuple[str, str]:
    """
    Intelligently truncates LaTeX text at appropriate boundaries.
    """
    if len(text) <= max_size:
        return text, ""
    
    break_points = find_latex_break_points(text)
    
    # Find the best break point before max_size
    best_break = 0
    for point in break_points:
        if point < max_size:
            best_break = point
        else:
            break
    
    # If no good break point found, fall back to simple truncation
    if best_break == 0:
        return text[:max_size], text[max_size:]
    
    return text[:best_break], text[best_break:]

def extract_latex_metadata(text: str) -> dict:
    """
    Extract important LaTeX metadata that should be preserved during translation.
    """
    metadata = {
        'documentclass': None,
        'packages': [],
        'commands': [],
        'environments': []
    }
    
    # Extract documentclass
    doc_match = re.search(r'\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}', text)
    if doc_match:
        metadata['documentclass'] = doc_match.group(0)
    
    # Extract package imports
    package_matches = re.findall(r'\\usepackage(?:\[[^\]]*\])?\{[^}]+\}', text)
    metadata['packages'] = package_matches
    
    # Extract custom commands
    command_matches = re.findall(r'\\newcommand\{[^}]+\}(?:\[[^\]]*\])?\{[^}]*\}', text)
    metadata['commands'] = command_matches
    
    return metadata

def create_latex_translation_prompt(text: str, source_lang: str, target_lang: str, 
                                   metadata: dict = None, context: str = None) -> str:
    """
    Create a specialized prompt for LaTeX translation.
    """
    base_prompt = f"""You are a professional translator specializing in LaTeX document translation from {source_lang} to {target_lang}.

CRITICAL INSTRUCTIONS:
1. Translate ONLY the textual content, NOT LaTeX commands, labels, or structural elements
2. Preserve ALL LaTeX formatting, commands, and structure EXACTLY as they appear
3. Maintain the EXACT same number of \\begin{{}} and \\end{{}} commands
4. Do NOT translate:
   - LaTeX commands (\\chapter, \\section, \\begin, \\end, etc.)
   - Labels and references (\\label{{}}, \\ref{{}}, \\cite{{}})
   - File paths and URLs
   - Mathematical expressions
   - Code blocks
   - Package names and options
   - Environment names (itemize, enumerate, figure, table, etc.)
   - Any text inside curly braces following LaTeX commands
5. DO translate:
   - Chapter/section titles (the text inside \\chapter{{}}, \\section{{}} etc.)
   - Body text and paragraphs
   - Figure captions
   - Table content (but not LaTeX table structure)
   - Comments (preserve the % symbol but translate the comment text)
   - Item text in lists (translate text after \\item)

FORMATTING RULES:
- Keep all spacing, indentation, and line breaks exactly as in the original
- Preserve all special characters and symbols
- Maintain the exact structure of tables, lists, and other environments
- Do not add or remove any LaTeX commands

"""
    
    if metadata:
        base_prompt += f"\nThis document uses documentclass: {metadata.get('documentclass', 'unknown')}\n"
    
    if context:
        base_prompt += f"\nContext from previous chunks: {context}\n"
    
    base_prompt += "\nProvide ONLY the translated LaTeX content with no additional comments or explanations. Ensure every \\begin has its matching \\end."
    
    return base_prompt

def translate_latex_chunk(text: str, source_lang: str, target_lang: str, 
                         metadata: dict = None, context: str = None) -> str:
    """
    Translate a single chunk of LaTeX text.
    """
    system_prompt = create_latex_translation_prompt(text, source_lang, target_lang, metadata, context)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text.strip()}
    ]
    
    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.3  # Lower temperature for more consistent translation
        )
        
        if response.choices[0].finish_reason != "stop":
            raise Exception(f"Translation failed with reason: {response.choices[0].finish_reason}")
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error translating chunk: {e}")
        raise

def translate_latex_text(text: str, source_lang: str, target_lang: str, file_name: str) -> str:
    """
    Translate LaTeX text with intelligent chunking and context preservation.
    """
    # Extract metadata from the document
    metadata = extract_latex_metadata(text)
    
    # Split text into manageable chunks
    chunks = []
    remaining_text = text
    context = ""
    
    while remaining_text:
        chunk, remaining_text = smart_truncate_latex(remaining_text, MAX_CONTENT_SIZE)
        chunks.append(chunk)
    
    print(f"Translating {len(chunks)} chunks for file: {file_name}")
    
    translated_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"Translating chunk {i+1}/{len(chunks)}...")
        
        # For chunks after the first, provide context from the previous chunk
        chunk_context = context if i > 0 else None
        
        translated_chunk = translate_latex_chunk(
            chunk, source_lang, target_lang, metadata, chunk_context
        )
        
        translated_chunks.append(translated_chunk)
        
        # Update context with the last few lines of the current chunk for next iteration
        lines = chunk.split('\n')
        context = '\n'.join(lines[-3:]) if len(lines) > 3 else chunk
    
    # Join all translated chunks
    return '\n'.join(translated_chunks)

def validate_latex_structure(original: str, translated: str) -> bool:
    """
    Enhanced validation to ensure LaTeX structure is preserved.
    """
    # Count important LaTeX elements
    elements_to_check = [
        r'\\begin\{[^}]+\}',
        r'\\end\{[^}]+\}',
        r'\\chapter\{',
        r'\\section\{',
        r'\\subsection\{',
        r'\\subsubsection\{',
        r'\\item\b',
        r'\\includegraphics',
        r'\\cite\{',
        r'\\ref\{',
        r'\\label\{',
    ]
    
    validation_passed = True
    
    for element in elements_to_check:
        orig_count = len(re.findall(element, original))
        trans_count = len(re.findall(element, translated))
        
        if orig_count != trans_count:
            print(f"Warning: Mismatch in {element} count. Original: {orig_count}, Translated: {trans_count}")
            validation_passed = False
    
    # Check for balanced begin/end pairs
    begin_matches = re.findall(r'\\begin\{([^}]+)\}', original)
    end_matches = re.findall(r'\\end\{([^}]+)\}', original)
    
    trans_begin_matches = re.findall(r'\\begin\{([^}]+)\}', translated)
    trans_end_matches = re.findall(r'\\end\{([^}]+)\}', translated)
    
    # Check if environment pairs match
    from collections import Counter
    orig_env_balance = Counter(begin_matches) == Counter(end_matches)
    trans_env_balance = Counter(trans_begin_matches) == Counter(trans_end_matches)
    
    if not orig_env_balance:
        print("Warning: Original document has unbalanced begin/end environments")
        validation_passed = False
    
    if not trans_env_balance:
        print("Warning: Translated document has unbalanced begin/end environments")
        validation_passed = False
        
    # Show specific environment mismatches
    if Counter(begin_matches) != Counter(trans_begin_matches):
        print("Environment type mismatches detected:")
        orig_envs = Counter(begin_matches)
        trans_envs = Counter(trans_begin_matches)
        
        for env in set(orig_envs.keys()) | set(trans_envs.keys()):
            orig_count = orig_envs.get(env, 0)
            trans_count = trans_envs.get(env, 0)
            if orig_count != trans_count:
                print(f"  {env}: Original={orig_count}, Translated={trans_count}")
    
    return validation_passed

def translate_latex_file(input_file_path: str, output_file_path: str, 
                        source_lang: str, target_lang: str):
    """
    Translate a LaTeX file from source language to target language.
    """
    print(f"Reading file: {input_file_path}")
    
    with open(input_file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    print(f"File size: {len(text)} characters")
    
    try:
        translated_text = translate_latex_text(
            text, source_lang, target_lang, os.path.basename(input_file_path)
        )
        
        # Validate structure
        if validate_latex_structure(text, translated_text):
            print("LaTeX structure validation passed")
        else:
            print("Warning: LaTeX structure validation failed")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(translated_text)
        
        print(f"Translation completed successfully: {output_file_path}")
        
    except Exception as e:
        print(f"Error during translation: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate LaTeX files using OpenAI API.')
    parser.add_argument('input_file_path', type=str, help='The full path to the input LaTeX file.')
    parser.add_argument('output_file_path', type=str, help='The full path to the output LaTeX file.')
    parser.add_argument('--target_lang', type=str, default='French', help='The target language.')
    parser.add_argument('--source_lang', type=str, default='English', help='The source language.')
    
    args = parser.parse_args()
    
    if not args.input_file_path.endswith('.tex'):
        print("Warning: Input file doesn't have .tex extension")
    
    translate_latex_file(args.input_file_path, args.output_file_path, 
                        args.source_lang, args.target_lang)
    print(f'Successfully translated {args.input_file_path} to {args.output_file_path}')