from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_session import Session
from pymongo import MongoClient
from bson import ObjectId
import uuid
import os
import datetime
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import io
import pytesseract
import re
import easyocr

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# MongoDB Atlas connection
client = MongoClient('mongodb+srv://gnana1313:Gnana1212@dbs.8wngtib.mongodb.net/student_art_gallery?retryWrites=true&w=majority&appName=DBs')
db = client['certificate_verification']

# Collections
users_col = db['users']
applications_col = db['applications']
certificates_col = db['certificates']
courses_col = db['courses']

# --- ROUTES ---

# Homepage
@app.route('/')
def home():
    return render_template('home.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = users_col.find_one({'email': email})
        if existing_user:
            return render_template('signup.html', error="User with this email already exists")
        
        # Create new user
        user_data = {
            'name': name,
            'roll_no': roll_no,
            'email': email,
            'password': password  # In production, hash the password
        }
        users_col.insert_one(user_data)
        
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Find user
        user = users_col.find_one({'email': email, 'password': password})
        if user:
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password")
    
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Admin Logout
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('home'))

# User Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user data for profile
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('dashboard.html', user=user)

# Apply Certificate
@app.route('/apply', methods=['GET', 'POST'])
def apply_certificate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        course = request.form['course']
        
        # Create application
        application_data = {
            'user_id': session['user_id'],
            'name': name,
            'roll_no': roll_no,
            'course': course,
            'status': 'Pending',
            'created_at': datetime.datetime.now()
        }
        applications_col.insert_one(application_data)
        
        return redirect(url_for('status'))
    
    # Get available courses for dropdown
    courses = list(courses_col.find())
    # Get user data for profile
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('apply_certificate.html', courses=courses, user=user)

# Status
@app.route('/status')
def status():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all applications for the user, most recent first
    applications = list(applications_col.find({'user_id': session['user_id']}).sort('created_at', -1))
    
    # Get user data for profile
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('status.html', applications=applications, user=user)

# Certificates
@app.route('/certificates')
def certificates():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's certificates
    user_certificates = list(certificates_col.find({'user_id': session['user_id']}))
    # Get user data for profile
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('certificates.html', certificates=user_certificates, user=user)

# Certificate Verification
@app.route('/verify', methods=['GET', 'POST'])
def verify_certificate():
    result = None
    certificate_data = None
    error = None

    if request.method == 'POST':
        if 'certificate_file' not in request.files:
            error = 'No file uploaded.'
        else:
            file = request.files['certificate_file']
            if file.filename == '' or not file.filename.lower().endswith('.png'):
                error = 'Please upload a PNG certificate file.'
            else:
                import tempfile
                from PIL import Image
                import os
                fd, temp_path = tempfile.mkstemp(suffix='.png')
                os.close(fd)
                try:
                    file.save(temp_path)
                    image = Image.open(temp_path)
                    hash_code = None
                    # Check both info and text for maximum compatibility
                    if hasattr(image, 'text') and 'certificate_hash' in image.text:
                        hash_code = image.text['certificate_hash']
                    elif 'certificate_hash' in image.info:
                        hash_code = image.info['certificate_hash']
                    if hash_code:
                        certificate = certificates_col.find_one({'hash': hash_code})
                        if certificate:
                            result = 'verified'
                            certificate_data = certificate
                        else:
                            result = 'not_verified'
                    else:
                        error = 'This image does not contain a certificate hash. Please upload a valid certificate generated by this system.'
                finally:
                    os.remove(temp_path)

    return render_template('verify.html', result=result, certificate=certificate_data, error=error)

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Static admin credentials
        if username == 'admin' and password == '123456':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    
    return render_template('admin_login.html')

# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Calculate statistics
    stats = {
        'users': users_col.count_documents({}),
        'applications': applications_col.count_documents({}),
        'courses': courses_col.count_documents({}),
        'certificates': certificates_col.count_documents({})
    }
    
    return render_template('admin_dashboard.html', stats=stats)

# Admin: Users
@app.route('/admin/users')
def admin_users():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    users = list(users_col.find({}, {'password': 0}))  # Exclude passwords
    # Add certificate count for each user
    for user in users:
        user['certificates'] = certificates_col.count_documents({'user_id': str(user['_id'])})
    return render_template('admin_users.html', users=users)

# Admin: Applications
@app.route('/admin/applications')
def admin_applications():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Get applications and join with certificates to get hash
    applications = list(applications_col.find())
    
    # For each application, get the certificate hash if it exists
    for app in applications:
        if app.get('status') == 'Certificate Generated':
            certificate = certificates_col.find_one({'user_id': app['user_id'], 'name': app['name'], 'course': app['course']})
            if certificate:
                app['hash'] = certificate['hash']
    
    return render_template('admin_applications.html', applications=applications)

# Admin: Generate Certificate
@app.route('/admin/generate_certificate/<application_id>', methods=['POST'])
def generate_certificate(application_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Get application
    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if application:
        # Generate unique hash
        hash_code = str(uuid.uuid4())
        
        # Create certificate
        certificate_data = {
            'user_id': application['user_id'],
            'name': application['name'],
            'roll_no': application['roll_no'],
            'course': application['course'],
            'hash': hash_code,
            'generated_at': datetime.datetime.now()
        }
        certificates_col.insert_one(certificate_data)
        
        # Update application status and add hash
        applications_col.update_one(
            {'_id': ObjectId(application_id)},
            {'$set': {'status': 'Certificate Generated', 'hash': hash_code}}
        )
    
    return redirect(url_for('admin_applications'))

# Admin: Reject Application
@app.route('/admin/reject_application/<application_id>', methods=['POST'])
def reject_application(application_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Update application status to rejected
    applications_col.update_one(
        {'_id': ObjectId(application_id)},
        {'$set': {'status': 'Rejected'}}
    )
    
    return redirect(url_for('admin_applications'))

# Admin: Courses
@app.route('/admin/courses', methods=['GET', 'POST'])
def admin_courses():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form['name']
        duration = request.form['duration']
        
        course_data = {
            'name': name,
            'duration': duration,
            'company': 'MakeSkilled'  # Default company
        }
        courses_col.insert_one(course_data)
        return redirect(url_for('admin_courses'))
    
    courses = list(courses_col.find())
    return render_template('admin_courses.html', courses=courses)

# Admin: Delete Course
@app.route('/admin/delete_course/<course_id>', methods=['POST'])
def delete_course(course_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Check if course is being used in any applications
    course = courses_col.find_one({'_id': ObjectId(course_id)})
    if course:
        # Check if any applications use this course
        applications_using_course = applications_col.count_documents({'course': course['name']})
        if applications_using_course > 0:
            # Don't delete if course is in use
            return redirect(url_for('admin_courses'))
        
        # Delete the course
        courses_col.delete_one({'_id': ObjectId(course_id)})
    
    return redirect(url_for('admin_courses'))

# Download Certificate as PNG
@app.route('/download/<hashcode>')
def download_certificate(hashcode):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Find certificate
    certificate = certificates_col.find_one({'hash': hashcode, 'user_id': session['user_id']})
    if not certificate:
        return "Certificate not found", 404
    
    try:
        # Create certificate image using PIL
        width, height = 1200, 800
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to load fonts, fallback to default if not available
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            name_font = ImageFont.truetype("arial.ttf", 36)
            subtitle_font = ImageFont.truetype("arial.ttf", 24)
            body_font = ImageFont.truetype("arial.ttf", 18)
            small_font = ImageFont.truetype("arial.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw gradient background
        for y in range(height):
            r = int(255 - (y / height) * 20)
            g = int(255 - (y / height) * 15)
            b = int(255 - (y / height) * 10)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Draw border
        border_color = (102, 126, 234)  # Blue
        draw.rectangle([(0, 0), (width-1, height-1)], outline=border_color, width=8)
        draw.rectangle([(20, 20), (width-21, height-21)], outline=(232, 232, 232), width=2)
        
        # Draw decorative elements
        # Top gradient bar
        for x in range(width):
            r = int(102 + (x / width) * 50)
            g = int(126 + (x / width) * 30)
            b = int(234 + (x / width) * 20)
            draw.line([(x, 0), (x, 8)], fill=(r, g, b))
        
        # Watermark - move to lower part, behind signatures, and make more transparent
        watermark_color = (102, 126, 234, 10)  # Even lighter blue
        watermark_font_size = 72
        try:
            watermark_font = ImageFont.truetype("arial.ttf", watermark_font_size)
        except:
            watermark_font = ImageFont.load_default()
        watermark_y = 650
        draw.text((width//2, watermark_y), "CERTIFICATE", font=watermark_font, fill=watermark_color, anchor="mm")
        
        # Logo
        logo_color = (102, 126, 234)
        draw.text((width//2, 80), "MakeSkilled", font=subtitle_font, fill=logo_color, anchor="mm")
        
        # Title
        title_color = (44, 62, 80)  # Dark blue
        draw.text((width//2, 150), "Certificate of Completion", font=title_font, fill=title_color, anchor="mm")
        
        # Subtitle
        subtitle_color = (127, 140, 141)  # Gray
        draw.text((width//2, 220), "This is to certify that", font=body_font, fill=subtitle_color, anchor="mm")
        
        # Student name
        name_color = (44, 62, 80)
        draw.text((width//2, 280), certificate['name'], font=name_font, fill=name_color, anchor="mm")
        
        # Course text
        draw.text((width//2, 340), "has successfully completed the course", font=body_font, fill=subtitle_color, anchor="mm")
        
        # Course name - properly aligned and wrapped if needed, moved further down
        course_color = (102, 126, 234)
        course_text = certificate['course']
        
        # Check if course name is too long and wrap it
        if len(course_text) > 25:
            # Split into multiple lines if too long
            words = course_text.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= 25:
                    current_line += " " + word if current_line else word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Draw multiple lines with proper spacing
            line_height = 35
            start_y = 420 - (len(lines) - 1) * line_height // 2
            for i, line in enumerate(lines):
                y_pos = start_y + i * line_height
                draw.text((width//2, y_pos), line, font=subtitle_font, fill=course_color, anchor="mm")
            course_name_bottom = start_y + (len(lines)-1)*line_height
        else:
            draw.text((width//2, 420), course_text, font=subtitle_font, fill=course_color, anchor="mm")
            course_name_bottom = 420
        
        # Date - moved down to avoid overlap
        date_text = f"Issued on {certificate['generated_at'].strftime('%B %d, %Y') if certificate.get('generated_at') else 'Date'}"
        draw.text((width//2, course_name_bottom + 50), date_text, font=body_font, fill=subtitle_color, anchor="mm")
        
        # Signatures - moved down to maintain proper spacing
        signature_y = course_name_bottom + 130
        # Left signature
        draw.text((300, signature_y), "Sravani M", font=small_font, fill=title_color, anchor="mm")
        draw.text((300, signature_y + 20), "Director of Education", font=small_font, fill=subtitle_color, anchor="mm")
        draw.line([(225, signature_y - 10), (375, signature_y - 10)], fill=title_color, width=2)
        
        # Right signature
        draw.text((900, signature_y), "Madhu Parvathaneni", font=small_font, fill=title_color, anchor="mm")
        draw.text((900, signature_y + 20), "CEO, MakeSkilled", font=small_font, fill=subtitle_color, anchor="mm")
        draw.line([(825, signature_y - 10), (975, signature_y - 10)], fill=title_color, width=2)
        
        # Certificate ID
        cert_id = f"Certificate ID: {certificate['hash'][:8].upper()}"
        draw.text((width//2, height - 50), cert_id, font=small_font, fill=(149, 165, 166), anchor="mm")
        
        # Save to bytes with hash in metadata
        img_bytes = io.BytesIO()
        meta = PngImagePlugin.PngInfo()
        meta.add_text("certificate_hash", certificate['hash'])
        img.save(img_bytes, format='PNG', pnginfo=meta, quality=95)
        img_bytes.seek(0)
        # Double-check hash is present in metadata (for debugging/logging)
        test_img = Image.open(img_bytes)
        hash_in_meta = test_img.info.get('certificate_hash')
        if not hash_in_meta:
            print('WARNING: Certificate hash not found in PNG metadata after saving!')
        img_bytes.seek(0)
        
        # Return PNG file
        return send_file(img_bytes, mimetype='image/png', as_attachment=True, 
                        download_name=f"certificate_{certificate['name'].replace(' ', '_')}.png")
    
    except Exception as e:
        # Fallback to simple HTML if PNG generation fails
        print(f"PNG generation failed: {e}")
        certificate_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }}
                .certificate {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center; max-width: 800px; margin: 0 auto; }}
                .title {{ font-size: 36px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
                .subtitle {{ font-size: 18px; color: #7f8c8d; margin-bottom: 40px; }}
                .name {{ font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; }}
                .course {{ font-size: 20px; color: #34495e; margin-bottom: 20px; }}
                .hash {{ font-size: 12px; color: #95a5a6; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="certificate">
                <div class="title">Certificate of Completion</div>
                <div class="subtitle">This is to certify that</div>
                <div class="name">{certificate['name']}</div>
                <div class="course">has successfully completed the course</div>
                <div class="course"><strong>{certificate['course']}</strong></div>
                <div class="hash">Certificate ID: {certificate['hash'][:8].upper()}</div>
            </div>
        </body>
        </html>
        """
        return certificate_html

if __name__ == '__main__':
    app.run(debug=True) 