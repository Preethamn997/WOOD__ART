from flask import Flask, render_template, request, flash, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "123"

# Create the customer table if it doesn't exist
con = sqlite3.connect("database.db")
con.execute("CREATE TABLE IF NOT EXISTS customer(pid INTEGER PRIMARY KEY, name TEXT, address TEXT, contact TEXT, mail TEXT, password TEXT)")
con.close()

@app.route('/')
def home():
    products = [
        {'name': 'SOFA', 'image': 'sofa.jpg'},
        {'name': 'COT', 'image': 'cot.jpg'},
        {'name': 'DINING Table', 'image': 'dining.jpg'},
        {'name': 'INTERIOR', 'image': 'interior.jpg'},
        {'name': 'SOFA CUM BED', 'image': 'sofacumbed.jpg'},
        {'name': 'Kitchen Interior', 'image':'kitchen_interior1.jpg'},
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


@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product_page(id):
    # Logic to fetch product details for the given ID
    # Render the product page template with the product data
    return render_template('product.html')

if __name__ == '__main__':
    app.run(debug=True)
