from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import secrets
import requests
from functools import wraps
from dotenv import load_dotenv
import uuid
from werkzeug.utils import secure_filename
from threading import Thread

load_dotenv() # Load variables from .env if present

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_booking_key_2026'
# Ensure instance folder exists for sqlite db
db_path = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'instance')
if not os.path.exists(db_path):
    os.makedirs(db_path)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///guesthouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Image upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)

OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "vicky123")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "vicky.fdj31@gmail.com")

# Debug logging
print(f"🔧 OWNER_PASSWORD loaded: {'Yes' if OWNER_PASSWORD else 'No'}")
print(f"🔧 BREVO_API_KEY loaded: {'Yes' if BREVO_API_KEY else 'No'}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_and_optimize_image(file, acc_id):
    """Save uploaded image without optimization"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Get file extension
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"acc_{acc_id}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Save file directly without optimization
    file.save(filepath)
    
    return filename

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_owner'):
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def send_confirmation_email(to_email, name, acc_type, ref, check_in, check_out):
    if not BREVO_API_KEY:
        print("⚠️ BREVO_API_KEY not configured!")
        return False
    
    def send_email_async():
        try:
            body = f"""Hello {name},
    
Your booking for {acc_type} has been successfully APPROVED!
Reference Number: {ref}
Dates: {check_in.strftime('%b %d, %Y')} to {check_out.strftime('%b %d, %Y')}

Thank you for choosing Lakshmi Guest House. We look forward to hosting you!

Best regards,
Lakshmi Guest House Management
"""
            
            print(f"📧 Sending confirmation email to {to_email}...")
            
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": BREVO_API_KEY},
                json={
                    "sender": {"name": "Lakshmi Guest House", "email": SENDER_EMAIL},
                    "to": [{"email": to_email, "name": name}],
                    "subject": f"Booking Confirmed: {acc_type} at Lakshmi Guest House",
                    "textContent": body
                }
            )
            
            if response.status_code == 201:
                print(f"✅ Confirmation email sent to {to_email}")
            else:
                print(f"❌ Brevo Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Failed to send confirmation email: {e}")
    
    thread = Thread(target=send_email_async)
    thread.daemon = True
    thread.start()
    return True

def send_rejection_email(to_email, name, acc_type, ref):
    if not BREVO_API_KEY:
        print("⚠️ BREVO_API_KEY not configured!")
        return False
    
    def send_email_async():
        try:
            body = f"""Hello {name},
    
Your booking for {acc_type} (Ref: {ref}) has unfortunately NOT been approved.
This is because the required 30% advance payment has not been received.

If you have any questions or would like to make the payment and recreate the booking, please contact us.

Thank you for considering Lakshmi Guest House.

Best regards,
Lakshmi Guest House Management
"""
            
            print(f"📧 Sending rejection email to {to_email}...")
            
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": BREVO_API_KEY},
                json={
                    "sender": {"name": "Lakshmi Guest House", "email": SENDER_EMAIL},
                    "to": [{"email": to_email, "name": name}],
                    "subject": f"Booking Update: {acc_type} at Lakshmi Guest House",
                    "textContent": body
                }
            )
            
            if response.status_code == 201:
                print(f"✅ Rejection email sent to {to_email}")
            else:
                print(f"❌ Brevo Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Failed to send rejection email: {e}")
    
    thread = Thread(target=send_email_async)
    thread.daemon = True
    thread.start()
    return True

# --- Models ---
class Accommodation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # e.g. "Room 1", "Hall 1"
    type = db.Column(db.String(50), nullable=False)  # Hall, Cottage, Room
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_filenames = db.Column(db.Text, nullable=True)
    is_closed = db.Column(db.Boolean, default=False)
    max_people = db.Column(db.Integer, default=1)  # Number of people accommodation
    facilities = db.Column(db.Text, nullable=True)  # Comma-separated: AC,TV,Heater

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='Pending') # Pending, Approved, Rejected
    booking_ref = db.Column(db.String(20), unique=True, nullable=False)
    advance_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    accommodation = db.relationship('Accommodation', backref=db.backref('bookings', lazy=True))

# --- Setup Database ---
with app.app_context():
    db.create_all()
    if not Accommodation.query.first():
        inventory = [
            # 4 Halls
            Accommodation(name='Hall 1', type='Hall', description='Our largest hall suitable for weddings and massive gatherings.', price=1500.0, image_filenames='sample_hall.jpg,sample_hall.jpg,sample_hall.jpg', max_people=15),
            Accommodation(name='Hall 2', type='Hall', description='Elegant hall perfect for formal events and corporate dinners.', price=2500.0, image_filenames='sample_hall.jpg,sample_hall.jpg,sample_hall.jpg', max_people=25),
            Accommodation(name='Hall 3', type='Hall', description='Cozy indoor hall for birthdays and small celebrations.', price=4000.0, image_filenames='sample_hall.jpg,sample_hall.jpg', max_people=50),
            
            # 2 Cottages
            Accommodation(name='Cottage 1', type='Cottage', description='A private and fully furnished cottage explicitly designed for couples.', price=3000.0, image_filenames='cottage1[1].jpeg,cottage1[2].jpeg', max_people=15, facilities='AC,TV,Heater'),
            Accommodation(name='Cottage 2', type='Cottage', description='A large cottage featuring two bedrooms, private kitchen, and living room.', price=4000.0, image_filenames='cottage2[1].jpeg,cottage2[2].jpeg,cottage2[3].jpeg', max_people=30, facilities='AC,TV,Heater'),
            
            # 8 Rooms
            Accommodation(name='Room 1', type='Room', description='Compact and comfortable single room.', price=1300.0, image_filenames='room1.jpeg', max_people=4, facilities=None),
            Accommodation(name='Room 2', type='Room', description='Standard double bed room with basic amenities.', price=1300.0, image_filenames='room2.jpeg', max_people=4, facilities=None),
            Accommodation(name='Room 3', type='Room', description='Spacious double room with balcony view.', price=1500.0, image_filenames='room3[1].jpeg,room3[2].jpeg', max_people=4, facilities='AC,TV,Heater'),
            Accommodation(name='Room 4', type='Room', description='Premium executive room with central air conditioning.', price=1500.0, image_filenames='room4[1].jpeg,room4[2].jpeg', max_people=4, facilities='AC,TV,Heater'),
            Accommodation(name='Room 5', type='Room', description='Large suite with one double bed and two twin beds.', price=1500.0, image_filenames='room5.jpeg', max_people=4, facilities='AC,TV,Heater'),
            Accommodation(name='Room 6', type='Room', description='Luxury premium room with minibar and attached lounge.', price=1500.0, image_filenames='room6.jpeg', max_people=4, facilities='AC,TV,Heater'),
            Accommodation(name='Room 7', type='Room', description='Simple AC room perfect for short stays.', price=800.0, image_filenames='room1.jpeg', max_people=4),
            Accommodation(name='Room 8', type='Room', description='Economical choice without AC but excellent ventilation.', price=800.0, image_filenames='room2.jpeg', max_people=4),
        ]
        db.session.add_all(inventory)
        db.session.commit()

# --- Routes ---
@app.route('/')
def index():
    types = ['Hall', 'Cottage', 'Room']
    categories = []
    
    today = datetime.now().date()
    for t in types:
        total_units = Accommodation.query.filter_by(type=t).count()
        
        unavailable_count = db.session.query(Accommodation.id).filter(
            Accommodation.type == t,
            db.or_(
                Accommodation.is_closed == True,
                Accommodation.id.in_(
                    db.session.query(Booking.accommodation_id).filter(
                        Booking.status == 'Approved',
                        Booking.check_out >= today
                    )
                )
            )
        ).count()
        
        available_today = total_units - unavailable_count
        
        # Use specific images for categories
        if t == 'Cottage':
            img_filename = 'cottage2[2].jpeg'
        else:
            img_filename = f"sample_{t.lower()}.jpg"
        
        categories.append({
            'name': t,
            'description': f"Browse our beautiful properties and pick the perfect {t.lower()} for your needs.",
            'available': available_today,
            'image_filename': img_filename
        })
        
    return render_template('index.html', categories=categories)

@app.route('/category/<string:acc_type>')
def category_view(acc_type):
    # Retrieve all accommodations of this type
    accommodations = Accommodation.query.filter_by(type=acc_type).all()
    today = datetime.now().date()
    
    # Pre-calculate booked status
    for acc in accommodations:
        if acc.is_closed:
            acc.is_available_today = False
        else:
            is_booked = Booking.query.filter(
                Booking.accommodation_id == acc.id,
                Booking.status == 'Approved',
                Booking.check_out >= today
            ).first()
            acc.is_available_today = not bool(is_booked)
        
    return render_template('category.html', accommodations=accommodations, acc_type=acc_type)

@app.route('/book/<int:acc_id>', methods=['GET', 'POST'])
def book(acc_id):
    accommodation = Accommodation.query.get_or_404(acc_id)
    
    if accommodation.is_closed:
        flash(f"Sorry, {accommodation.name} is currently closed and unavailable for booking.", "error")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        guest_name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        check_in_str = request.form.get('check_in')
        check_out_str = request.form.get('check_out')

        try:
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if check_in < today:
                flash("Check-in date cannot be in the past.", "error")
                return redirect(url_for('book', acc_id=acc_id))
                
            if check_in >= check_out:
                flash("Check-out date must be after check-in date.", "error")
                return redirect(url_for('book', acc_id=acc_id))
            
            if accommodation.is_closed:
                flash(f"Sorry, {accommodation.name} is currently closed and unavailable.", "error")
                return redirect(url_for('book', acc_id=acc_id))
            
            # 1-to-1 Availability Check (Only considering Approved bookings)
            overlapping_approved = Booking.query.filter(
                Booking.accommodation_id == acc_id,
                Booking.status == 'Approved',
                Booking.check_in < check_out,
                Booking.check_out > check_in
            ).first()

            if overlapping_approved:
                flash(f"Sorry, {accommodation.name} is already booked for these dates.", "error")
                return redirect(url_for('book', acc_id=acc_id))

            # Generate booking reference using accommodation name for uniqueness
            # Format: Room3-ABC1, Cottage1-XYZ9, etc.
            short_id = str(uuid.uuid4())[:4].upper()
            ref = f"{accommodation.name.replace(' ', '')}-{short_id}"
            stay_days = (check_out - check_in).days
            advance = (accommodation.price * stay_days) * 0.30  # 30% advance of total cost

            new_booking = Booking(
                accommodation_id=acc_id,
                guest_name=guest_name,
                email=email,
                phone=phone,
                check_in=check_in,
                check_out=check_out,
                booking_ref=ref,
                advance_amount=advance,
                status='Pending'
            )
            db.session.add(new_booking)
            db.session.commit()
            
            return redirect(url_for('success', name=guest_name, type=accommodation.name, ref=ref, advance=advance, phone=phone, email=email, check_in=check_in_str, check_out=check_out_str))
            
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for('book', acc_id=acc_id))
            
    return render_template('book.html', accommodation=accommodation)

@app.route('/success')
def success():
    name = request.args.get('name', 'Guest')
    acc_type = request.args.get('type', 'Accommodation')
    ref = request.args.get('ref', 'UNKNOWN')
    advance = request.args.get('advance', '0.0')
    phone = request.args.get('phone', '')
    email = request.args.get('email', '')
    check_in = request.args.get('check_in', '')
    check_out = request.args.get('check_out', '')
    return render_template('success.html', name=name, acc_type=acc_type, ref=ref, advance=advance, phone=phone, email=email, check_in=check_in, check_out=check_out)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == OWNER_PASSWORD:
            session['is_owner'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('owner_dashboard'))
        else:
            flash('Invalid password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('is_owner', None)
    flash('Logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/owner')
@login_required
def owner_dashboard():
    pending = Booking.query.filter_by(status='Pending').order_by(Booking.created_at.desc()).all()
    approved = Booking.query.filter_by(status='Approved').order_by(Booking.check_in.desc()).all()
    rejected = Booking.query.filter_by(status='Rejected').order_by(Booking.created_at.desc()).all()
    accommodations = Accommodation.query.order_by(Accommodation.type).all()
    
    total_earnings = sum(b.advance_amount for b in approved)
    
    return render_template('owner_dashboard.html', pending=pending, approved=approved, rejected=rejected, earnings=total_earnings, accommodations=accommodations)

@app.route('/owner/approve/<int:id>', methods=['POST'])
@login_required
def approve_booking(id):
    booking = Booking.query.get_or_404(id)
    if booking.status != 'Pending':
        flash('Booking is not pending.', 'error')
        return redirect(url_for('owner_dashboard'))
        
    # Check if there's already an approved overlapping booking (just to be safe)
    overlapping_approved = Booking.query.filter(
        Booking.accommodation_id == booking.accommodation_id,
        Booking.status == 'Approved',
        Booking.check_in < booking.check_out,
        Booking.check_out > booking.check_in
    ).first()
    
    if overlapping_approved:
        flash('Cannot approve: There is already an approved booking for these dates.', 'error')
        return redirect(url_for('owner_dashboard'))
        
    booking.status = 'Approved'
    
    # Reject other pending bookings for the same unit and overlapping dates
    overlapping_pending = Booking.query.filter(
        Booking.accommodation_id == booking.accommodation_id,
        Booking.id != booking.id,
        Booking.status == 'Pending',
        Booking.check_in < booking.check_out,
        Booking.check_out > booking.check_in
    ).all()
    
    for op in overlapping_pending:
        op.status = 'Rejected'
        
    db.session.commit()
    
    # Send email
    if send_confirmation_email(booking.email, booking.guest_name, booking.accommodation.name, booking.booking_ref, booking.check_in, booking.check_out):
        flash(f'Booking #{booking.booking_ref} approved and email sent successfully!', 'success')
    else:
        flash(f'Booking #{booking.booking_ref} approved BUT email failed to send (check MAIL_PASSWORD).', 'success')
        
    return redirect(url_for('owner_dashboard'))

@app.route('/owner/reject/<int:id>', methods=['POST'])
@login_required
def reject_booking(id):
    booking = Booking.query.get_or_404(id)
    booking.status = 'Rejected'
    db.session.commit()
    
    if send_rejection_email(booking.email, booking.guest_name, booking.accommodation.name, booking.booking_ref):
        flash(f'Booking #{booking.booking_ref} rejected and email notification sent.', 'success')
    else:
        flash(f'Booking #{booking.booking_ref} rejected (email failed to send).', 'success')
        
    return redirect(url_for('owner_dashboard'))

@app.route('/owner/toggle_unit/<int:id>', methods=['POST'])
@login_required
def toggle_unit(id):
    acc = Accommodation.query.get_or_404(id)
    acc.is_closed = not acc.is_closed
    db.session.commit()
    status = "closed" if acc.is_closed else "opened"
    flash(f'{acc.name} has been {status}.', 'success')
    return redirect(url_for('owner_dashboard'))

@app.route('/owner/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_booking(id):
    booking = Booking.query.get_or_404(id)
    if booking.status == 'Approved':
        booking.status = 'Cancelled'
        db.session.commit()
        flash(f'Booking #{booking.booking_ref} has been cancelled and the room is reopened.', 'success')
    else:
        flash('Only approved bookings can be cancelled.', 'error')
    return redirect(url_for('owner_dashboard'))

# Image upload feature removed - images are now static

# Image delete feature removed - images are now static

@app.route('/owner/edit_unit/<int:acc_id>', methods=['POST'])
@login_required
def edit_unit(acc_id):
    accommodation = Accommodation.query.get_or_404(acc_id)
    
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '')
    max_people = request.form.get('max_people', '')
    
    if not name:
        flash('Room name cannot be empty.', 'error')
        return redirect(url_for('owner_dashboard'))
    
    try:
        price = float(price)
        if price < 0:
            flash('Price cannot be negative.', 'error')
            return redirect(url_for('owner_dashboard'))
    except ValueError:
        flash('Invalid price format. Please enter a valid number.', 'error')
        return redirect(url_for('owner_dashboard'))
    
    try:
        max_people = int(max_people)
        if max_people < 1:
            flash('Accommodation capacity must be at least 1 person.', 'error')
            return redirect(url_for('owner_dashboard'))
    except ValueError:
        flash('Invalid capacity format. Please enter a valid number.', 'error')
        return redirect(url_for('owner_dashboard'))
    
    accommodation.name = name
    accommodation.price = price
    accommodation.max_people = max_people
    db.session.commit()
    
    flash(f'Room updated: {name} - ₹{price} (Capacity: {max_people})', 'success')
    return redirect(url_for('owner_dashboard'))

@app.route('/owner/update_facilities/<int:acc_id>', methods=['POST'])
@login_required
def update_facilities(acc_id):
    accommodation = Accommodation.query.get_or_404(acc_id)
    
    # Get checked facilities
    facilities = []
    if request.form.get('ac'):
        facilities.append('AC')
    if request.form.get('tv'):
        facilities.append('TV')
    if request.form.get('heater'):
        facilities.append('Heater')
    
    # Store as comma-separated string
    accommodation.facilities = ','.join(facilities) if facilities else None
    db.session.commit()
    
    facility_text = ', '.join(facilities) if facilities else 'None'
    flash(f'Facilities updated for {accommodation.name}: {facility_text}', 'success')
    return redirect(url_for('owner_dashboard'))

if __name__ == '__main__':
    # Debug mode only for development
    is_production = os.environ.get('PRODUCTION', 'False') == 'True'
    app.run(debug=not is_production, port=5000)
