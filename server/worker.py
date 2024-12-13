import os
import base64
import hashlib
import io
import json
import time
import re
import logging
from dotenv import load_dotenv

# Image and AI Processing Libraries
from PIL import Image, ImageDraw, ImageFont
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
import openai
from openai import OpenAI

# Google Cloud and Data Storage Libraries
from google.oauth2 import service_account
from google.cloud import pubsub_v1
from google.cloud import storage
import redis
from pymongo.mongo_client import MongoClient

# Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()

# MongoDB Connection
try:
    uri = "mongodb+srv://text2comicuser:text2comic@text2comic.w2ba2.mongodb.net/?retryWrites=true&w=majority&appName=text2comic"
    mc = MongoClient(uri)
    db = mc['text2comic']
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Set Environment Variables for AI Services
os.environ['STABILITY_HOST'] = 'grpc.stability.ai:443'
os.environ['STABILITY_KEY'] = os.getenv('STABLE_DIFFUSION_API')
os.environ['OPENAI_API'] = os.getenv('OPEN_AI_API')

# Redis Client Configuration
try:
    redis_client = redis.Redis(
        host='redis-12295.c309.us-east-2-1.ec2.redns.redis-cloud.com',
        port=12295,
        db=0,
        password='wLqNJWxFSnMpARKxCQYn1LKyVymLWMlK'
    )
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise

# Google Cloud Credentials
try:
    credentials = service_account.Credentials.from_service_account_file('service-credentials.json')
    g_client = storage.Client(credentials=credentials)
    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
    logger.info("Google Cloud credentials loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Google Cloud credentials: {e}")
    raise

# Pub/Sub Configuration
PROJECT_ID = 'dcsclab05'  
SUBSCRIPTION_ID = 'text2comic-requests-subscription'
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

def hash_prompt(prompt):
    """Generate a unique hash for the prompt."""
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

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
                Create a comic-style image where {person} says, \"{speech}\".
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
        for resp in answer:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    raise Exception("Your request activated the API's safety filters and could not be processed. Please modify the prompt and try again")
                if artifact.type == generation.ARTIFACT_IMAGE:
                    img_binary = io.BytesIO(artifact.binary)
                    img = Image.open(img_binary)
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    return img_base64
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

def add_text_to_image(base64_image, text_from_prompt):
    try:
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
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
        buffered = io.BytesIO()
        result.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_base64
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

def stitch_images(base64_images):
    try:
        # Convert all base64 images to Image objects
        images = [Image.open(io.BytesIO(base64.b64decode(img))) for img in base64_images]
        
        # Ensure that no more than 4 images are provided
        if len(images) > 4:
            raise ValueError("No more than 4 images should be provided.")

        # Resize all images to the size of the largest image (if they are not already the same size)
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        
        # Resize all images to have the same width and height (max dimensions)
        images = [img.resize((max_width, max_height)) for img in images]

        # Calculate the total width and height of the stitched image (2x2 grid layout)
        total_width = max_width * 2  # Two images per row
        total_height = max_height * 2  # Two images per column
        
        # Create a blank canvas for the stitched image
        stitched_image = Image.new('RGB', (total_width, total_height), (255, 255, 255))

        # Place each image in the correct grid position
        for index, img in enumerate(images):
            row = index // 2  # Determines row position (0 or 1)
            col = index % 2  # Determines column position (0 or 1)
            
            x_offset = col * max_width
            y_offset = row * max_height
            
            stitched_image.paste(img, (x_offset, y_offset))

        return stitched_image

    except Exception as e:
        raise Exception(f"Error occurred during image stitching: {e}")



def upload_to_gcp(image, hashed_prompt):
    try:
        bucket_name = 'text2comic'  # Replace with your actual GCP bucket name
        bucket = g_client.get_bucket(bucket_name)
        
        # Create a unique file name based on hashed prompt
        
        file_name = f"comic_image_{hashed_prompt}.png"
        
        # Create a blob object and upload the image
        blob = bucket.blob(file_name)
        
        # Save the image in the GCP bucket
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        buffered.seek(0)
        blob.upload_from_file(buffered, content_type='image/png')

        # Generate the public URL for the uploaded image
        image_url = f"https://storage.googleapis.com/{bucket_name}/{file_name}"
        print(f"Image successfully uploaded to: {image_url}")
        return image_url
    except Exception as e:
        raise Exception(f"Error occurred while uploading image to GCP: {e}")

def convert_image_to_base64(image):
    """Convert an image to base64 encoding."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Function to download the image from GCP
def download_image_from_gcp(image_url):

    try:
        # Extract the file name from the URL
        file_name = image_url.split('/')[-1]

        # Download the image from GCP
        bucket_name = 'text2comic'  # Replace with your actual GCP bucket name
        bucket = g_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        # Download the image as a BytesIO object
        image_data = blob.download_as_bytes()
        image = Image.open(io.BytesIO(image_data))
        
        return image
    except Exception as e:
        raise Exception(f"Error downloading image from GCP: {e}")

def get_from_cache(hashed_prompt):
    """Check Redis cache for an existing image URL using the hashed prompt."""
    return redis_client.get(hashed_prompt)


def set_in_cache(hashed_prompt, image_url):
    """Store the image URL in Redis cache with the hashed prompt."""
    redis_client.set(hashed_prompt, image_url)  # Cache for 1 hour

def store_comic_response(message_id, comic_base64):
    """Store the comic response in Redis with the message ID as the key."""
    redis_client.set(message_id, comic_base64)

def publish_comic_request(user_input, customizations, cfg, step, key):
    """Publish a comic generation request to Pub/Sub."""
    try:
        # Prepare the message data
        message_data = {
            'userInput': user_input,
            'customizations': customizations,
            'cfgValue': cfg,
            'steps': step,
            'key': key,
            'timestamp': time.time()
        }
        
        # Convert to JSON bytes
        data = json.dumps(message_data).encode('utf-8')
        
        # Publish to Pub/Sub topic
        future = publisher.publish(topic_path, data)
        message_id = future.result()
        
        return message_id
    except Exception as e:
        raise Exception(f"Error publishing to Pub/Sub: {e}")

def generate_comic_from_request(message_data):
    """Main function to generate comic from request data"""
    try:
        # Extract request details
        user_input = message_data['userInput']
        customizations = message_data['customizations']
        cfg = message_data['cfgValue']
        step = message_data['steps']
        key = message_data['key']
        
        # Prepare prompt for conversation generation
        prompt = ("Convert the following boring text into a comic style conversation "
                  "of no more than four sentences or total dialogues between characters "
                  "while retaining information. Try to keep the characters as people "
                  "from the story. Keep a line break after each dialogue and don't "
                  "include words like Scene 1, narration context and scenes etc. "
                  "Keep the name of the character and not character number: \n\n\n")
        input_text = prompt + user_input

        # Hash the original prompt for caching
        hashed_prompt = hash_prompt(user_input)

        # Check cache first
        cached_url = redis_client.get(hashed_prompt)
        if cached_url:
            logger.info(f"Cache hit for prompt: {hashed_prompt}")
            image = download_image_from_gcp(cached_url.decode('utf-8'))
            base64_image = convert_image_to_base64(image)
            return base64_image

        # Generate conversation
        response = convert_text_to_conversation(input_text)
        
        # Generate comic panels
        serialized_images = []
        for i in range(min(len(response[0]), 4)):
            base64_image = stable_diff(
                response[1][i], response[0][i], i, customizations, cfg, step, key)
            text = add_line_breaks(response[0][i])
            final_image = add_text_to_image(base64_image, text)
            serialized_images.append(final_image)

        # Stitch images
        stitched_image = stitch_images(serialized_images)
        
        # Upload to GCP
        image_url = upload_to_gcp(stitched_image, hashed_prompt)
        
        # Cache the image URL
        redis_client.set(hashed_prompt, image_url)

        # Save metadata
        metadata = {
            "time": time.time(),
            "prompt": user_input,
            "image_url": image_url
        }
        db.metadata.insert_one(metadata)

        # Convert stitched image to base64
        buffered = io.BytesIO()
        stitched_image.save(buffered, format="PNG")
        stitched_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return stitched_base64

    except Exception as e:
        logger.error(f"Comic generation failed: {e}")
        

def process_comic_request(message):
    """Process a single comic generation request"""
    try:
        # Decode message data
        message_data = json.loads(message.data.decode('utf-8'))
        message_id = message.message_id

        logger.info(f"Processing comic request: {message_id}")

        # Generate comic
        comic_base64 = generate_comic_from_request(message_data)

        # Store comic response in Redis
        redis_client.set(str(message_id), comic_base64)
        logger.info(f"Comic stored for message ID: {message_id}")

        # Acknowledge message
        message.ack()
        return message_id

    except Exception as e:
        logger.error(f"Error processing comic request: {e}")
        # Negative acknowledgement to retry or move to dead-letter queue
        message.nack()
        return None

def start_subscriber():
    """Start the Pub/Sub subscriber to process requests"""
    def callback(message):
        try:
            logger.info(f"Received message: {message.message_id}")
            result = process_comic_request(message)
            if result:
                logger.info(f"Comic generated successfully for message: {result}")
            else:
                logger.warning(f"Failed to process message: {message.message_id}")
        except Exception as e:
            logger.error(f"Error in subscriber callback: {e}")

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logger.info(f"Listening for messages on {subscription_path}")
    return streaming_pull_future

# Include all the previously defined helper methods like stable_diff(), 
# convert_text_to_conversation(), add_text_to_image(), etc.
# (These methods would remain the same as in the previous implementation)

def main():
    """Main entry point for the worker"""
    try:
        logger.info("Comic Generation Worker Starting...")
        
        # Start the Pub/Sub subscriber
        subscriber_future = start_subscriber()
        
        # Keep the script running
        subscriber_future.result(timeout=None)
    except Exception as e:
        logger.error(f"Fatal error in worker: {e}")
    finally:
        logger.info("Worker shutting down...")

if __name__ == "__main__":
    main()