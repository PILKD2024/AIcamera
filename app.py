import base64
import psycopg2
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='icons', static_url_path='/icons')

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
    """Save the original camera image along with optional prompt text."""
    try:
        original_file = request.files.get('original_image')
        prompt_text = request.form.get('prompt', '')

        if not original_file:
            return jsonify({
                'status': 'error',
                'message': 'Missing original_image file.'
            }), 400

        original_data = original_file.read()

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert into DB (generated_image_data left NULL)
        query = """
            INSERT INTO generated_images (original_image_data, prompt_text)
            VALUES (%s, %s)
            RETURNING id;
        """
        cur.execute(query, (psycopg2.Binary(original_data), prompt_text))
        new_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'status': 'ok', 'id': new_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_images', methods=['GET'])
def get_images():
    """Fetch saved images and prompt text."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, original_image_data, prompt_text
            FROM generated_images
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for row in rows:
            row_id = row[0]
            orig_data = row[1]
            prompt_text = row[2] or ""

            orig_b64 = base64.b64encode(orig_data).decode('utf-8') if orig_data else None

            results.append({
                'id': row_id,
                'original_image_base64': orig_b64,
                'prompt_text': prompt_text
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/delete_image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image and its associated text by id."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM generated_images WHERE id = %s", (image_id,)
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        if deleted:
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'status': 'error', 'message': 'Image not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/history.html')
def serve_history():
    return send_from_directory('.', 'history.html')

@app.route('/manifest.webmanifest')
def manifest():
    return send_from_directory('.', 'manifest.webmanifest')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js')


if __name__ == '__main__':
    # 3. Run the Flask app (default: localhost:5000)
    app.run(host="0.0.0.0", port=10000, debug=True)
