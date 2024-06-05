from flask import Flask, request, render_template, send_from_directory, jsonify
import os
import subprocess
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'runs/detect'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
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
    directory = os.path.dirname(filename)
    file = os.path.basename(filename)
    return send_from_directory(directory, file)

if __name__ == '__main__':
    app.run(debug=True)