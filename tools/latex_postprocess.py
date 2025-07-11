#!/usr/bin/env python3
"""
LaTeX Post-Processing Script
This script fixes common issues that may occur during LaTeX translation.
"""

import re
import argparse
from collections import Counter
from typing import List, Tuple

def find_missing_environments(text: str) -> List[Tuple[str, str]]:
    """
    Find missing \\begin or \\end commands for environments.
    Returns list of (environment_name, missing_type) tuples.
    """
    begin_matches = re.findall(r'\\begin\{([^}]+)\}', text)
    end_matches = re.findall(r'\\end\{([^}]+)\}', text)
    
    begin_counter = Counter(begin_matches)
    end_counter = Counter(end_matches)
    
    missing = []
    
    for env in set(begin_matches + end_matches):
        begin_count = begin_counter.get(env, 0)
        end_count = end_counter.get(env, 0)
        
        if begin_count > end_count:
            for _ in range(begin_count - end_count):
                missing.append((env, 'end'))
        elif end_count > begin_count:
            for _ in range(end_count - begin_count):
                missing.append((env, 'begin'))
    
    return missing

def fix_environment_balance(text: str) -> str:
    """
    Attempt to fix unbalanced LaTeX environments.
    """
    missing = find_missing_environments(text)
    
    if not missing:
        return text
    
    print(f"Found {len(missing)} unbalanced environments:")
    for env, missing_type in missing:
        print(f"  Missing \\{missing_type}{{{env}}}")
    
    fixed_text = text
    
    # Strategy: Look for patterns and try to fix them intelligently
    for env, missing_type in missing:
        if missing_type == 'end':
            # Find the last \begin{env} and add \end{env} after its content
            begin_pattern = rf'\\begin\{{{re.escape(env)}\}}'
            matches = list(re.finditer(begin_pattern, fixed_text))
            
            if matches:
                # Find the last occurrence
                last_match = matches[-1]
                insert_pos = last_match.end()
                
                # Try to find a good place to insert the \end command
                # Look for the end of the paragraph or section
                remaining_text = fixed_text[insert_pos:]
                
                # Find next paragraph break, section, or end of document
                next_break = None
                for pattern in [r'\n\n', r'\\chapter', r'\\section', r'\\subsection', r'\\end\{document\}']:
                    match = re.search(pattern, remaining_text)
                    if match:
                        if next_break is None or match.start() < next_break:
                            next_break = match.start()
                
                if next_break is not None:
                    insert_pos += next_break
                else:
                    # Insert before \end{document} if found, otherwise at end
                    end_doc_match = re.search(r'\\end\{document\}', fixed_text)
                    if end_doc_match:
                        insert_pos = end_doc_match.start()
                    else:
                        insert_pos = len(fixed_text)
                
                fixed_text = (fixed_text[:insert_pos] + 
                            f"\n\\end{{{env}}}\n" + 
                            fixed_text[insert_pos:])
                print(f"Added \\end{{{env}}} at position {insert_pos}")
        
        elif missing_type == 'begin':
            # Find the first \end{env} and add \begin{env} before it
            end_pattern = rf'\\end\{{{re.escape(env)}\}}'
            match = re.search(end_pattern, fixed_text)
            
            if match:
                # Look backwards to find a good place for \begin
                before_text = fixed_text[:match.start()]
                
                # Try to find the start of the relevant section
                insert_pos = 0
                for pattern in [r'\\chapter', r'\\section', r'\\subsection']:
                    matches = list(re.finditer(pattern, before_text))
                    if matches:
                        last_section = matches[-1]
                        if last_section.end() > insert_pos:
                            insert_pos = last_section.end()
                
                # Insert after the line break following the section
                next_newline = before_text.find('\n', insert_pos)
                if next_newline != -1:
                    insert_pos = next_newline + 1
                
                fixed_text = (fixed_text[:insert_pos] + 
                            f"\\begin{{{env}}}\n" + 
                            fixed_text[insert_pos:])
                print(f"Added \\begin{{{env}}} at position {insert_pos}")
    
    return fixed_text

def fix_common_latex_issues(text: str) -> str:
    """
    Fix common LaTeX translation issues.
    """
    # Fix spacing around LaTeX commands
    text = re.sub(r'\\([a-zA-Z]+)\s*\{', r'\\\1{', text)
    
    # Fix spacing in references
    text = re.sub(r'\\(ref|cite|label)\s*\{', r'\\\1{', text)
    
    # Ensure proper spacing after commands
    text = re.sub(r'\\([a-zA-Z]+)\}([a-zA-Z])', r'\\\1} \2', text)
    
    # Fix double backslashes (line breaks)
    text = re.sub(r'\\\\\s*\\\\', r'\\\\', text)
    
    # Fix itemize/enumerate items
    text = re.sub(r'\\item\s+([A-Z])', r'\\item \1', text)
    
    return text

def validate_and_fix_latex(input_file: str, output_file: str = None) -> bool:
    """
    Validate and fix a LaTeX file.
    """
    if output_file is None:
        output_file = input_file.replace('.tex', '_fixed.tex')
    
    print(f"Processing: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"Original file size: {len(text)} characters")
    
    # Check for missing environments
    missing = find_missing_environments(text)
    
    if missing:
        print(f"Found {len(missing)} environment issues. Attempting to fix...")
        fixed_text = fix_environment_balance(text)
        fixed_text = fix_common_latex_issues(fixed_text)
        
        # Verify the fix
        new_missing = find_missing_environments(fixed_text)
        
        if len(new_missing) < len(missing):
            print(f"Reduced environment issues from {len(missing)} to {len(new_missing)}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(fixed_text)
            
            print(f"Fixed file saved as: {output_file}")
            return True
        else:
            print("Could not automatically fix all issues. Manual review required.")
            return False
    else:
        print("No environment issues found.")
        
        # Still apply common fixes
        fixed_text = fix_common_latex_issues(text)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(fixed_text)
        
        print(f"Applied common fixes and saved as: {output_file}")
        return True

def main():
    parser = argparse.ArgumentParser(description='Post-process translated LaTeX files')
    parser.add_argument('input_file', help='Input LaTeX file to process')
    parser.add_argument('-o', '--output', help='Output file (default: input_fixed.tex)')
    
    args = parser.parse_args()
    
    success = validate_and_fix_latex(args.input_file, args.output)
    
    if success:
        print("Post-processing completed successfully.")
    else:
        print("Post-processing completed with warnings. Manual review recommended.")

if __name__ == "__main__":
    main()
