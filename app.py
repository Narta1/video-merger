import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid
import time
import requests
from video_processor import VideoProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'aac', 'm4a'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload and output directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_extensions):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_size(file):
    """Get file size in bytes"""
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    return size

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and video processing"""
    try:
        # Check if files are present
        if 'image' not in request.files or 'audio' not in request.files:
            flash('Both image and audio files are required', 'error')
            return redirect(url_for('index'))
        
        image_file = request.files['image']
        audio_file = request.files['audio']
        
        # Check if files are selected
        if image_file.filename == '' or audio_file.filename == '':
            flash('Please select both image and audio files', 'error')
            return redirect(url_for('index'))
        
        # Validate file types
        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            flash('Invalid image file type. Allowed: PNG, JPG, JPEG, GIF', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            flash('Invalid audio file type. Allowed: MP3, WAV, AAC, M4A', 'error')
            return redirect(url_for('index'))
        
        # Check file sizes
        if get_file_size(image_file) > MAX_FILE_SIZE:
            flash('Image file too large. Maximum size: 100MB', 'error')
            return redirect(url_for('index'))
        
        if get_file_size(audio_file) > MAX_FILE_SIZE:
            flash('Audio file too large. Maximum size: 100MB', 'error')
            return redirect(url_for('index'))
        
        # Generate unique filenames
        unique_id = str(uuid.uuid4())
        image_filename = f"{unique_id}_{secure_filename(image_file.filename)}"
        audio_filename = f"{unique_id}_{secure_filename(audio_file.filename)}"
        output_filename = f"{unique_id}_video.mp4"
        
        # Save uploaded files
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        image_file.save(image_path)
        audio_file.save(audio_path)
        
        app.logger.info(f"Files saved: {image_path}, {audio_path}")
        
        # Process video
        processor = VideoProcessor()
        success, message = processor.create_video(image_path, audio_path, output_path)
        
        if success:
            # Store output filename in session for download
            from flask import session
            session['output_file'] = output_filename
            flash('Video created successfully! Click download to get your file.', 'success')
            return redirect(url_for('download_page'))
        else:
            flash(f'Error creating video: {message}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        app.logger.error(f"Error in upload_files: {str(e)}")
        flash('An unexpected error occurred during processing', 'error')
        return redirect(url_for('index'))

@app.route('/download_page')
def download_page():
    """Page showing download link"""
    from flask import session
    if 'output_file' not in session:
        flash('No video file available for download', 'error')
        return redirect(url_for('index'))
    
    return render_template('index.html', download_ready=True, filename=session['output_file'])

@app.route('/download/<filename>')
def download_file(filename):
    """Download the generated video file"""
    try:
        from flask import session
        if 'output_file' not in session or session['output_file'] != filename:
            flash('Invalid download request', 'error')
            return redirect(url_for('index'))
        
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            flash('File not found', 'error')
            return redirect(url_for('index'))
        
        # Clean up session
        session.pop('output_file', None)
        
        return send_file(file_path, as_attachment=True, download_name=f"merged_video_{int(time.time())}.mp4")
    
    except Exception as e:
        app.logger.error(f"Error in download_file: {str(e)}")
        flash('Error downloading file', 'error')
        return redirect(url_for('index'))

@app.route('/cleanup')
def cleanup_files():
    """Clean up old files (can be called periodically)"""
    try:
        current_time = time.time()
        cleanup_threshold = 3600  # 1 hour
        
        # Clean upload folder
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename == '.gitkeep':
                continue
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.getctime(file_path) < current_time - cleanup_threshold:
                os.remove(file_path)
                app.logger.info(f"Cleaned up upload file: {filename}")
        
        # Clean output folder
        for filename in os.listdir(app.config['OUTPUT_FOLDER']):
            if filename == '.gitkeep':
                continue
            file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            if os.path.getctime(file_path) < current_time - cleanup_threshold:
                os.remove(file_path)
                app.logger.info(f"Cleaned up output file: {filename}")
        
        return jsonify({'status': 'success', 'message': 'Cleanup completed'})
    
    except Exception as e:
        app.logger.error(f"Error in cleanup: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})






@app.route('/generate_from_urls', methods=['POST'])
def generate_from_urls():
    try:
        image_url = request.form.get('image_url')
        audio_url = request.form.get('audio_url')

        if not image_url or not audio_url:
            flash('Both image and audio URLs are required.', 'error')
            return redirect(url_for('index'))

        def download_from_url(url, folder, allowed_extensions):
            ext = url.split('.')[-1].split('?')[0].lower()
            if ext not in allowed_extensions:
                raise ValueError(f"Invalid file extension: {ext}")
            filename = f"{uuid.uuid4()}.{ext}"
            path = os.path.join(folder, filename)
            response = requests.get(url)
            with open(path, 'wb') as f:
                f.write(response.content)
            return path

        image_path = download_from_url(image_url, app.config['UPLOAD_FOLDER'], ALLOWED_IMAGE_EXTENSIONS)
        audio_path = download_from_url(audio_url, app.config['UPLOAD_FOLDER'], ALLOWED_AUDIO_EXTENSIONS)
        output_filename = f"{uuid.uuid4()}_video.mp4"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        processor = VideoProcessor()
        success, message = processor.create_video(image_path, audio_path, output_path)

        if success:
            from flask import session
            session['output_file'] = output_filename
            flash('Video created from URLs successfully!', 'success')
            return redirect(url_for('download_page'))
        else:
            flash(f'Error creating video: {message}', 'error')
            return redirect(url_for('index'))

    except Exception as e:
        app.logger.error(f"Error in generate_from_urls: {str(e)}")
        flash('An unexpected error occurred during processing.', 'error')
        return redirect(url_for('index'))









if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
