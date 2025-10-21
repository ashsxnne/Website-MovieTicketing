from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------------- DATABASE SETUP ----------------
def init_db():
    if not os.path.exists('database.db'):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS user_table (
                        u_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        u_name TEXT,
                        u_email TEXT UNIQUE,
                        u_pass TEXT,
                        u_role TEXT,
                        u_status TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS tbl_booking (
                        b_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        u_id INTEGER,
                        movie_name TEXT,
                        showtime TEXT,
                        seat_no TEXT,
                        booking_fee REAL)''')

        conn.commit()
        conn.close()

init_db()

# ---------------- LANDING PAGE ----------------
@app.route('/')
def home():
    return render_template('logout.html')  # first page when visiting site

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match!")

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("""INSERT INTO user_table (u_name, u_email, u_pass, u_role, u_status)
                         VALUES (?, ?, ?, ?, ?)""",
                      (username, email, hashed_password, 'Customer', 'Active'))
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

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM user_table WHERE u_email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
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
@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'Admin':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM user_table")
        users = c.fetchall()
        conn.close()
        return render_template('admin.html', users=users)
    else:
        return redirect(url_for('login'))

# ---------------- CUSTOMER DASHBOARD ----------------
@app.route('/customer')
def customer_dashboard():
    if 'role' in session and session['role'] == 'Customer':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tbl_booking WHERE u_id = ?", (session['user_id'],))
        bookings = c.fetchall()
        conn.close()
        return render_template('index.html', bookings=bookings)
    else:
        return redirect(url_for('login'))

# ---------------- MOVIES PAGE ----------------
@app.route('/movies')
def movies():
    if 'role' in session:
        return render_template('movies.html')
    else:
        return redirect(url_for('login'))

# ---------------- BOOK TICKET ----------------
@app.route('/book_ticket', methods=['GET', 'POST'])
def book_ticket():
    if 'role' in session and session['role'] == 'Customer':
        if request.method == 'POST':
            movie = request.form['movie']
            showtime = request.form['showtime']
            seat = request.form['seat']
            fee = request.form['fee']

            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute(
                "INSERT INTO tbl_booking (u_id, movie_name, showtime, seat_no, booking_fee) VALUES (?, ?, ?, ?, ?)",
                (session['user_id'], movie, showtime, seat, fee))
            conn.commit()
            conn.close()

            return redirect(url_for('thankyou'))
        return render_template('buyticket.html')
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
        c.execute("SELECT * FROM tbl_booking WHERE u_id = ?", (session['user_id'],))
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
        c.execute("SELECT movie_name, showtime, seat_no FROM tbl_booking WHERE b_id = ? AND u_id = ?",
                  (ticket_id, session['user_id']))
        ticket = c.fetchone()
        if ticket:
            movie_name, showtime, seat_no = ticket
            c.execute("DELETE FROM tbl_booking WHERE b_id = ? AND u_id = ?",
                      (ticket_id, session['user_id']))
            conn.commit()
            conn.close()
            return redirect(url_for('cancel_success',
                                    movie=movie_name,
                                    date='N/A',  # you can remove this if not needed
                                    time=showtime,
                                    seats=seat_no))
        else:
            conn.close()
            return redirect(url_for('viewtickets'))
    else:
        return redirect(url_for('login'))

#--------------cancellation success-----------
@app.route('/cancel_success')
def cancel_success():
        movie = request.args.get('movie')
        date = request.args.get('date')
        time = request.args.get('time')
        seats = request.args.get('seats')
        return render_template('cancel_success.html', movie=movie, date=date, time=time, seats=seats)


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')


# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
