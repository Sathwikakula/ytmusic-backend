from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)

ytmusic = YTMusic()

@app.route('/search')
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Query parameter 'q' is missing"}), 400
    
    try:
        search_results = ytmusic.search(query, filter="songs", limit=15)
        return jsonify(search_results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# UPGRADED Endpoint to stream audio and handle seeking (Range Requests)
@app.route('/stream')
def stream():
    video_id = request.args.get('videoId')
    if not video_id:
        return "videoId parameter is missing", 400

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            audio_url = info['url']
        
        # Get the range header from the client's request
        range_header = request.headers.get('Range', None)
        
        # Prepare headers for the request to Google's servers
        headers = {'User-Agent': request.user_agent.string}
        if range_header:
            headers['Range'] = range_header

        # Make the request to the real audio URL
        req = requests.get(audio_url, stream=True, headers=headers)

        # Create the response to send back to the client
        # Use a generator to stream the content chunk by chunk
        def generate():
            for chunk in req.iter_content(chunk_size=4096):
                yield chunk

        # Build the Flask response with appropriate headers
        resp = Response(generate(), mimetype=req.headers['content-type'])
        
        # If it was a range request, set the status code to 206 Partial Content
        if range_header:
            resp.status_code = 206
            resp.headers.add('Content-Range', req.headers.get('Content-Range'))
        
        resp.headers.add('Content-Length', req.headers.get('Content-Length'))
        resp.headers.add('Accept-Ranges', 'bytes')

        return resp
        
    except Exception as e:
        print(f"Server error: {e}")
        return "Error fetching stream", 500

if __name__ == '__main__':
    app.run(debug=True)