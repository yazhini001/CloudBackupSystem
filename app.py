import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, session, redirect

from datetime import datetime

import pymysql
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        autocommit=True
    )

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        try:

            sql = """
            SELECT * FROM users
            WHERE username=%s AND password=%s
            """

            cursor.execute(sql, (username, password))
            user = cursor.fetchone()

            if user:

                session['user_id'] = user[0]
                session['username'] = user[1]

                return redirect('/dashboard')

            return "Invalid Username or Password!"

        finally:
            cursor.close()
            db.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        try:

            sql = """
            INSERT INTO users(username,email,password)
            VALUES(%s,%s,%s)
            """

            cursor.execute(sql, (username, email, password))

            return "User Registered Successfully!"

        finally:
            cursor.close()
            db.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/')

    db = get_db()
    cursor = db.cursor()

    try:

        cursor.execute(
            "SELECT COUNT(*) FROM backups WHERE user_id=%s",
            (session['user_id'],)
        )

        file_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT file_size FROM backups WHERE user_id=%s",
            (session['user_id'],)
        )

        sizes = cursor.fetchall()

        total_size = 0

        for size in sizes:
            if size[0]:
                total_size += float(size[0].replace(" KB", ""))

        cursor.execute(
            """
            SELECT file_name
            FROM backups
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT 5
            """,
            (session['user_id'],)
        )

        recent_files = cursor.fetchall()

        return render_template(
            'dashboard.html',
            username=session['username'],
            file_count=file_count,
            total_size=round(total_size, 2),
            recent_files=recent_files
        )

    finally:
        cursor.close()
        db.close()

@app.route('/upload', methods=['GET', 'POST']) #  Allows both viewing and uploading
def upload_file():
    if request.method == 'POST':
        upload_result = None
        file_url = None
        
        try:
            if 'file' not in request.files:
                return "No file part", 400
            
            file = request.files['file']
            if file.filename == '':
                return "No selected file", 400

            if file:
                # Force resource_type='raw' for PDFs
                upload_result = cloudinary.uploader.upload(
                    file,
                    resource_type="raw" 
                )
                
                file_url = upload_result.get('secure_url')
                
                # Your MySQL database insertion code goes here
                # cursor.execute("INSERT INTO ... VALUES (%s)", (file_url,))
                
                return "Upload successful!", 200

        except Exception as e:
            print(f"Error during upload: {e}")
            return f"Internal Server Error: {str(e)}", 500

    # ⬇️ THIS IS WHAT LOADS THE PAGE WHeN YOU JUST VISIT THE URL
    # Replace 'upload.html' with whatever your HTML file is named
    return render_template('upload.html')

@app.route('/files')
def files():

    search = request.args.get('search', '')

    db = get_db()
    cursor = db.cursor()

    try:

        sql = """
        SELECT id,file_name,cloudinary_url,upload_data,file_size,category
        FROM backups
        WHERE user_id=%s
        AND file_name LIKE %s
        """

        cursor.execute(
            sql,
            (
                session['user_id'],
                '%' + search + '%'
            )
        )

        files = cursor.fetchall()

        return render_template(
            'files.html',
            files=files,
            search=search
        )

    finally:
        cursor.close()
        db.close()

@app.route('/delete/<int:file_id>')
def delete_file(file_id):

    db = get_db()
    cursor = db.cursor()

    try:

        cursor.execute(
            """
            UPDATE backups
            SET is_deleted=1
            WHERE id=%s
            """,
            (file_id,)
        )

        return "File Moved To Recycle Bin!"

    finally:
        cursor.close()
        db.close()

@app.route('/recycle_bin')
def recycle_bin():

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, file_name, upload_data
        FROM backups
        WHERE user_id=%s
        AND is_deleted=1
        """,
        (session['user_id'],)
    )

    files = cursor.fetchall()

    return render_template(
        'recycle_bin.html',
        files=files
    )


@app.route('/restore/<int:file_id>')
def restore_file(file_id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE backups
        SET is_deleted=0
        WHERE id=%s
        """,
        (file_id,)
    )

    db.commit()

    return "File Restored Successfully!"


@app.route('/profile')
def profile():

    if 'user_id' not in session:
        return redirect('/')

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT username, email FROM users WHERE id=%s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    if not user:
        return "User not found!"

    return render_template(
        'profile.html',
        username=user[0],
        email=user[1]
    )

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():

    if request.method == 'POST':

        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT password
            FROM users
            WHERE id=%s
            """,
            (session['user_id'],)
        )

        current_password = cursor.fetchone()[0]

        if old_password != current_password:
            return "Old Password is incorrect!"

        if new_password != confirm_password:
            return "New Password and Confirm Password do not match!"

        cursor.execute(
            """
            UPDATE users
            SET password=%s
            WHERE id=%s
            """,
            (new_password, session['user_id'])
        )

        db.commit()

        return "Password Changed Successfully!"

    return render_template('change_password.html')

@app.route('/favorite/<int:file_id>')
def favorite_file(file_id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE backups
        SET is_favorite=1
        WHERE id=%s
        """,
        (file_id,)
    )

    db.commit()

    return "File Added To Favorites!"

@app.route('/favorites')
def favorites():

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT id, file_name, upload_data
        FROM backups
        WHERE user_id=%s
        AND is_favorite=1
        """,
        (session['user_id'],)
    )

    files = cursor.fetchall()

    return render_template(
        'favorites.html',
        files=files
    )

@app.route("/check_env")
def check_env():
    return {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD_EXISTS": os.getenv("DB_PASSWORD") is not None,

        "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "API_KEY_EXISTS": os.getenv("CLOUDINARY_API_KEY") is not None,
        "API_SECRET_EXISTS": os.getenv("CLOUDINARY_API_SECRET") is not None
    }

if __name__ == '__main__':
    app.run(debug=True)
