import discord
import requests
import json
import webbrowser
from oauthlib.oauth2 import WebApplicationClient
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# Temporary workaround for local development to allow insecure HTTP (Do not use in production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

# Load OAuth client credentials from JSON file
with open('C:\\Users\\kristiqn\\Downloads\\client.json') as f:
    credentials = json.load(f)
    CLIENT_ID = credentials['installed']['client_id']
    CLIENT_SECRET = credentials['installed']['client_secret']
    AUTHORIZATION_URL = credentials['installed']['auth_uri']
    TOKEN_URL = credentials['installed']['token_uri']
    REDIRECT_URI = 'http://localhost:8080'
    SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly',
              'https://www.googleapis.com/auth/classroom.coursework.students.readonly']

oauth_client = WebApplicationClient(CLIENT_ID)
access_token = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global access_token
        if self.path.startswith("/?code="):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
            authorization_code = self.path.split("=")[1].split("&")[0]
            print(f"Authorization code received: {authorization_code}")

            token_url, headers, body = oauth_client.prepare_token_request(
                TOKEN_URL, authorization_response=self.path, redirect_url=REDIRECT_URI, code=authorization_code
            )

            token_response = requests.post(token_url, headers=headers, data=body, auth=(CLIENT_ID, CLIENT_SECRET))
            print(f"Token response: {token_response.json()}")

            oauth_client.parse_request_body_response(json.dumps(token_response.json()))
            access_token = token_response.json().get('access_token')
            print(f"Access token received: {access_token}")
        else:
            self.send_response(404)
            self.end_headers()

def get_authorization_code():
    authorization_url = oauth_client.prepare_request_uri(
        AUTHORIZATION_URL, redirect_uri=REDIRECT_URI, scope=SCOPES
    )
    print(f"Authorization URL: {authorization_url}")
    webbrowser.open(authorization_url)
    httpd = HTTPServer(('localhost', 8080), OAuthHandler)
    httpd.handle_request()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # Automatically start the OAuth flow when the bot is ready
    get_authorization_code()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$courses'):
        if access_token:
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.get('https://classroom.googleapis.com/v1/courses', headers=headers)
                response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
                course_names = [course['name'] for course in response.json().get('courses', [])]
                if course_names:
                    await message.channel.send('\n'.join(course_names))
                else:
                    await message.channel.send("No courses found.")
            except requests.exceptions.RequestException as e:
                print("Error fetching courses:", e)
                await message.channel.send("Error fetching courses.")
        else:
            await message.channel.send("Error getting access token.")
            
    if message.content.startswith('$assignments'):
        if access_token:
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                courses_response = requests.get('https://classroom.googleapis.com/v1/courses', headers=headers)
                courses_response.raise_for_status()
                courses = courses_response.json().get('courses', [])
                if not courses:
                    await message.channel.send("No courses found.")
                    return
                
                assignments = []
                for course in courses:
                    course_id = course['id']
                    try:
                        coursework_response = requests.get(
                            f'https://classroom.googleapis.com/v1/courses/{course_id}/courseWork', headers=headers
                        )
                        coursework_response.raise_for_status()
                        coursework = coursework_response.json().get('courseWork', [])
                        for work in coursework:
                            assignments.append(f"{course['name']}: {work['title']}")
                    except requests.exceptions.RequestException as e:
                        print(f"Error fetching coursework for course {course_id}: {e}")
                        await message.channel.send(f"Error fetching coursework for course {course['name']}.")

                if assignments:
                    await message.channel.send('\n'.join(assignments))
                else:
                    await message.channel.send("No assignments found.")
            except requests.exceptions.RequestException as e:
                print("Error fetching assignments:", e)
                await message.channel.send("Error fetching assignments.")
        else:
            await message.channel.send("Error getting access token.")

client.run('MTI0MzMyNjYwMzQ3NjQ2Nzc3Mg.GahIEW.PMngbQ9_dIDHYVz8rMIoBQoi0I2RjK_xroPARg')
