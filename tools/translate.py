# Description: This script uses the OpenAI API to translate text from one
#     language to another.
#     The script takes the path to an input file, the path to an output file,
#     the source language, and the target language as input.
#     To use it, you need to have an OpenAI API key and install the OpenAI
#     Python package.
#     You can install the OpenAI Python package using the following command:
#     ```bash
#     pip install openai
#     ```
#     You also need to create a .env file in the root directory of the project
#     and add your OpenAI API key to it as follows:
#     ```env
#     OPENAI_API_KEY=your-api-key
#     ```
#     You can get your OpenAI API key from the OpenAI website.
# Author: Michaël Launay
# Date: 2024-08-03

import openai
import os
from dotenv import load_dotenv
import argparse
from typing import Tuple

MAX_TOKENS = 12000
MAX_CONTENT_SIZE = 9999
GPT_MODEL = "gpt-4o-mini"

# Load environment variables from the .env file
load_dotenv()

# Get the API key from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')

# Create an instance of the OpenAI API
openai_client = openai.OpenAI()

def truncate_text_at_last_empty_line(text:str, max_size:int)->Tuple[str, str]:
    """
    Truncates the given text at the last empty line before the max_size.

    Args:
        text (str): The text to be truncated.
        max_size (int): The maximum size of the text.

    Returns:
        Tuple[str, str]: The truncated text and the rest of the text.
    """
    if len(text) <= max_size:
        return text, None

    truncated_text = text[:max_size]
    
    # Find the last empty line before the limit
    last_empty_line_index = truncated_text.rfind(os.linesep+os.linesep)

    if last_empty_line_index == -1:
        # If no empty line is found, simply truncate at max_size
        return truncated_text, text[max_size:]

    return truncated_text[:last_empty_line_index], text[last_empty_line_index:]

def translate_text(text, source_lang, target_lang, file_name):
    """
    Translates the given text from the source language to the target language.

    Args:
        text (str): The text to be translated.
        source_lang (str): The source language of the text.
        target_lang (str): The target language for the translation.
        file_name (str): The name of the file being translated.

    Returns:
        str: The translated text.

    Raises:
        None

    """
    truncate_text, rest_of_text = truncate_text_at_last_empty_line(text, MAX_CONTENT_SIZE)
    chunks = [truncate_text]
    while rest_of_text:
        chunk, rest_of_text = truncate_text_at_last_empty_line(rest_of_text, MAX_CONTENT_SIZE)
        chunks.append(chunk)
    messages=[
        {
            "role": "system",
            "content": f"You are a translator tasked with translating the content below, which is a piece provided from the {file_name} file from {source_lang} to {target_lang}."\
                "Please provide only the translated text."\
                "Be mindful of the file type to avoid breaking it."\
                "Be careful to preserve the escaped characters for apostrophes or quotation marks when they are present in the strings to be translated."
        }
    ]
    translation = ""
    for chunk in chunks:
        if len(messages) > 1:
            del messages[1]
        messages.append({
            "role": "user",
            "content": chunk.strip()
        })
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
        )
        if response.choices[0].finish_reason != "stop":
            raise Exception(f"Translation failed with reason {response.choices[0].finish_reason} for chunk starts with {chunk[:100]}.")
        if translation:
            translation += os.linesep + os.linesep
        translation += response.choices[0].message.content
    return translation

def translate_file(input_file_path, output_file_path, source_lang, target_lang):
    """
    Translates the contents of the input file from the source language to the target language and saves the translated text in the output file.
    Args:
        input_file_path (str): The path to the input file.
        output_file_path (str): The path to the output file.
        source_lang (str): The source language code.
        target_lang (str): The target language code.
    """
    with open(input_file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    translated_text = translate_text(text, source_lang, target_lang, os.path.basename(input_file_path))
    
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(translated_text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate text files using OpenAI API.')
    parser.add_argument('input_file_path', type=str, help='The full path to the input file.')
    parser.add_argument('output_file_path', type=str, help='The full path to the output file.')
    parser.add_argument('--target_lang', type=str, default='French', help='The target language.')
    parser.add_argument('--source_lang', type=str, default='English', help='The source language.')

    args = parser.parse_args()

    translate_file(args.input_file_path, args.output_file_path, args.source_lang, args.target_lang)
    print(f'Translated {args.input_file_path} to {args.output_file_path} successfully.')
