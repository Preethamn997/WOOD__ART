from flask import Flask, render_template, request, flash, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "123"

# Create the customer table if it doesn't exist
con = sqlite3.connect("database.db")
con.execute("CREATE TABLE IF NOT EXISTS customer(pid INTEGER PRIMARY KEY, name TEXT, address TEXT, contact TEXT, mail TEXT, password TEXT)")
con.close()

# Create the admin login table if it doesn't exist
con_admin = sqlite3.connect("admin_login.db")
con_admin.execute("CREATE TABLE IF NOT EXISTS admin_login(pid INTEGER PRIMARY KEY, email TEXT, password TEXT)")
con_admin.close()

@app.route('/')
def home():
    products = [
        {'name': 'SOFA', 'image': 'homepics/sofa.jpg'},
        {'name': 'COT', 'image': 'homepics/cot.jpg'},
        {'name': 'DINING', 'image': 'homepics/dining.jpg'},
        {'name': 'INTERIOR', 'image': 'homepics/interior.jpg'},
        {'name': 'SOFA CUM BED', 'image': 'homepics/sofacumbed.jpg'},
        {'name': 'KITCHEN INTERIOR', 'image': 'homepics/kitchen_interior1.jpg'},
        # Add more product listings here
    ]
    
    if 'user_id' in session:
        # User is logged in
        user_email = session['email']
        logout_button_text = 'Logout'
        logout_button_url = url_for('logout')
    else:
        # User is not logged in
        user_email = ''
        logout_button_text = ''
        logout_button_url = ''
    
    return render_template('home.html', products=products, user_email=user_email, logout_button_text=logout_button_text, logout_button_url=logout_button_url)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Process login form data
        email = request.form['email']
        password = request.form['password']
        
        con = sqlite3.connect("database.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM customer WHERE mail = ?", (email,))
        user = cur.fetchone()
        
        if user:
            # User exists, check password
            if password == user[5]:
                # Password matches, set session variables
                session['user_id'] = user[0]
                session['email'] = user[4]
                
                flash("Login Successful", "success")
                con.close()
                return redirect(url_for('home'))
        
        flash("Invalid email or password", "danger")
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form['name']
            address = request.form['address']
            contact = request.form['contact']
            mail = request.form['mail']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            if password != confirm_password:
                flash("Password and Confirm Password do not match", "danger")
                return redirect(url_for('register'))

            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute("INSERT INTO customer(name, address, contact, mail, password) VALUES (?, ?, ?, ?, ?)", (name, address, contact, mail, password))
            con.commit()
            con.close()
            
            flash("Registration Successful", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists. Please choose a different email.", "danger")
        except sqlite3.Error:
            flash("Error in Registration", "danger")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Clear session variables
    session.pop('user_id', None)
    session.pop('email', None)
    
    flash("Logged out successfully", "success")
    return redirect(url_for('home'))


@app.route('/product')
def product_page():
    # Logic to fetch product details for the given name
    name = request.args.get('name')

    # Determine the folder based on the product name
    folder = os.path.join(app.static_folder, name.lower().replace(" ", "_"))

    # Retrieve all image files in the folder
    images = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

    return render_template('product.html', images=images, product_name=name)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # Process login form data
        email = request.form['email']
        password = request.form['password']
        
        con_admin = sqlite3.connect("admin_login.db")
        cur_admin = con_admin.cursor()
        cur_admin.execute("SELECT * FROM admin_login WHERE email = ?", (email,))
        admin = cur_admin.fetchone()
        
        if admin:
            # Admin exists, check password
            if password == admin[2]:
                # Password matches, set session variables
                session['admin_id'] = admin[0]
                session['admin_email'] = admin[1]
                
                flash("Admin Login Successful", "success")
                con_admin.close()
                
                # Redirect to the admin dashboard
                return redirect(url_for('admin_dashboard'))  # Modify this line
    
        flash("Invalid email or password", "danger")
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if the admin is logged in
    if 'admin_id' in session:
        # Admin is logged in, render the admin dashboard template
        return render_template('admin_dashboard.html')
    else:
        # Admin is not logged in, redirect to the admin login page
        return redirect(url_for('admin_login'))
    
@app.route('/customer_details')
def customer_details():
    # Connect to the database
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    
    # Retrieve customer details from the database
    cur.execute("SELECT name, address, contact, mail FROM customer")
    customers = cur.fetchall()
    
    # Close the database connection
    con.close()
    
    # Render the customer_details.html template and pass the customers data
    return render_template('customer_details.html', customers=customers)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    # Logic for adding a product
    # ...
    return render_template('add_product.html')

@app.route('/edit_product', methods=['GET', 'POST'])
def edit_product():

    return render_template('edit_product.html')
 
@app.route('/contact_us')
def contact_us():
    # Logic for handling the contact us page
    # ...
    return render_template('contact_us.html')

@app.route('/feedback')
def feedback():

    return render_template('feedback.html')

@app.route('/faq')
def faq():
     return render_template('faq.html')


if __name__ == '__main__':
    app.run(debug=True)
