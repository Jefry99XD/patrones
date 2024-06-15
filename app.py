from flask import Flask, request, render_template, send_from_directory, jsonify
import os
import subprocess
import re
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'runs/detect'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Description:
    # This endpoint renders the main index page of the application.
    
    # Input:
    # - Method: GET
    
    # Output:
    # - Success: Returns the rendered `index.html` template.
    
    # Constraints:
    # - None
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Description:
    # This endpoint handles file upload and processes the file using a YOLO model.
    
    # Input:
    # - Method: POST
    # - Form Data: 'file' (file to be uploaded)
    
    # Output:
    # - Success: Returns JSON with the path to the result image.
    #   Example: {'result_path': 'path/to/result_image.jpg'}
    # - Error: Returns JSON with an error message and a corresponding HTTP status code.
    #   Example: {'error': 'No file part'} with status code 400
    
    # Constraints:
    # - 'file' must be present in the request files.
    # - 'file' must have a filename.
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            command = f"python detect.py --weights runs/train/final/weights/best.pt --source {file_path}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            if result.stderr:
                output_lines = result.stderr.split('\n')
                result_folder_line = next((line for line in output_lines if "Results saved to" in line), None)
                if result_folder_line:
                    result_folder_line_cleaned = re.sub(r'\x1b\[[0-9;]*m', '', result_folder_line)

                    result_folder_path = result_folder_line_cleaned.split("Results saved to ")[1].strip()
                    result_folder_name = os.path.basename(result_folder_path)
                    result_image_path = os.path.join(result_folder_path, filename)

                    return jsonify({'result_path': result_image_path.replace("\\", "/")}), 200
                else:
                    return jsonify({'error': 'Result folder not found in YOLO output'}), 500

            output_lines = result.stdout.split('\n')
            result_folder_line = next((line for line in output_lines if "Results saved to" in line), None)
            if result_folder_line:
                result_folder_line_cleaned = re.sub(r'\x1b\[[0-9;]*m', '', result_folder_line)

                result_folder_path = result_folder_line_cleaned.split("Results saved to ")[1].strip()
                result_folder_name = os.path.basename(result_folder_path)
                result_image_path = os.path.join(result_folder_path, filename)

                return jsonify({'result_path': result_image_path.replace("\\", "/")}), 200
            else:
                return jsonify({'error': 'Result folder not found in YOLO output'}), 500
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/result/<path:filename>')
def result_file(filename):
    # Description:
    # This endpoint serves the processed result file.
    
    # Input:
    # - Method: GET
    # - URL Parameter: 'filename' (path to the result file)
    
    # Output:
    # - Success: Returns the requested file.
    
    # Constraints:
    # - The 'filename' parameter must be a valid path to an existing file.
    
    directory = os.path.dirname(filename)
    file = os.path.basename(filename)
    
    # Determine file extension to check if it's a video or image
    file_extension = os.path.splitext(file)[1].lower()
    
    # Send the file using Flask's send_from_directory
    # If the file is a video (.mp4), copy it to "static/videos" and rename it to "final.mp4"
    if os.path.isfile(os.path.join(directory, file)):
        if file_extension == '.mp4':
            # Ensure the destination directory exists
            videos_directory = os.path.join(os.getcwd(), 'static')
            if not os.path.exists(videos_directory):
                os.makedirs(videos_directory)
            
            # Construct new file path in videos directory with the name 'final.mp4'
            new_file_path = os.path.join(videos_directory, 'final.mp4')
            
            # Copy the file
            shutil.copyfile(os.path.join(directory, file), new_file_path)
            
            # Return the 'final.mp4' file using Flask's send_from_directory
            return send_from_directory(videos_directory, 'final.mp4')
        
        # For non-video files, return the requested file using Flask's send_from_directory
        return send_from_directory(directory, file)
    
    else:
        # Handle case where file does not exist
        return "File not found", 404

if __name__ == '__main__':
    # Description:
    # This block checks if the script is being run directly (not imported as a module).
    # If true, it runs the Flask development server.
    
    # Input:
    # - None (this is the entry point of the script)
    
    # Output:
    # - Starts the Flask application in debug mode, allowing for real-time code changes.
    
    # Constraints:
    # - This should only be used in a development environment. 
    #   For production, a production-ready server like Gunicorn should be used.
    app.run(debug=True)