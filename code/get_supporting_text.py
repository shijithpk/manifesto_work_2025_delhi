import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import time
import json


env_path = '.env'
load_dotenv(dotenv_path=env_path)
gemini_api_key = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=gemini_api_key)

MODEL_ID = "gemini-1.5-pro-002"

party_dict = {
		"aap": "Aam Aadmi Party",
		"bjp": "Bharatiya Janata Party",
		"cong": "Indian National Congress"
	}

party_list = [key.upper() for key in party_dict.keys()]

state_dict = {
		"dl": "Delhi"
	}

safety_settings = [
		types.SafetySetting(
			category="HARM_CATEGORY_HARASSMENT",
			threshold="OFF",
		),
		types.SafetySetting(
			category="HARM_CATEGORY_HATE_SPEECH",
			threshold="OFF",
		),
		types.SafetySetting(
			category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
			threshold="OFF",
		),
		types.SafetySetting(
			category="HARM_CATEGORY_DANGEROUS_CONTENT",
			threshold="OFF",
		),
		types.SafetySetting(
			category="HARM_CATEGORY_CIVIC_INTEGRITY",
			threshold="OFF",
		)
	]


def write_markdown_file(content, filename):
	"""Writes content to a markdown file."""
	try:
		with open(filename, 'w', encoding='utf-8') as f:
			f.write(content)
	except Exception as e:
		print(f"Error writing file: {str(e)}")


def clean_markdown_file(input_file, output_file):
	with open(input_file, 'r') as f:
		lines = f.readlines()

	filtered_lines = [line for line in lines if line.strip() not in ['```markdown', '```', '# MARKDOWN OVER']]

	with open(output_file, 'w') as f:
		f.writelines(filtered_lines)


def create_supporting_text_file(year, state, party_list, extension):

	system_instruction = f'You are an expert on the Indian state of {state}, and the issues faced by its people.'

	with open(f'manifestos/comparison_{year}.json', 'r') as filex:
		comparison_content = json.load(filex)
	
	all_supporting_text = ""
	
	for party in party_list:

		file_path = f'manifestos/{year}_{state}_{party.lower()}.{extension}'

		with open(file_path, 'r') as filey:
			party_manifesto_content = filey.read()

		prompt = f"""
			Below is json content where the primary keys are various political issues. Against each issue, are pledges made by 3 parties in the Indian state of Delhi: AAP, BJP and CONG. The short forms stand for Aam Aadmi Party, Bharatiya Janata Party and Congress respectively.

			json_content: ```{comparison_content}```

			Below is markdown content containing the party manifesto of {party_dict[party.lower()]} for the {year} {state_dict[state]} assembly elections.

			markdown_content: ```{party_manifesto_content}```

			I want you to go through the json_content, and for each issue, extract the list of points against {party}.
			
			For each point, I want you to go through markdown_content, and select the sentence most related to that point.
			
			Then I want you to present the information in markdown in this format: 
				```
				- extracted point
					- most related sentence
				< BLANK LINE >
				```
			If you cannot find a sentence related to a point, write 'No related sentence found' instead under the extracted point.
			
			Do not rewrite the extracted point or most related sentence. Do not add any words to them.			

			Return only markdown as your output. 
		"""

		response = client.models.generate_content(
				model=MODEL_ID,
				contents=prompt,
				config=types.GenerateContentConfig(
					system_instruction=system_instruction,
					temperature=0,
					safety_settings=safety_settings,
				)
			)

		if response.text:
			all_supporting_text += party + "\n"
			all_supporting_text += response.text + "\n\n"
		else:
			print("Warning: No text returned.")

		time.sleep(20)

	write_markdown_file(all_supporting_text, f'manifestos/supporting_text_{year}_raw.md')

	clean_markdown_file(f'manifestos/supporting_text_{year}_raw.md', f'manifestos/supporting_text_{year}.md')


create_supporting_text_file(2025, 'dl', party_list, 'md')