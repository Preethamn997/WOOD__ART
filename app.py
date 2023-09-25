from flask import Flask, render_template, request, flash, redirect, url_for, session, send_from_directory, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
import stripe
import bleach
import bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email
from datetime import timedelta
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

app = Flask(__name__, static_url_path='/static')
# csrf = CSRFProtect(app)
app.secret_key = "123"
stripe.api_key = 'sk_test_51NgQuDSFWaBWl4suxeSpzmVVZHXPhJKr8oWBPq298xPCBaNnX3Ltiyqg6sGZwjxg39acW3dpossLG6eiV5nrSoum00F82l97z9'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Session expires after 1 day
app.config['UPLOAD_FOLDER'] = 'static'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

YOUR_DOMAIN = "http://localhost:5000"

# Create the customer table if it doesn't exist
con = sqlite3.connect("database.db")
con.execute("""
    CREATE TABLE IF NOT EXISTS customer (
        pid INTEGER PRIMARY KEY,
        name TEXT,
        address1 TEXT,
        address2 TEXT,
        city TEXT,
        pincode TEXT,
        state TEXT,
        contact TEXT,
        mail TEXT UNIQUE,
        password TEXT
    )
""")
con.close()

con_cart = sqlite3.connect("cart.db")
con_cart.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        product_id INTEGER,
        title TEXT,
        category TEXT,
        quantity INTEGER,
        price REAL,
        image_path TEXT
    )
""")
con_cart.close()


# Create the admin login table if it doesn't exist
con_admin = sqlite3.connect("admin_login.db")
con_admin.execute("CREATE TABLE IF NOT EXISTS admin_login(pid INTEGER PRIMARY KEY, email TEXT, password TEXT)")
con_admin.close()

# Create the product details table if it doesn't exist
con_products = sqlite3.connect("products.db")
con_products.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, title TEXT, price REAL, description TEXT, category TEXT, image_path TEXT)")
con_products.close()

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


@app.route('/')
def home():
    products = [
        {'name': 'SOFA', 'image': 'homepics/sofa.jpg'},
        {'name': 'COT', 'image': 'homepics/cot.jpg'},
        {'name': 'DINING', 'image': 'homepics/dining.jpg'},
        {'name': 'INTERIOR', 'image': 'homepics/interior.jpg'},
        {'name': 'SOFA CUM BED', 'image': 'homepics/sofacumbed.jpg'},
        {'name': 'KITCHEN INTERIOR', 'image': 'homepics/kitchen_interior1.jpg'},
        {'name': 'BOOK RACK', 'image' : 'homepics/book_rack.jpg'},
        {'name': 'BOSS CHAIR', 'image' : 'homepics/boss_chair.jpg'},
        {'name': 'CENTER TABLE', 'image' : 'homepics/center_table.jpg'}
        # Add more product listings here
    ]
    
    user_email = None
    logout_button_text = None
    logout_button_url = None
    user_profile = None

    if 'user_id' in session:
        user_email = session['email']
        logout_button_text = 'Logout'
        logout_button_url = url_for('logout')

        # Fetch the user profile data from the session
        user_profile = session.get('user_profile')

    return render_template('home.html', products=products, user_email=user_email, logout_button_text=logout_button_text, logout_button_url=logout_button_url, user_profile=user_profile)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
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
            if password == user[9]:  
                # Password matches, set session variables
                session['user_id'] = user[0]
                session['email'] = user[8]  
                
                # Fetch the user profile data and store it in the session
                user_profile = get_user_profile(user[0])
                if user_profile:
                    session['user_profile'] = user_profile

                flash("Login Successful", "success")
                con.close()
                
                # Redirect back to the page where the login button was clicked previously
                return redirect(session.pop('next', url_for('home')))
        
        flash("Invalid email or password", "danger")
    
    return render_template('login.html', form=form)



# Flask route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = LoginForm()
    if request.method == 'POST':
        try:
            name = bleach.clean(request.form['name'])
            address1 = request.form['address1']
            address2 = request.form['address2']
            city = request.form['city']
            pincode = request.form['pincode']
            state = request.form['state']
            contact = request.form['contact']
            mail = request.form['mail']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if password != confirm_password:
                flash("Password and Confirm Password do not match", "danger")
                return redirect(url_for('register'))
            
            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute("INSERT INTO customer(name, address1, address2, city, pincode, state, contact, mail, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (name, address1, address2, city, pincode, state, contact, mail, password))
            con.commit()
            con.close()
            
            flash("Registration Successful", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists. Please choose a different email.", "danger")
        except sqlite3.Error:
            flash("Error in Registration", "danger")
    
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    # Clear session variables
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('user_profile', None)
    
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))



@app.route('/product')
def product_page():
    # Logic to fetch product details for the given name
    name = request.args.get('name')

    # Determine the folder based on the product name
    folder = os.path.join(app.static_folder, name.lower().replace(" ", "_"))

    # Retrieve all image files in the folder
    images = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

    con = sqlite3.connect("products.db")
    cur = con.cursor()

    product_info = []

    for image in images:
        separator = "\\"
        result = (name + separator + image).lower().replace(" ", "_") # Convert result to lowercase string
        # Retrieve product information from the database
        cur.execute("SELECT id, title, price, description FROM products WHERE image_path = ?", (result,))
        product_data = cur.fetchall()
        print("product_data", product_data)

        if product_data:
            # If a match is found, retrieve the title, price, and description
            id, title, price, description = product_data[0]

            # Add the product information to the list
            product_info.append({"image": f"{name.lower().replace(' ', '_')}/{image}", "title": title, "price": price, "description": description, "pid": id})

    # Close the connection
    con.close()

    # Fetch the user email and logout button text for rendering
    user_email = None
    logout_button_text = None

    if 'user_id' in session:
        user_email = session['email']
        logout_button_text = 'Logout'

    # Render the template with the combined list of images and product info
    return render_template('product.html', product_info=product_info, user_email=user_email, logout_button_text=logout_button_text)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        try:
            # Process form data
            title = request.form['title']
            price = request.form['price']
            description = request.form['description']
            category = request.form['category']
            image = request.files['image']

            # Save the product image and get the image path
            if image and allowed_file(image.filename):
                image_path = save_product_image(image, category)
            else:
                flash("Invalid file format. Please choose a valid image file.", "danger")
                return redirect(url_for('add_product'))

            con_products = sqlite3.connect("products.db")
            cur_products = con_products.cursor()
            cur_products.execute("INSERT INTO products(title, price, description, category, image_path) VALUES (?, ?, ?, ?, ?)",
                                 (title, price, description, category, image_path))
            con_products.commit()
            con_products.close()

            flash("Product added successfully", "success")
            # Stay on the same page after form submission
            return redirect(url_for('add_product'))
        except sqlite3.Error:
            flash("Error in adding product", "danger")

    return render_template('add_product.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_product_image(image, category):
    filename = secure_filename(image.filename)
    category_folder = os.path.join(app.config['UPLOAD_FOLDER'], category.lower().replace(" ", "_"))
    os.makedirs(category_folder, exist_ok=True)
    filepath = os.path.join(category_folder, filename)
    image.save(filepath)

    # Update the image path to include only the relative path
    image_path = os.path.join(category.lower().replace(" ", "_"), filename)
    return image_path




@app.route('/product_description.html')
def product_description():
    form = LoginForm()
    # Retrieve the product information from the URL parameters
    product_id = request.args.get('id')
    product_image = request.args.get('image')
    # Fetch the user email and logout button text for rendering
    user_email = None
    logout_button_text = None
    con = sqlite3.connect("products.db")
    cur = con.cursor()
    cur.execute("SELECT title, price, description FROM products WHERE id = ?", (product_id,))
    product = cur.fetchall()
    print("product_data", product)
    
    if product:
            # If a match is found, retrieve the title, price, and description
            title, price, description = product[0]

            # Add the product information to the list
            # product_info.append({ "title": title, "price": price, "description": description})
            
    

    # Close the connection
    con.close()

    user_email = None
    logout_button_text = None

    if 'user_id' in session:
        user_email = session['email']
        logout_button_text = 'Logout'

    return render_template('product_description.html',
                           user_email=user_email,
                           logout_button_text=logout_button_text,
                           title=title,
                           price=price,
                           description=description,
                           product_image=product_image,
                           form=form,
                           product_id=product_id)


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


@app.route('/edit_product', methods=['GET', 'POST'])
def edit_product():
    # Logic for editing a product
    # ...
    return render_template('edit_product.html')


@app.route('/contact_us')
def contact_us():
    # Logic for handling the contact us page
    # ...
    return render_template('contact_us.html')


@app.route('/feedback')
def feedback():
    # Logic for handling the feedback page
    # ...
    return render_template('feedback.html')


@app.route('/faq')
def faq():
    # Logic for handling the FAQ page
    # ...
    return render_template('faq.html')


def get_user_profile(user_id):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT name, address1, address2, city, pincode, state, contact, mail FROM customer WHERE pid = ?", (user_id,))
    user_profile = cur.fetchone()
    con.close()
    if user_profile:
        profile_keys = ["name", "address1", "address2", "city", "pincode", "state", "contact", "mail"]
        return dict(zip(profile_keys, user_profile))
    return None


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please login to view your profile.", "info")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_profile = get_user_profile(user_id)

    if user_profile:
        return render_template('profile.html', user=user_profile)
    else:
        flash("User profile not found", "danger")
        return redirect(url_for('home'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    # Check if the user is logged in
    if 'user_id' not in session:
        flash("Please login to update your profile.", "info")
        return redirect(url_for('login'))

    # Get the updated profile data from the form
    user_id = session['user_id']
    name = request.form['name']
    address1 = request.form['address1']
    address2 = request.form['address2']
    city = request.form['city']
    pincode = request.form['pincode']
    state = request.form['state']
    contact = request.form['contact']

    # Update the user profile data in the database
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("UPDATE customer SET name=?, address1=?, address2=?, city=?, pincode=?, state=?, contact=? WHERE pid=?",
                (name, address1, address2, city, pincode, state, contact, user_id))
    con.commit()
    con.close()

    # Update the session with the new name
    session['user_profile']['name'] = name

    flash("Profile updated successfully", "success")
    return redirect(url_for('profile'))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    form = LoginForm()
    # Check if the user is logged in
    if 'user_id' not in session:
        flash("Please login to add products to your cart.", "info")
        return redirect(url_for('login'))
    
    # Get product details from the form
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    print(product_id)
    print(quantity)
    print(request.form)
    
    # Validate product_id and quantity
    if not product_id or not quantity:
        flash("Invalid product details", "danger")
        print("product not added to the cart")
        return redirect(url_for('home'))
    
    # Convert product_id and quantity to integers
    try:
        product_id = int(product_id)
        quantity = int(quantity)
    except ValueError:
        flash("Invalid product details", "danger")
        return redirect(url_for('home'))
    
    # Get user ID from session
    user_id = session['user_id']
    
    # Retrieve product details from the products table based on the product_id
    con_products = sqlite3.connect("products.db")
    cur_products = con_products.cursor()
    cur_products.execute("SELECT title, category, price, image_path FROM products WHERE id = ?", (product_id,))
    product_data = cur_products.fetchone()
    con_products.close()
    
    if not product_data:
        flash("Product not found", "danger")
        return redirect(url_for('home'))
    
    title, category, price, image_path = product_data
    
    # Insert the product into the cart table
    con_cart = sqlite3.connect("cart.db")
    cur_cart = con_cart.cursor()
    cur_cart.execute("INSERT INTO cart (user_id, product_id, title, category, quantity, price,image_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (user_id, product_id, title, category, quantity, price, image_path))
    con_cart.commit()
    con_cart.close()
    
    flash("Product added to cart", "success")
    
    # Redirect back to the referring page (the page where the form was submitted)
    referring_page = request.headers.get('Referer')
    return redirect(referring_page)

@app.route('/check_availability', methods=['POST'])
def check_availability():
    geolocator = Nominatim(user_agent="geoapiExercises")
    # Get the ZIP code from the form data
    zip_code = request.form.get('zip_code')
    location = geolocator.geocode(zip_code)
    print("Zipcode:",zip_code)
    print("Details of the Zipcode:")
    print(location)

    # Implement your availability checking logic here
    # You can check the ZIP code against a database or other data source

    # For demonstration, we'll assume it's available if the ZIP code is not empty
    bangalore_coords = (12.971599, 77.594566)

    # Check if the location coordinates are within a certain radius of Bangalore
    if location:
        user_coords = (location.latitude, location.longitude)
        distance = geodesic(user_coords, bangalore_coords).kilometers
        print("Distance to Bangalore:", distance)
        
        # Set a maximum allowed distance (adjust as needed)
        max_distance_km = 50  # For example, within 50 km of Bangalore

        if distance <= max_distance_km:
            availability_message = "Available in bangalore"
        else:
            availability_message = "Not Available outside Bangalore"
    else:
        availability_message = "Not Available"

    return jsonify({'availability_message': availability_message})


@app.route('/cart')
def cart():
    form = LoginForm()
    user_email = session.get('email')

    if not user_email:
        flash("Please log in to view your cart", "info")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch products in the user's cart from the cart table
    con_cart = sqlite3.connect("cart.db")
    cur_cart = con_cart.cursor()
    cur_cart.execute("SELECT id, title, category, quantity, price, image_path FROM cart WHERE user_id = ?", (user_id,))
    cart_items = cur_cart.fetchall()
    con_cart.close()

    # Calculate total amount
    total_amount = sum(item[3] * item[4] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, user_email=user_email, total_amount=total_amount, form=form)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    # Check if the user is logged in
    if 'user_id' in session:
        user_id = session['user_id']
        
        # Delete the item from the cart table based on item_id and user_id
        con_cart = sqlite3.connect("cart.db")
        cur_cart = con_cart.cursor()
        cur_cart.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (item_id, user_id))
        con_cart.commit()
        con_cart.close()

        flash("Item removed from cart", "success")
    
    # Redirect back to the cart page
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    # Check if the user is logged in
    if 'user_id' in session:
        user_id = session['user_id']
        new_quantity = int(request.form.get('quantity', 1))  # Get the new quantity from the form
        
        # Update the quantity of the item in the cart table based on item_id and user_id
        con_cart = sqlite3.connect("cart.db")
        cur_cart = con_cart.cursor()
        cur_cart.execute("UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?", (new_quantity, item_id, user_id))
        con_cart.commit()
        con_cart.close()

        flash("Quantity updated in cart", "success")
    
    # Redirect back to the cart page
    return redirect(url_for('cart'))


def calculate_total_amount(cart_items):
    user_email = session.get('email')
    if user_email:
        user_id = session['user_id']

        # Fetch products in the user's cart from the cart table
        con_cart = sqlite3.connect("cart.db")
        cur_cart = con_cart.cursor()
        cur_cart.execute("SELECT id, title, category, quantity, price, image_path FROM cart WHERE user_id = ?", (user_id,))
        cart_items = cur_cart.fetchall()
        con_cart.close()

        # Calculate total amount
        total_amount = sum(item[3] * item[4] for item in cart_items)
        return total_amount

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        # Retrieve the cart items and total amount from the session
        cart_items = session.get('cart_items', [])
        total_amount = calculate_total_amount(cart_items)

        # Create a Stripe checkout session
        stripe_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'inr',  # Change to your desired currency
                        'unit_amount': int(total_amount * 100),  # Stripe requires amount in cents
                        'product_data': {
                            'name': 'Your Cart',
                              # Replace with an actual image URL
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/payment-success',  # Redirect URL after successful payment
            cancel_url=YOUR_DOMAIN + '/cart',  # Redirect URL if payment is canceled  # Redirect URL if payment is canceled
        )

        return jsonify({'sessionId': stripe_session.id, 'totalAmount': total_amount})

    except Exception as e:
        # Log any exceptions that occur
        print(f"Error creating checkout session: {str(e)}")
        return "Error creating checkout session", 400


@app.route('/payment-success')
def payment_success():
    # Clear the cart items from the session after successful payment
    session.pop('cart_items', None)

    flash("Payment successful. Thank you for your purchase!", "success")
    return redirect(url_for('home'))


@app.route('/payment-cancelled')
def payment_cancelled():
    flash("Payment cancelled.", "info")
    return redirect(url_for('cart'))


if __name__ == '__main__':
    app.run(debug=True)
