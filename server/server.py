import os
import json
import base64
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import pubsub_v1
import time
import redis
from pymongo.mongo_client import MongoClient

load_dotenv()

# MongoDB Connection
uri = "mongodb+srv://text2comicuser:text2comic@text2comic.w2ba2.mongodb.net/?retryWrites=true&w=majority&appName=text2comic"
mc = MongoClient(uri)
db = mc['text2comic']

# Flask App Setup
app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})

# Redis Client
redis_client = redis.Redis(
    host='redis-12295.c309.us-east-2-1.ec2.redns.redis-cloud.com',
    port=12295,
    db=0,
    password='wLqNJWxFSnMpARKxCQYn1LKyVymLWMlK'
)

# Google Cloud Credentials and Clients
credentials = service_account.Credentials.from_service_account_file('service-credentials.json')
publisher = pubsub_v1.PublisherClient(credentials=credentials)

# Pub/Sub Configuration
PROJECT_ID = 'dcsclab05'  
TOPIC_ID = 'text2comic-requests'

# Topic full path
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def hash_prompt(prompt):
    """Hash the user input to generate a unique key."""
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

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

@app.route('/', methods=['GET'])
def test():
    return 'The server is running!'

@app.route('/', methods=['POST'])
def generate_comic_from_text():
    try:
        user_input = request.get_json()['userInput']
        customisations = request.get_json()['customizations']
        cfg = request.get_json()['cfgValue']
        step = request.get_json()['steps']
        key = request.get_json()['key']

        # Publish request to Pub/Sub
        message_id = publish_comic_request(user_input, customisations, cfg, step, key)
        
        return jsonify({
            'status': 'Request queued', 
            'message_id': message_id
        }), 202  # Accepted status code
    
    except Exception as e:
        error_message = str(e)
        return json.dumps({'error': error_message}), 500, {'Content-Type': 'application/json'}

@app.route('/check-comic', methods=['GET'])
def check_comic_response():
    message_id = request.args.get('message_id')
    if not message_id:
        return jsonify({'error': 'No message ID provided'}), 400
    
    # Retrieve the comic response from Redis
    comic_response = redis_client.get(message_id)
    
    if comic_response:
        # Convert bytes to string if needed
        return jsonify({
            'status': 'completed',
            'images': comic_response.decode('utf-8')
        })
    else:
        return jsonify({
            'status': 'pending'
        }), 202

if __name__ == "__main__":
    app.run(host='0.0.0.0')
