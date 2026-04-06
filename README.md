# Lakshmi Guest House Booking System

**Lakshmi Guest House** is a Flask-based web application tailored for managing and reserving 14 unique guest accommodations, including event halls, private cottages, and multi-tier rooms. The platform provides guests with an intuitive public interface to browse units, view photo galleries, verify real-time availability, and seamlessly book their stay.

What sets this system apart is its manual approval-based payment pipeline. Instead of relying on expensive third-party payment gateways, the application coordinates secure peer-to-peer payments. 

### Payment & Communication Workflow
1. **Pending Request**: When a guest submits a reservation, the system places their request in a "Pending" state. It dynamically calculates the total cost of their stay across their selected dates and computes a fixed **30% advance payment**.
2. **GPay Instructions**: On the success screen, the guest is presented with the owner's Google Pay phone number (9894081505) and a unique Booking Reference Code. Guests are instructed to GPay the 30% advance directly to the owner and include the reference code in the payment remarks.
3. **Owner Dashboard**: Administrators access a secure `/owner` dashboard where they can see all pending requests and track total incoming balance. 
4. **Final Approval & Email**: Once the owner verifies the receipt of the GPay transfer, they simply click "Approve". This automatically clears overlapping requests for the same room and triggers the system to send an **automated SMTP email confirmation** to the guest's personal email, officially confirming their booking. 

This infrastructure safely keeps the owner in full financial control while prioritizing direct and transparent communication with the guest!
