import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import time

env_path = '.env'
load_dotenv(dotenv_path=env_path)
gemini_api_key = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=gemini_api_key)

MODEL_ID = "gemini-1.5-pro-002"

system_instruction = 'You are a specialist in translating Hindi to formal English.'

party_dict = {
		"aap": "Aam Aadmi Party",
		"bjp": "Bharatiya Janata Party",
		"cong": "Indian National Congress"
	}

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
	
def clean_file(input_file, output_file):
	with open(input_file, 'r') as f:
		lines = f.readlines()

	filtered_lines = [line for line in lines if line.strip() not in ['```markdown', '```', '# MARKDOWN OVER']]

	with open(output_file, 'w') as f:
		f.writelines(filtered_lines)


def translate_pdf_content(year, state, party):

	file_path = f'manifestos/{year}_{state}_{party}_hindi.pdf'

	uploads = []
	file_upload = client.files.upload(path=file_path)
	uploads.append(file_upload)

	multiple_files = [
			types.Part.from_uri(f.uri, mime_type=f.mime_type) for f in uploads
		]


	cache_prompt = f"""
			The attached markdown file contains the Hindi text of the {party_dict[party]} manifesto for the {year} {state_dict[state]} assembly elections.

			Translate the text from Hindi to formal English.

			Return the translation in markdown format.

			The markdown should retain the structure of the original markdown file.
		"""

	cached_content = client.caches.create(
		model=MODEL_ID,
		config=types.CreateCachedContentConfig(
				system_instruction=system_instruction,
				contents=[
					cache_prompt,
					types.Content(
						role="user",
						parts=multiple_files,
						)
					],
				ttl="3600s",
			),
		)

	combined_markdown = ""

	initial_chat_msg = """
		Add the string '# MARKDOWN OVER' at the end of the markdown you have created.

		Now I want you to return the markdown.

		Do not return any markdown now, start after i type 'Send a part' in my next message.

		When i type 'Send a part', return as much markdown as you can.

		Return only markdown in your output.

		The next time i type 'Send a part', start from where you left off.

		Keep doing this when i type 'Send a part' till there is no more markdown to return.	
	"""

	repeated_chat_msg = 'Send a part'

	chat = client.chats.create(
		model=cached_content.model,
		config=types.GenerateContentConfig(
			cached_content=cached_content.name,
			temperature=0,
			safety_settings=safety_settings,
		),
	)

	chat.send_message(initial_chat_msg)

	markdown_remaining = True	

	while markdown_remaining:	

		response = chat.send_message(repeated_chat_msg)

		if response.text:
			combined_markdown += response.text + "\n\n"
			if 'MARKDOWN OVER' in response.text:	
				print("No more markdown")
				markdown_remaining = False	
		else:
			print("Erroring out.")
			break
		
		time.sleep(10)

	output_filename = f'manifestos/{year}_{state}_{party}_translated_raw.md'


	write_markdown_file(combined_markdown, output_filename)

	cleaned_filename = f'manifestos/{year}_{state}_{party}_translated.md'
	clean_file(output_filename, cleaned_filename)


translate_pdf_content('2025', 'dl', 'bjp')


# once all pdfs are there, do loop
# for party in ['bjp', 'aap', 'cong']:
# 	translate_pdf_content('2025', 'dl', party)