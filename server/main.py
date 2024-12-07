import os
import base64
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import io
import warnings
from PIL import Image, ImageDraw, ImageFont
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
import openai
import cv2
import json
import re
import textwrap
from openai import OpenAI


load_dotenv()

os.environ['STABILITY_HOST'] = 'grpc.stability.ai:443'
os.environ['STABILITY_KEY'] = os.getenv('STABLE_DIFFUSION_API')
os.environ['OPENAI_API'] = os.getenv('OPEN_AI_API')
os.environ['CONVERT_API_KEY'] = os.getenv('CONVERT_API')

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})

# ==== Helper Functions ====
def convert_text_to_conversation(text):
    try:
        response = request_chat_gpt_api(text)
        speech, person = generate_map_from_text(response)
        return (speech, person)
    except openai.APIError as e:
        raise Exception(f"OpenAI API returned an API Error: {e}")
    except openai.APIConnectionError as e:
        raise Exception(f"Failed to connect to OpenAI API: {e}")
    except openai.RateLimitError as e:
        raise Exception(f"OpenAI API request exceeded rate limit: {e}")

def generate_map_from_text(text):
    try:
        d = {}
        who_spoke = {}
        dialogue = []
        speak = []
        l = text.split("\n")
        for word in l:
            if 'Scene' not in word and 'Act' not in word:
                if ':' in word:
                    dialogue.append((word.split(':')[1]))
                    speak.append((word.split(':')[0]))
        for i in range(len(dialogue)):
            d[i] = dialogue[i]
            who_spoke[i] = speak[i]
        return (d, who_spoke)
    except Exception as e:
        raise Exception(f"Error occurred during map generation: {e}")

def stable_diff(person, speech, name, features, cfg, step, key):
    stability_api = client.StabilityInference(
        key=key,
        verbose=True,
        engine="stable-diffusion-xl-1024-v1-0",
    )
    try:
        answer = stability_api.generate(
            prompt=f"""
                Create a comic-style image where {person} says, "{speech}".
                Capture the expressions of the user from the dialogue.
                Add styles based on the following features {features}
                """,
            seed=992446758,
            steps=int(step),
            cfg_scale=int(cfg),
            width=512,
            height=512,
            samples=1,
            sampler=generation.SAMPLER_K_DPMPP_2M
        )
        folder_path = "./images"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        for resp in answer:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    raise Exception("Your request activated the API's safety filters and could not be processed. Please modify the prompt and try again")
                if artifact.type == generation.ARTIFACT_IMAGE:
                    image_path = os.path.join(folder_path, f"{name}.png")
                    img_binary = io.BytesIO(artifact.binary)
                    img = Image.open(img_binary)
                    img.save(image_path)
                    return image_path
    except Exception as e:
        error_message = str(e)
        balance_err = "Your organization does not have enough balance to request this action"
        details_match = re.search('details = "(.*?)"', error_message)
        if details_match:
            details = details_match.group(1)
            if details.startswith(balance_err):
                raise Exception("Insufficient balance in stable diffusion key. Please top up and try again.")
            error_message = details
        print(error_message)
        raise Exception(error_message)

def add_line_breaks(text):
    try:
        words = text.split()
        new_text = ''
        for i, word in enumerate(words):
            new_text += word
            if (i+1) % 7 == 0:
                new_text += '\n'
            else:
                new_text += ' '
        return new_text
    except AttributeError as e:
        raise Exception(f"Error occurred during line break addition: {e}")

def add_text_to_image(image_path, text_from_prompt, file_number):
    try:
        image = Image.open(image_path)
        right_pad = 0
        left_pad = 0
        top_pad = 50
        bottom_pad = 0
        width, height = image.size
        new_width = width + right_pad + left_pad
        new_height = height + top_pad + bottom_pad
        result = Image.new(image.mode, (new_width, new_height), (255, 255, 255))
        result.paste(image, (left_pad, top_pad))
        font_type = ImageFont.truetype("font/animeace2_reg.ttf", 12)
        draw = ImageDraw.Draw(result)
        draw.text((10, 0), text_from_prompt, fill='black', font=font_type)
        result.save(f"./images/{file_number}.png")
        border_img = cv2.imread(f"./images/{file_number}.png")
        borderoutput = cv2.copyMakeBorder(
            border_img, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[0, 0, 0])
        cv2.imwrite(f"./images/{file_number}.png", borderoutput)
    except Exception as e:
        raise Exception(f"Error occurred during text addition: {e}")

def request_chat_gpt_api(prompt):
    openai.api_key = os.environ['OPENAI_API']
    client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=os.environ['OPENAI_API'],
)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "system",
            "content": "You are a fun yet knowledgeable assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        temperature=0.6,
        max_tokens=150
    )
    return response.choices[0].message.content

# ==== Routes ====
@app.route('/', methods=['GET'])
def test():
    return 'The server is running!'

@app.route('/', methods=['POST'])
def generate_comic_from_text():
    try:
        prompt = "Convert the following boring text into a comic style conversation between characters while retaining information. Try to keep the characters as people from the story. Keep a line break after each dialogue and don't include words like Scene 1, narration context and scenes etc. Keep the name of the character and not character number: \n\n\n"
        user_input = request.get_json()['userInput']
        customisation = request.get_json()['customizations']
        cfg = request.get_json()['cfgValue']
        step = request.get_json()['steps']
        key = request.get_json()['key']
        input = prompt + user_input
        response = convert_text_to_conversation(input)
        generated_images_paths = []
        for i in range(len(response[0])):
            image_path = stable_diff(
                response[1][i], response[0][i], i, customisation, cfg, step, key)
            generated_images_paths.append(image_path)
            text = add_line_breaks(response[0][i])
            add_text_to_image(f"./images/{i}.png", text, i)
        return jsonify({'folderPath': './images'}), 200
    except Exception as e:
        error_message = str(e)
        return json.dumps({'error': error_message}), 500, {'Content-Type': 'application/json'}

if __name__ == "__main__":
    app.run(host='0.0.0.0')
