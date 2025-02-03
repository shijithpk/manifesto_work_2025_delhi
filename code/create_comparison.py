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

def clean_file(input_file, output_file):
	with open(input_file, 'r') as f:
		lines = f.readlines()

	filtered_lines = [line for line in lines if line.strip() not in ['```json', '```']]

	with open(output_file, 'w') as f:
		f.writelines(filtered_lines)


def create_cache(year, state, party, extension):

	system_instruction = f'You are an expert on the Indian state of {state}, and the issues faced by its people.'

	uploads = []

	file_path = f'manifestos/{year}_{state}_{party}.{extension}'
	file_upload = client.files.upload(path=file_path)
	uploads.append(file_upload)

	multiple_files = [
			types.Part.from_uri(f.uri, mime_type=f.mime_type) for f in uploads
		]
	
	cache_prompt = f"""
		The file attached is the party manifesto of {party_dict[party]} for the {year} {state_dict[state]} assembly elections.

		Go through the manifesto and understand what the party is promising or pledging to the voters of {state_dict[state]}.
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
				ttl="3600s", # 1 hour is default , just making ttl explicit here
			),
		)

	return cached_content


def create_chat(cache):
	chat = client.chats.create(
						model=cache.model,		
						config=types.GenerateContentConfig(
							cached_content=cache.name,
							temperature=0,
							safety_settings=safety_settings,
						),
					)
	
	return chat


def get_party_promises(year, state, party, extension):

	party_cache = create_cache(year, state, party, extension)

	party_chat = create_chat(party_cache)

	response = party_chat.send_message(f"""
					This is a numbered list of issues that are most important to the voters of Delhi:
						1. "Pollution"
						2. "Inflation & Cost of Living"
						3. "Employment & Job Creation"
						4. "Education"
						5. "Healthcare"
						6. "Public Transport & Traffic management"
						7. "Water Supply"
						8. "Electricity"
						9. "Waste management & Sanitation"
						10. "Women's Safety & Empowerment"
						11. "Business, Trade & Industry"
						12. "Corruption"
						13. "Housing"
						14. "Urban Infrastructure Development"

					For each of the issues in the list, I want you to find the five most relevant promises/pledges/proposals made by {party_dict[party]} in its manifesto. 

					Return only a json as output.

					The structure of the json will look like this:```
						{{
							"Pollution": {{
								{party.upper()}: 
									['promise_pledge_proposal_1_text', 'promise_pledge_proposal_2_text', 'promise_pledge_proposal_3_text', 
									'promise_pledge_proposal_4_text', 
									'promise_pledge_proposal_5_text', 
									],
							}},
							"Inflation & Cost of Living": {{
								{party.upper()}: 
									['promise_pledge_proposal_1_text', 'promise_pledge_proposal_2_text', 'promise_pledge_proposal_3_text', 
									'promise_pledge_proposal_4_text', 
									'promise_pledge_proposal_5_text', 
									],
							}},
							...					
						}}
					```
					The promises/pledges/proposals should be concrete and specific measures, not vague or generic points.
					
					If a party does not talk about a key issue in its manifesto, leave the field for that party blank.

					If there are less than five promises/pledges/proposals for a key issue, mention as many possible.

					The text for each pledge/promise/proposal can be upto 50 words long.

					Do not combine two promises/pledges/proposals into one. Keep them separate.

					Also start the promise/pledge/proposal with a verb and write it in active voice with an implied subject. To provide two examples:
						1) "Door step delivery of Ration will be introduced." should be written as "Introduce door step delivery of ration" 
						2) "10 new colleges and 200 new schools will be started in Delhi." should be written as "Start 10 new colleges and 200 new schools in Delhi"

				""")

	return response.text


def create_chat_all_party(state):

	system_instruction = f'You are an expert on the Indian state of {state}, and the issues faced by its people.'

	all_party_chat = client.chats.create(
							model=MODEL_ID,
							config=types.GenerateContentConfig(
								system_instruction=system_instruction,
								temperature=0,
								safety_settings=safety_settings,
							),
						)

	return all_party_chat

all_party_chat = create_chat_all_party('Delhi')

def get_merged_json_prompt(party_list):
	# Get promises for each party
	party_promises = {}
	for party in party_list:
		party_promises[party] = get_party_promises('2025', 'dl', party, 'md')
	
	# Build the party lists section dynamically
	party_lists_text = "\n".join([f"This is the list for {party_dict[party]}: {party_promises[party]}" for party in party_list])
	
	# Build the json structure example dynamically
	json_structure_parts = []
	for issue in ["Pollution", "Inflation & Cost of Living"]:
		party_sections = []
		for party in party_list:
			party_sections.append(f"'{party.upper()}': ['promise_pledge_proposal_1_text', 'promise_pledge_proposal_2_text', 'promise_pledge_proposal_3_text', 'promise_pledge_proposal_4_text', 'promise_pledge_proposal_5_text']")
		json_structure_parts.append(f'"{issue}": {{\n' + ',\n'.join(party_sections) + '\n}}')
	
	json_structure = "{\n" + ",\n".join(json_structure_parts) + "\n...}"
	
	merged_json_prompt = f"""
		I have lists of promises/pledges/proposals made by {', '.join([party_dict[party] for party in party_list])} on several key issues.
										   
		The lists are in json format.
										   
		{party_lists_text}

		Combine the lists from the {'three' if len(party_list) == 3 else 'two'} parties. 
		
		Return the combined output as json. 

		The structure of the json will look like this:```
			{json_structure}
			```

		Do not shorten the text of any promise/pledge/proposal. 
		Do not add any text of your own.
	"""
	
	return merged_json_prompt

party_list = ['aap', 'bjp', 'cong']
merged_json_prompt = get_merged_json_prompt(party_list)
merged_json_response = all_party_chat.send_message(merged_json_prompt)

output_filename = 'manifestos/comparison_2025_raw.json'

with open(output_filename, 'w', encoding='utf-8') as f:
	f.write(merged_json_response.text)

cleaned_filename = 'manifestos/comparison_2025.json'
clean_file(output_filename, cleaned_filename)