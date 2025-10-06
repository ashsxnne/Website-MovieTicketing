from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create user table
    c.execute('''CREATE TABLE IF NOT EXISTS user_table (
                    u_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    u_name TEXT,
                    u_email TEXT,
                    u_pass TEXT,
                    u_role TEXT,
                    u_status TEXT)''')

    # Create booking table
    c.execute('''CREATE TABLE IF NOT EXISTS tbl_booking (
                    b_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    u_id INTEGER,
                    movie_name TEXT,
                    showtime TEXT,
                    seat_no TEXT,
                    booking_fee REAL)''')

    conn.commit()
    conn.close()


# Initialize DB if not already done
init_db()


# Home route
@app.route('/')
def index():
    return render_template('index.html')


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO user_table (u_name, u_email, u_pass, u_role, u_status) VALUES (?, ?, ?, ?, ?)",
                  (name, email, password, role, 'Pending'))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM user_table WHERE u_email = ? AND u_pass = ?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['role'] = user[4]
            session['status'] = user[5]

            # Redirect based on role
            if session['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            return "Invalid credentials", 400
    return render_template('login.html')


# Admin Dashboard
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


# Customer Dashboard
@app.route('/customer')
def customer_dashboard():
    if 'role' in session and session['role'] == 'Customer':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tbl_booking WHERE u_id = ?", (session['user_id'],))
        bookings = c.fetchall()
        conn.close()
        return render_template('customer.html', bookings=bookings)
    else:
        return redirect(url_for('login'))


# Book Ticket
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
            return redirect(url_for('customer_dashboard'))

        return render_template('book_ticket.html')
    else:
        return redirect(url_for('login'))


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
