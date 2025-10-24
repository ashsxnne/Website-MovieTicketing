from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_2025_movie_booking'


# ---------------- DATABASE CLEANUP ----------------
def cleanup_duplicate_movies():
    """Remove duplicate movies from the database"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Find and remove duplicate movies
    c.execute('''
        DELETE FROM movies 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM movies 
            GROUP BY title, genre, duration
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Removed duplicate movies")


# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Users table
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
                    FOREIGN KEY (u_id) REFERENCES user_table (u_id))''')

    # Movies table with UNIQUE constraint
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
                    UNIQUE(title, genre, duration)  -- ADD THIS LINE
                )''')

    # Create admin user if not exists
    try:
        admin_password = generate_password_hash('admin123')
        c.execute('''INSERT OR IGNORE INTO user_table (u_name, u_email, u_pass, u_role) 
                     VALUES (?, ?, ?, ?)''',
                  ('Administrator', 'admin@moviebooking.com', admin_password, 'Admin'))
    except:
        pass

    # Create sample customer user if not exists
    try:
        customer_password = generate_password_hash('customer123')
        c.execute('''INSERT OR IGNORE INTO user_table (u_name, u_email, u_pass, u_role) 
                     VALUES (?, ?, ?, ?)''',
                  ('John Customer', 'customer@moviebooking.com', customer_password, 'Customer'))
    except:
        pass

    # Insert sample movies if not exist - USE INSERT OR IGNORE
    sample_movies = [
        ('Sinners (2025)', 'Horror/Thriller', '2h 15m', 'R',
         'Twin brothers return home and face supernatural evil in 1932 Mississippi Delta.',
         '/static/1.jpg'),
        ('Harry Potter and the Prisoner of Azkaban (2004)', 'Fantasy/Adventure', '2h 22m', 'PG',
         'Harry Potter discovers that a dangerous prisoner has escaped from Azkaban.',
         '/static/2.png'),
        ('THE CONJURING: Last Rites', 'Horror', '2h 5m', 'PG',
         'Paranormal investigators Ed and Lorraine Warren face their most terrifying case.',
         '/static/3.jpg'),
        ('The Lord of the Rings: The Return of the King (2003)', 'Fantasy/Adventure', '3h 21m', 'PG-13',
         'The final battle for Middle-earth begins as Frodo journeys to destroy the One Ring.',
         '/static/4.png'),
        ('Weapons', 'Horror/Anthology', '1h 58m', 'R-16',
         'An interconnected horror anthology exploring the human psyche.',
         '/static/5.jpg'),
        ('Alice in Wonderland', 'Fantasy/Adventure', '1h 48m', 'PG',
         'Alice returns to the whimsical world of Wonderland to face the Red Queen.',
         '/static/6.jpg')
    ]

    for movie in sample_movies:
        c.execute('''INSERT OR IGNORE INTO movies (title, genre, duration, rating, description, poster_url) 
                     VALUES (?, ?, ?, ?, ?, ?)''', movie)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# Initialize database and clean duplicates
init_db()
cleanup_duplicate_movies()  # Clean up any existing duplicates


# ---------------- ALL ROUTES ----------------

# ---------------- LANDING PAGE ----------------
@app.route('/')
@app.route('/home')
def home():
    return render_template('logout.html')


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
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'customer')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM user_table WHERE u_email = ?", (email,))
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
            return render_template('login.html', error="Invalid credentials!")

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
        c.execute("SELECT id, title, genre, duration FROM movies")
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
                'duration': movie[3]
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

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if movie already exists
        c.execute("SELECT id FROM movies WHERE title = ? AND genre = ? AND duration = ?",
                  (title, genre, duration))
        existing_movie = c.fetchone()

        if existing_movie:
            # Movie already exists, don't add duplicate
            conn.close()
            return redirect(url_for('admin_dashboard'))
        else:
            # Add new movie
            c.execute("INSERT INTO movies (title, genre, duration) VALUES (?, ?, ?)",
                      (title, genre, duration))
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


# ---------------- CUSTOMER DASHBOARD ----------------
@app.route('/customer')
def customer_dashboard():
    if 'role' in session and session['role'] == 'Customer':
        return render_template('index.html')
    else:
        return redirect(url_for('login'))


# ---------------- MOVIES PAGE ----------------
@app.route('/movies')
def movies():
    if 'role' in session:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM movies WHERE is_active = 1")
        movies_data = c.fetchall()
        conn.close()
        return render_template('movies.html', movies=movies_data)
    else:
        return redirect(url_for('login'))


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

            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute(
                "INSERT INTO tbl_booking (u_id, movie_name, show_date, showtime, seat_no, booking_fee) VALUES (?, ?, ?, ?, ?, ?)",
                (session['user_id'], movie, show_date, showtime, seats, fee))
            conn.commit()
            conn.close()

            return redirect(url_for('thankyou'))

        # GET request - show booking form
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM movies WHERE is_active = 1")
        movies_data = c.fetchall()
        conn.close()
        return render_template('buyticket.html', movies=movies_data)
    else:
        return redirect(url_for('login'))


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


# ---------------- CANCEL TICKET ----------------
@app.route('/cancel_ticket/<int:ticket_id>', methods=['POST'])
def cancel_ticket(ticket_id):
    if 'role' in session and session['role'] == 'Customer':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("""
            SELECT movie_name, show_date, showtime, seat_no 
            FROM tbl_booking 
            WHERE b_id = ? AND u_id = ?
        """, (ticket_id, session['user_id']))

        ticket = c.fetchone()
        if ticket:
            movie_name, show_date, showtime, seat_no = ticket

            c.execute("DELETE FROM tbl_booking WHERE b_id = ? AND u_id = ?",
                      (ticket_id, session['user_id']))
            conn.commit()
            conn.close()

            return redirect(url_for('cancel_success',
                                    movie=movie_name,
                                    date=show_date,
                                    time=showtime,
                                    seats=seat_no))
        else:
            conn.close()
            return redirect(url_for('viewtickets'))
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


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')


# ---------------- ERROR HANDLER ----------------
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# ---------------- MAIN ----------------
if __name__ == '__main__':
    print("🎬 Movie Ticket Booking System Starting...")
    print("📍 Server running at: http://localhost:5000")
    print("👤 Admin Login: admin@moviebooking.com / admin123")
    print("👤 Customer Login: customer@moviebooking.com / customer123")
    app.run(debug=True, port=5000)