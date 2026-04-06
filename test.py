from app import app, db, Booking
import datetime

with app.app_context():
    print("Today is:", datetime.datetime.now().date())
    for b in Booking.query.all():
        print(f"ID: {b.id}, Guest: {b.guest_name}, Room: {b.accommodation_id}, In: {b.check_in}, Out: {b.check_out}, Status: {b.status}")
