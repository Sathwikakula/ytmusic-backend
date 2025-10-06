from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import requests
import os

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable frontend to access API

# Initialize YTMusic
ytmusic = YTMusic()  # Limited access, no login

# -------------------- Search Endpoint --------------------
@app.route('/search')
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Query parameter 'q' is missing"}), 400

    try:
        results = ytmusic.search(query, filter="songs", limit=15)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- Stream Endpoint --------------------
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

        range_header = request.headers.get('Range', None)
        headers = {'User-Agent': request.user_agent.string}
        if range_header:
            headers['Range'] = range_header

        req = requests.get(audio_url, stream=True, headers=headers)

        def generate():
            for chunk in req.iter_content(chunk_size=4096):
                yield chunk

        resp = Response(generate(), mimetype=req.headers.get('content-type'))
        if range_header:
            resp.status_code = 206
            if 'Content-Range' in req.headers:
                resp.headers['Content-Range'] = req.headers['Content-Range']
        resp.headers['Content-Length'] = req.headers.get('Content-Length', '0')
        resp.headers['Accept-Ranges'] = 'bytes'

        return resp

    except Exception as e:
        print(f"Server error: {e}")
        return "Error fetching stream", 500

# -------------------- Main --------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render sets PORT
    app.run(host="0.0.0.0", port=port, debug=True)
