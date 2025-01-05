import base64
import psycopg2
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__)

# 1. Configure your PostgreSQL database connection
#    Replace with your actual database credentials
DB_HOST = 'dpg-cttejurqf0us73erd8s0-a'
DB_NAME = 'database_aicamera'
DB_USER = 'database_aicamera_user'
DB_PASSWORD = 'K3qqkaQzJoSLEhOsMIOhlVYi9ktIaANz'
DB_PORT = 5432

# 2. Connect to the PostgreSQL database
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn


conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    port=DB_PORT
)
command = """CREATE TABLE IF NOT EXISTS generated_images (
            id SERIAL PRIMARY KEY,
            original_image_data BYTEA,
            generated_image_data BYTEA,
            prompt_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
try:
    # read the connection parameters
    cur = conn.cursor()
    # create table one by one
    cur.execute(command)
    # close communication with the PostgreSQL database server
    cur.close()
    # commit the changes
    conn.commit()
except (Exception, psycopg2.DatabaseError) as error:
    print(error)

@app.route('/')
def index():
    """Serve the main index.html or your frontend entry."""
    return send_from_directory('.', 'index.html')  # Adjust path as needed

@app.route('/save_image', methods=['POST'])
def save_image():
    """
    Save both the original camera image and the AI-generated image.
    """
    try:
        original_file = request.files.get('original_image')     # The camera-captured image
        generated_file = request.files.get('generated_image')   # The AI-generated image
        prompt_text = request.form.get('prompt', '')

        if not (original_file and generated_file):
            return jsonify({
                'status': 'error',
                'message': 'Missing files. Need both original_image and generated_image.'
            }), 400

        original_data = original_file.read()
        generated_data = generated_file.read()

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert into DB
        query = """
            INSERT INTO generated_images (original_image_data, generated_image_data, prompt_text)
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        cur.execute(query, (psycopg2.Binary(original_data),
                            psycopg2.Binary(generated_data),
                            prompt_text))
        new_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'status': 'ok', 'id': new_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_images', methods=['GET'])
def get_images():
    """
    Fetch all rows, returning both original and generated images in base64, plus prompt text.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, original_image_data, generated_image_data, prompt_text
            FROM generated_images
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for row in rows:
            row_id = row[0]
            orig_data = row[1]  # bytes or None
            gen_data = row[2]   # bytes or None
            prompt_text = row[3] or ""

            # Base64-encode each blob if present
            orig_b64 = base64.b64encode(orig_data).decode('utf-8') if orig_data else None
            gen_b64 = base64.b64encode(gen_data).decode('utf-8') if gen_data else None

            results.append({
                'id': row_id,
                'original_image_base64': orig_b64,
                'generated_image_base64': gen_b64,
                'prompt_text': prompt_text
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/history.html')
def serve_history():
    return send_from_directory('.', 'history.html')

if __name__ == '__main__':
    # 3. Run the Flask app (default: localhost:5000)
    app.run(host="0.0.0.0", port=10000, debug=True)
