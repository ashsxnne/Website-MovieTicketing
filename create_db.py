import sqlite3
from werkzeug.security import generate_password_hash


def create_database():
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Create admin user
    admin_password = generate_password_hash('admin123')
    try:
        c.execute('''INSERT INTO user_table (u_name, u_email, u_pass, u_role) 
                     VALUES (?, ?, ?, ?)''',
                  ('Administrator', 'admin@moviebooking.com', admin_password, 'Admin'))
    except:
        pass  # Admin already exists

    # Create sample customer user
    customer_password = generate_password_hash('customer123')
    try:
        c.execute('''INSERT INTO user_table (u_name, u_email, u_pass, u_role) 
                     VALUES (?, ?, ?, ?)''',
                  ('John Customer', 'customer@moviebooking.com', customer_password, 'Customer'))
    except:
        pass  # Customer already exists

    # Insert sample movies
    sample_movies = [
        ('Sinners (2025)', 'Horror/Thriller', '2h 15m', 'R',
         'Twin brothers return home and face supernatural evil in 1932 Mississippi Delta.',
         '/static/2'),
        ('Harry Potter and the Prisoner of Azkaban (2004)', 'Fantasy/Adventure', '2h 22m', 'PG',
         'Harry Potter discovers that a dangerous prisoner has escaped from Azkaban.',
         '/static/2.p'),
        ('THE CONJURING: Last Rites', 'Horror', '2h 5m', 'PG',
         'Paranormal investigators Ed and Lorraine Warren face their most terrifying case.',
         '/static/3.j'),
        ('The Lord of the Rings: The Return of the King (2003)', 'Fantasy/Adventure', '3h 21m', 'PG-13',
         'The final battle for Middle-earth begins as Frodo journeys to destroy the One Ring.',
         '/static/4.'),
        ('Weapons', 'Horror/Anthology', '1h 58m', 'R-16',
         'An interconnected horror anthology exploring the human psyche.',
         '/static/5.j'),
        ('Alice in Wonderland', 'Fantasy/Adventure', '1h 48m', 'PG',
         'Alice returns to the whimsical world of Wonderland to face the Red Queen.',
         '/static/6.j')
    ]

    for movie in sample_movies:
        try:
            c.execute('''INSERT INTO movies (title, genre, duration, rating, description, poster_url) 
                         VALUES (?, ?, ?, ?, ?, ?)''', movie)
        except:
            pass  # Movie already exists

    conn.commit()
    conn.close()
    print("✅ Database and tables ready!")
    print("📊 Tables created: user_table, tbl_booking, movies")
    print("👤 Admin Login: admin@moviebooking.com / admin123")
    print("👤 Customer Login: customer@moviebooking.com / customer123")


if __name__ == '__main__':
    create_database()