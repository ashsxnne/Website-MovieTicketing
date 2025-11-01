from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import random
import string
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_2025_movie_booking'

# ---------------- DATABASE SETUP ----------------
def init_db():
    # Don't delete existing database to preserve data
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS user_table (
                    u_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    u_name TEXT NOT NULL,
                    u_email TEXT UNIQUE NOT NULL,
                    u_pass TEXT NOT NULL,
                    u_role TEXT DEFAULT 'Customer',
                    u_status TEXT DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Movies table
    c.execute('''CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    genre TEXT,
                    duration TEXT,
                    rating TEXT,
                    description TEXT,
                    poster_url TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(title, genre, duration)
                )''')

    # Movie schedules table
    c.execute('''CREATE TABLE IF NOT EXISTS movie_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        movie_title TEXT NOT NULL,
        show_date TEXT NOT NULL,
        showtime TEXT NOT NULL,
        total_seats INTEGER DEFAULT 40,
        available_seats INTEGER DEFAULT 40,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies (id),
        UNIQUE(movie_id, show_date, showtime)
    )''')

    # Bookings table
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_booking (
                    b_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    u_id INTEGER NOT NULL,
                    movie_name TEXT NOT NULL,
                    show_date TEXT,
                    showtime TEXT NOT NULL,
                    seat_no TEXT NOT NULL,
                    booking_fee REAL DEFAULT 0,
                    status TEXT DEFAULT 'Ongoing',
                    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_status TEXT DEFAULT 'Pending',
                    booking_reference TEXT,
                    FOREIGN KEY (u_id) REFERENCES user_table (u_id)
                )''')

    # Seat availability table
    c.execute('''CREATE TABLE IF NOT EXISTS seat_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            movie_title TEXT NOT NULL,
            show_date TEXT NOT NULL,
            showtime TEXT NOT NULL,
            seat_number TEXT NOT NULL,
            is_available BOOLEAN DEFAULT 1,
            booking_id INTEGER,
            FOREIGN KEY (schedule_id) REFERENCES movie_schedules (id),
            UNIQUE(schedule_id, seat_number)
        )''')

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ---------------- SEAT INITIALIZATION ----------------
def initialize_seat_availability():
    """Initialize seat availability for all movie schedules"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Define all seats (A1-E8)
    rows = ["A", "B", "C", "D", "E"]
    seats_per_row = 8
    all_seats = [f"{row}{i}" for row in rows for i in range(1, seats_per_row + 1)]

    # Get all active schedules
    c.execute("SELECT id, movie_title, show_date, showtime FROM movie_schedules WHERE is_active = 1")
    schedules = c.fetchall()

    # Initialize seats for each schedule
    for schedule in schedules:
        schedule_id, movie_title, show_date, showtime = schedule
        for seat in all_seats:
            try:
                c.execute('''INSERT OR IGNORE INTO seat_availability 
                            (schedule_id, movie_title, show_date, showtime, seat_number, is_available) 
                            VALUES (?, ?, ?, ?, ?, ?)''',
                          (schedule_id, movie_title, show_date, showtime, seat, 1))
            except Exception as e:
                print(f"Error inserting seat {seat} for {movie_title}: {e}")

    conn.commit()
    conn.close()
    print("✅ Seat availability initialized!")

# Initialize everything in correct order
print("🚀 Starting database setup...")
init_db()
initialize_seat_availability()
print("🎉 All database setup completed successfully!")

# ---------------- ALL ROUTES ----------------

# ---------------- HOME PAGE ----------------
@app.route('/')
@app.route('/home')
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, title, rating, poster_url FROM movies WHERE is_active = 1")
    movies = c.fetchall()
    conn.close()

    movie_list = []
    for movie in movies:
        movie_list.append({
            'id': movie[0],
            'title': movie[1],
            'rating': movie[2] if movie[2] else 'PG',
            'poster_url': movie[3]
        })

    return render_template('logout.html', movies=movie_list)

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match!")

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("""
                INSERT INTO user_table (u_name, u_email, u_pass, u_role, u_status)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, hashed_password, role, 'Active'))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Email already registered!")
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_email = request.form['username_email']
        password = request.form['password']
        role = request.form.get('role', 'customer')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if input is email or username
        if '@' in username_email:
            c.execute("SELECT * FROM user_table WHERE u_email = ?", (username_email,))
        else:
            c.execute("SELECT * FROM user_table WHERE u_name = ?", (username_email,))

        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            if user[4].lower() != role.lower():
                return render_template('login.html', error=f"Please login as {user[4]}")

            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            session['status'] = user[5]

            if session['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            return render_template('login.html', error="Invalid username/email or password!")

    return render_template('login.html')

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' in session and session['role'] == 'Admin':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Get all bookings
        c.execute("""
            SELECT b.b_id, u.u_name, b.movie_name, b.seat_no, b.show_date, b.status, b.booking_fee
            FROM tbl_booking b
            JOIN user_table u ON b.u_id = u.u_id
            ORDER BY b.booking_date DESC
        """)
        bookings = c.fetchall()

        # Get all movies
        c.execute("SELECT id, title, genre, duration, rating, description, poster_url FROM movies")
        movies = c.fetchall()

        conn.close()

        # Convert tuples to dictionaries for easier template access
        booking_list = []
        for booking in bookings:
            booking_list.append({
                'id': booking[0],
                'user_name': booking[1],
                'movie_title': booking[2],
                'seats': booking[3],
                'date': booking[4],
                'status': booking[5],
                'fee': booking[6]
            })

        movie_list = []
        for movie in movies:
            movie_list.append({
                'id': movie[0],
                'title': movie[1],
                'genre': movie[2],
                'duration': movie[3],
                'rating': movie[4],
                'description': movie[5] if movie[5] else '',
                'poster_url': movie[6] if movie[6] else ''
            })

        return render_template('adminindex.html', bookings=booking_list, movies=movie_list)
    else:
        return redirect(url_for('login'))

# ---------------- UPDATE BOOKING STATUS ----------------
@app.route('/update_booking/<int:booking_id>', methods=['POST'])
def update_booking(booking_id):
    if 'role' in session and session['role'] == 'Admin':
        new_status = request.form['status']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE tbl_booking SET status = ? WHERE b_id = ?", (new_status, booking_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

# ---------------- ADD MOVIE ----------------
@app.route('/add_movie', methods=['POST'])
def add_movie():
    if 'role' in session and session['role'] == 'Admin':
        title = request.form['title']
        genre = request.form['genre']
        duration = request.form['duration']
        rating = request.form['rating']
        description = request.form['description']
        poster_url = request.form.get('poster_url', '')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if movie already exists
        c.execute("SELECT id FROM movies WHERE title = ? AND genre = ? AND duration = ?",
                  (title, genre, duration))
        existing_movie = c.fetchone()

        if existing_movie:
            conn.close()
            return redirect(url_for('admin_dashboard'))
        else:
            # Add new movie
            c.execute('''INSERT INTO movies 
                        (title, genre, duration, rating, description, poster_url) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                      (title, genre, duration, rating, description, poster_url))
            conn.commit()
            conn.close()
            return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

# ---------------- EDIT MOVIE ----------------
@app.route('/edit_movie', methods=['POST'])
def edit_movie():
    if 'role' in session and session['role'] == 'Admin':
        movie_id = request.form['movie_id']
        title = request.form['title']
        genre = request.form['genre']
        duration = request.form['duration']
        rating = request.form['rating']
        description = request.form['description']
        poster_url = request.form.get('poster_url', '')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if movie already exists (excluding current movie)
        c.execute("SELECT id FROM movies WHERE title = ? AND genre = ? AND duration = ? AND id != ?",
                  (title, genre, duration, movie_id))
        existing_movie = c.fetchone()

        if existing_movie:
            conn.close()
            return redirect(url_for('admin_dashboard'))
        else:
            # Update the movie
            c.execute('''UPDATE movies SET 
                        title = ?, genre = ?, duration = ?, rating = ?, 
                        description = ?, poster_url = ?
                        WHERE id = ?''',
                      (title, genre, duration, rating, description, poster_url, movie_id))
            conn.commit()
            conn.close()
            return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

# ---------------- DELETE MOVIE ----------------
@app.route('/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    if 'role' in session and session['role'] == 'Admin':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

# ---------------- ADD SCHEDULE ----------------
@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    if 'role' in session and session['role'] == 'Admin':
        movie_id = request.form['movie_id']
        show_date = request.form['show_date']
        showtime = request.form['showtime']
        total_seats = request.form.get('total_seats', 40)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        try:
            # Get movie title
            c.execute("SELECT title FROM movies WHERE id = ?", (movie_id,))
            movie = c.fetchone()
            if not movie:
                return "Movie not found", 404
            movie_title = movie[0]

            # Check if schedule already exists
            c.execute("SELECT id FROM movie_schedules WHERE movie_id = ? AND show_date = ? AND showtime = ?",
                      (movie_id, show_date, showtime))
            existing_schedule = c.fetchone()

            if existing_schedule:
                return "Schedule already exists", 400
            else:
                # Add new schedule
                c.execute('''INSERT INTO movie_schedules 
                            (movie_id, movie_title, show_date, showtime, total_seats, available_seats) 
                            VALUES (?, ?, ?, ?, ?, ?)''',
                          (movie_id, movie_title, show_date, showtime, total_seats, total_seats))

                # Get the new schedule ID
                schedule_id = c.lastrowid

                # Initialize seat availability for this schedule
                rows = ["A", "B", "C", "D", "E"]
                seats_per_row = 8
                all_seats = [f"{row}{i}" for row in rows for i in range(1, seats_per_row + 1)]

                for seat in all_seats:
                    c.execute('''INSERT OR IGNORE INTO seat_availability 
                                (schedule_id, movie_title, show_date, showtime, seat_number, is_available) 
                                VALUES (?, ?, ?, ?, ?, ?)''',
                              (schedule_id, movie_title, show_date, showtime, seat, 1))

                conn.commit()
                return "Schedule added successfully", 200
        except Exception as e:
            conn.rollback()
            print(f"Error adding schedule: {e}")
            return f"Error adding schedule: {str(e)}", 500
        finally:
            conn.close()
    else:
        return "Unauthorized", 401

# ---------------- DELETE SCHEDULE ----------------
@app.route('/delete_schedule', methods=['POST'])
def delete_schedule():
    if 'role' in session and session['role'] == 'Admin':
        schedule_id = request.form['schedule_id']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        try:
            # First delete related seat availability
            c.execute("DELETE FROM seat_availability WHERE schedule_id = ?", (schedule_id,))
            # Then delete the schedule
            c.execute("DELETE FROM movie_schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return "Schedule deleted successfully", 200
        except Exception as e:
            conn.rollback()
            print(f"Error deleting schedule: {e}")
            return f"Error deleting schedule: {str(e)}", 500
        finally:
            conn.close()
    else:
        return "Unauthorized", 401

# ---------------- GET SCHEDULES FOR BOOKING ----------------
# ---------------- GET SCHEDULES FOR BOOKING ----------------
@app.route('/get_schedules_for_booking')
def get_schedules_for_booking():
    movie_title = request.args.get('movie_title')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
        SELECT id, show_date, showtime, available_seats 
        FROM movie_schedules 
        WHERE movie_title = ? AND is_active = 1 
        ORDER BY show_date, showtime
    """, (movie_title,))

    schedules = c.fetchall()
    conn.close()

    schedule_list = []
    for schedule in schedules:
        schedule_list.append({
            'id': schedule[0],
            'show_date': schedule[1],
            'showtime': schedule[2],
            'available_seats': schedule[3]
        })

    return jsonify({'schedules': schedule_list})

# ---------------- GET MOVIE SCHEDULES ----------------
@app.route('/get_movie_schedules')
def get_movie_schedules():
    movie_id = request.args.get('movie_id')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
        SELECT id, show_date, showtime, total_seats, available_seats
        FROM movie_schedules 
        WHERE movie_id = ? AND is_active = 1 
        ORDER BY show_date, showtime
    """, (movie_id,))

    schedules = c.fetchall()
    conn.close()

    schedule_list = []
    for schedule in schedules:
        schedule_list.append({
            'id': schedule[0],
            'show_date': schedule[1],
            'showtime': schedule[2],
            'total_seats': schedule[3],
            'available_seats': schedule[4]
        })

    return jsonify(schedule_list)

# ---------------- GET MOVIE SCHEDULES BY TITLE ----------------
@app.route('/get_movie_schedules_by_title')
def get_movie_schedules_by_title():
    movie_title = request.args.get('title')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
        SELECT ms.show_date, ms.showtime 
        FROM movie_schedules ms
        JOIN movies m ON ms.movie_id = m.id
        WHERE m.title = ? AND ms.is_active = 1 
        ORDER BY ms.show_date, ms.showtime
    """, (movie_title,))

    schedules = c.fetchall()
    conn.close()

    schedule_list = []
    for schedule in schedules:
        schedule_list.append({
            'show_date': schedule[0],
            'showtime': schedule[1]
        })

    return jsonify({'schedules': schedule_list})

# ---------------- SEAT MANAGEMENT ROUTES ----------------
@app.route('/get_seat_configuration')
def get_seat_configuration():
    schedule_id = request.args.get('schedule_id')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get schedule details
    c.execute('''SELECT movie_title, show_date, showtime, total_seats, available_seats 
                 FROM movie_schedules 
                 WHERE id = ?''', (schedule_id,))
    schedule = c.fetchone()

    if schedule:
        movie_title, show_date, showtime, total_seats, available_seats = schedule

        # Get seat layout from seat_availability
        c.execute('''SELECT GROUP_CONCAT(seat_number) 
                     FROM seat_availability 
                     WHERE schedule_id = ? 
                     ORDER BY seat_number''', (schedule_id,))
        seat_data = c.fetchone()
        seat_layout = seat_data[0] if seat_data[0] else ''

        result = {
            'movie_title': movie_title,
            'show_date': show_date,
            'showtime': showtime,
            'total_seats': total_seats,
            'available_seats': available_seats,
            'seat_layout': seat_layout
        }
    else:
        result = {}

    conn.close()
    return jsonify(result)

@app.route('/update_seat_configuration', methods=['POST'])
def update_seat_configuration():
    if 'role' in session and session['role'] == 'Admin':
        schedule_id = request.form['schedule_id']
        total_seats = int(request.form['total_seats'])
        available_seats = int(request.form['available_seats'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        try:
            # Update schedule seat counts
            c.execute('''UPDATE movie_schedules 
                         SET total_seats = ?, available_seats = ? 
                         WHERE id = ?''',
                      (total_seats, available_seats, schedule_id))

            conn.commit()
            return "Seat configuration updated successfully", 200
        except Exception as e:
            conn.rollback()
            print(f"Error updating seat configuration: {e}")
            return f"Error updating seat configuration: {str(e)}", 500
        finally:
            conn.close()
    else:
        return "Unauthorized", 401

@app.route('/save_seat_configuration', methods=['POST'])
def save_seat_configuration():
    if 'role' in session and session['role'] == 'Admin':
        schedule_id = request.form['schedule_id']
        total_seats = int(request.form['total_seats'])
        available_seats = int(request.form['available_seats'])
        seat_layout = request.form['seat_layout']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        try:
            # Update schedule seat counts
            c.execute('''UPDATE movie_schedules 
                         SET total_seats = ?, available_seats = ? 
                         WHERE id = ?''',
                      (total_seats, available_seats, schedule_id))

            # Clear existing seats for this schedule
            c.execute("DELETE FROM seat_availability WHERE schedule_id = ?", (schedule_id,))

            # Add new seats based on layout
            if seat_layout:
                seats = [seat.strip() for seat in seat_layout.split(',')]
                for seat in seats:
                    c.execute('''INSERT INTO seat_availability 
                                (schedule_id, movie_title, show_date, showtime, seat_number, is_available) 
                                VALUES (?, ?, ?, ?, ?, ?)''',
                              (schedule_id, "Movie", "2024-01-01", "00:00", seat, 1))

            conn.commit()
            return "Seat configuration saved successfully", 200
        except Exception as e:
            conn.rollback()
            print(f"Error saving seat configuration: {e}")
            return f"Error saving seat configuration: {str(e)}", 500
        finally:
            conn.close()
    else:
        return "Unauthorized", 401

# ---------------- CUSTOMER DASHBOARD ----------------
@app.route('/customer')
def customer_dashboard():
    if 'role' in session and session['role'] == 'Customer':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, title, rating, poster_url FROM movies WHERE is_active = 1")
        movies = c.fetchall()
        conn.close()

        movie_list = []
        for movie in movies:
            movie_list.append({
                'id': movie[0],
                'title': movie[1],
                'rating': movie[2],
                'poster_url': movie[3]
            })

        return render_template('index.html', movies=movie_list)
    else:
        return redirect(url_for('login'))

# ---------------- MOVIES PAGE ----------------
@app.route('/movies')
def movies():
    if 'role' in session:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, title, genre, duration, rating, description, poster_url FROM movies WHERE is_active = 1")
        movies_data = c.fetchall()
        conn.close()

        movie_list = []
        for movie in movies_data:
            movie_list.append({
                'id': movie[0],
                'title': movie[1],
                'genre': movie[2],
                'duration': movie[3],
                'rating': movie[4],
                'description': movie[5],
                'poster_url': movie[6]
            })

        return render_template('movies.html', movies=movie_list)
    else:
        return redirect(url_for('login'))

# ---------------- GET MOVIES API ----------------
@app.route('/get_movies')
def get_movies():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, title, genre, duration, rating, description, poster_url FROM movies WHERE is_active = 1")
    movies = c.fetchall()
    conn.close()

    movie_list = []
    for movie in movies:
        movie_list.append({
            'id': movie[0],
            'title': movie[1],
            'genre': movie[2],
            'duration': movie[3],
            'rating': movie[4],
            'description': movie[5],
            'poster_url': movie[6]
        })

    return jsonify(movie_list)

# ---------------- BOOK TICKET ----------------
@app.route('/book_ticket', methods=['GET', 'POST'])
def book_ticket():
    if 'role' in session and session['role'] == 'Customer':
        if request.method == 'POST':
            movie = request.form['movie']
            showtime = request.form['showtime']
            seats = request.form['seats']
            fee = request.form.get('fee', 0)
            show_date = request.form.get('show_date', 'N/A')

            # Generate booking reference
            booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            conn = sqlite3.connect('database.db')
            c = conn.cursor()

            try:
                # Get schedule ID
                c.execute("SELECT id FROM movie_schedules WHERE movie_title = ? AND show_date = ? AND showtime = ?",
                          (movie, show_date, showtime))
                schedule_data = c.fetchone()
                if not schedule_data:
                    return "Schedule not found", 404
                schedule_id = schedule_data[0]

                # Insert booking
                c.execute(
                    "INSERT INTO tbl_booking (u_id, movie_name, show_date, showtime, seat_no, booking_fee, payment_status, booking_reference) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (session['user_id'], movie, show_date, showtime, seats, fee, 'Paid', booking_ref))

                # Get the booking ID
                booking_id = c.lastrowid

                # Update seat availability in movie_schedules
                seat_list = [seat.strip() for seat in seats.split(',')]
                num_seats_booked = len(seat_list)

                c.execute('''UPDATE movie_schedules 
                            SET available_seats = available_seats - ? 
                            WHERE id = ?''',
                          (num_seats_booked, schedule_id))

                # Mark seats as unavailable in seat_availability table
                for seat in seat_list:
                    c.execute('''UPDATE seat_availability 
                                SET is_available = 0, booking_id = ?
                                WHERE schedule_id = ? AND seat_number = ?''',
                              (booking_id, schedule_id, seat))

                conn.commit()
                conn.close()

                return redirect(url_for('print_ticket', booking_id=booking_id))
            except Exception as e:
                conn.rollback()
                conn.close()
                return f"Error booking ticket: {str(e)}", 500

        # GET request - show the booking form
        return render_template('buyticket.html')
    else:
        return redirect(url_for('login'))


# ---------------- CANCEL TICKET WITH SEAT SELECTION ----------------
@app.route('/cancel_ticket/<int:ticket_id>', methods=['POST'])
def cancel_ticket(ticket_id):
    if 'role' in session and session['role'] == 'Customer':
        seats_to_cancel = request.form.get('seats_to_cancel', '')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        try:
            # Get booking details including all seats
            c.execute("""
                SELECT movie_name, show_date, showtime, seat_no 
                FROM tbl_booking 
                WHERE b_id = ? AND u_id = ?
            """, (ticket_id, session['user_id']))

            ticket = c.fetchone()
            if ticket:
                movie_name, show_date, showtime, all_seats = ticket

                if seats_to_cancel:
                    # Partial cancellation - cancel only selected seats
                    seats_to_cancel_list = [seat.strip() for seat in seats_to_cancel.split(',')]
                    remaining_seats_list = [seat.strip() for seat in all_seats.split(',') if
                                            seat.strip() not in seats_to_cancel_list]

                    if remaining_seats_list:
                        # Update the booking with remaining seats
                        remaining_seats = ', '.join(remaining_seats_list)
                        c.execute("""
                            UPDATE tbl_booking 
                            SET seat_no = ?, booking_fee = ? 
                            WHERE b_id = ? AND u_id = ?
                        """, (remaining_seats, len(remaining_seats_list) * 125, ticket_id, session['user_id']))
                    else:
                        # All seats cancelled - delete the booking
                        c.execute("DELETE FROM tbl_booking WHERE b_id = ? AND u_id = ?",
                                  (ticket_id, session['user_id']))

                    # Restore cancelled seats to available
                    for seat in seats_to_cancel_list:
                        c.execute('''UPDATE seat_availability 
                                    SET is_available = 1, booking_id = NULL
                                    WHERE movie_title = ? AND show_date = ? AND showtime = ? AND seat_number = ?''',
                                  (movie_name, show_date, showtime, seat))

                    # Update available seats count in movie_schedules
                    c.execute('''UPDATE movie_schedules 
                                SET available_seats = available_seats + ? 
                                WHERE movie_title = ? AND show_date = ? AND showtime = ?''',
                              (len(seats_to_cancel_list), movie_name, show_date, showtime))

                    conn.commit()
                    conn.close()

                    if remaining_seats_list:
                        return redirect(url_for('viewtickets'))
                    else:
                        return redirect(url_for('cancel_success',
                                                movie=movie_name,
                                                date=show_date,
                                                time=showtime,
                                                seats=seats_to_cancel))
                else:
                    # Full cancellation (if no seats specified)
                    seat_list = [seat.strip() for seat in all_seats.split(',')]
                    num_seats_cancelled = len(seat_list)

                    # Restore all seats to available
                    for seat in seat_list:
                        c.execute('''UPDATE seat_availability 
                                    SET is_available = 1, booking_id = NULL
                                    WHERE movie_title = ? AND show_date = ? AND showtime = ? AND seat_number = ?''',
                                  (movie_name, show_date, showtime, seat))

                    # Update available seats count
                    c.execute('''UPDATE movie_schedules 
                                SET available_seats = available_seats + ? 
                                WHERE movie_title = ? AND show_date = ? AND showtime = ?''',
                              (num_seats_cancelled, movie_name, show_date, showtime))

                    # Delete the booking
                    c.execute("DELETE FROM tbl_booking WHERE b_id = ? AND u_id = ?",
                              (ticket_id, session['user_id']))

                    conn.commit()
                    conn.close()

                    return redirect(url_for('cancel_success',
                                            movie=movie_name,
                                            date=show_date,
                                            time=showtime,
                                            seats=all_seats))
            else:
                conn.close()
                return redirect(url_for('viewtickets'))
        except Exception as e:
            conn.rollback()
            conn.close()
            return f"Error cancelling ticket: {str(e)}", 500
    else:
        return redirect(url_for('login'))

# ---------------- CANCELLATION SUCCESS ----------------
@app.route('/cancel_success')
def cancel_success():
    movie = request.args.get('movie', 'Unknown Movie')
    date = request.args.get('date', 'N/A')
    time = request.args.get('time', 'N/A')
    seats = request.args.get('seats', 'N/A')
    return render_template('cancel_success.html', movie=movie, date=date, time=time, seats=seats)

# ---------------- GET AVAILABLE SEATS ----------------
@app.route('/get_available_seats')
def get_available_seats():
    schedule_id = request.args.get('schedule_id')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''SELECT seat_number FROM seat_availability 
                WHERE schedule_id = ? AND is_available = 1''',
              (schedule_id,))

    available_seats = [row[0] for row in c.fetchall()]
    conn.close()

    return {'available_seats': available_seats}

# ---------------- PRINT TICKET ----------------
@app.route('/print_ticket/<int:booking_id>')
def print_ticket(booking_id):
    if 'user_id' in session:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
            SELECT b.*, u.u_name, u.u_email 
            FROM tbl_booking b 
            JOIN user_table u ON b.u_id = u.u_id 
            WHERE b.b_id = ? AND b.u_id = ?
        """, (booking_id, session['user_id']))
        booking = c.fetchone()
        conn.close()

        if booking:
            booking_data = {
                'id': booking[0],
                'movie': booking[2],
                'date': booking[3],
                'time': booking[4],
                'seats': booking[5],
                'fee': booking[6],
                'status': booking[7],
                'booking_date': booking[8],
                'payment_status': booking[9],
                'reference': booking[10],
                'user_name': booking[11],
                'user_email': booking[12]
            }
            return render_template('print_ticket.html', booking=booking_data)

    return redirect(url_for('viewtickets'))

# ---------------- THANK YOU ----------------
@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

# ---------------- VIEW TICKETS ----------------
@app.route('/viewtickets')
def viewtickets():
    if 'role' in session and session['role'] == 'Customer':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
            SELECT b_id, movie_name, show_date, showtime, seat_no, booking_fee, status 
            FROM tbl_booking 
            WHERE u_id = ? 
            ORDER BY booking_date DESC
        """, (session['user_id'],))
        tickets = c.fetchall()
        conn.close()
        return render_template('viewtickets.html', tickets=tickets)
    else:
        return redirect(url_for('login'))

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ---------------- ERROR HANDLER ----------------
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# ---------------- MAIN ----------------
if __name__ == '__main__':
    print("🎬 Movie Ticket Booking System Starting...")
    print("📍 Server running at: http://localhost:5000")
    print("👤 No pre-existing users - Register first!")
    app.run(debug=True, port=5000)