from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
import json
from ai_chatbot import AIEngine
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from products import PRODUCTS

app = Flask(__name__)

app.config['SECRET_KEY'] = 'mysecretkey1234'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sql.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

ai_engine = AIEngine()

# Product Model (Example for cart relationship)
class Product(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f"<Product {self.name} - Price: {self.price}>"

# Cart Model
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='cart_items', lazy=True)  # backref here in Cart model
    product = db.relationship('Product', backref='cart_items', lazy=True)

    def __repr__(self):
        return f"<Cart {self.user_id} - {self.product_id} - Quantity: {self.quantity}>"

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    profile_pic = db.Column(db.String(100))
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    password = db.Column(db.String(128), nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

# Order Model (Example of order relationship)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Added status column for order status

    def __repr__(self):
        return f"<Order {self.id} - User: {self.user_id} - Total: {self.total_amount}>"

# Routes
@app.route('/')
def ch():
    return render_template('ch.html')

@app.route('/chat', methods=['POST'])
def chat():
    if not request.is_json:
        return jsonify({"error": "Invalid input, expected JSON"}), 400
    
    user_message = request.json.get('message')
    session_id = request.json.get('session_id', 'default-session')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    response = ai_engine.generate_response(user_message, session_id)

    return jsonify({
        'response': response,
        'session_id': session_id
    })

@app.route('/pro.html')
def pro():
    return render_template('pro.html')

@app.route('/shop.html')
def shop():
    return render_template('shop.html')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/contact.html')
def contact():
    return render_template('contact.html')

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash("You need to log in first.", 'warning')
        return redirect(url_for('login'))
    
    # Fetch cart items from the database for the logged-in user
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()

    if not cart_items:
        return render_template('cart.html', cart=[], empty=True)

    cart_data = []
    for item in cart_items:
        product = item.product  # Get associated product
        cart_data.append({
            'name': product.name,
            'price': product.price,
            'quantity': item.quantity,
            'image': product.image_url  # Assuming products have an image URL
        })

    return render_template('cart.html', cart=cart_data)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart_route():
    if not request.is_json:
        return jsonify({"error": "Invalid input, expected JSON"}), 400

    product_data = request.json
    if not product_data.get('product_id') or not product_data.get('name') or not product_data.get('price'):
        return jsonify({"error": "Invalid product details"}), 400

    # Ensure user is logged in and session has a user_id
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 400

    # Check if the product exists in the database
    product_in_db = Product.query.filter_by(id=product_data['product_id']).first()
    if not product_in_db:
        return jsonify({"error": "Product not found in the database"}), 404

    # Check if the product is already in the user's cart
    existing_cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_data['product_id']).first()
    
    if existing_cart_item:
        existing_cart_item.quantity += 1  # Increment quantity if already in cart
        db.session.commit()
        return jsonify({"message": f"Product '{product_in_db.name}' updated in cart."})

    # Create a new cart item if not already in cart
    cart_item = Cart(user_id=user_id, product_id=product_data['product_id'], quantity=1)
    db.session.add(cart_item)
    db.session.commit()

    return jsonify({"message": f"Product '{product_in_db.name}' added to cart."})

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if user is not logged in
    
    user_id = session['user_id']  # Retrieve user_id from session
    cart = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart)  # Calculate total price from cart items
    
    if request.method == 'POST':
        # Create a new order based on the cart items and the total price
        order = Order(user_id=user_id, total_amount=total_price)
        db.session.add(order)
        db.session.commit()

        # Clear the cart after order is placed
        session['cart'] = []

        # Optionally, redirect to a confirmation or thank you page
        return redirect(url_for('thank_you', order_id=order.id))

    return render_template('checkout.html', cart=cart, total_price=total_price)

orders = []

@app.route('/orders')
def view_orders():
    return render_template('orders.html')  # Remove 'orders=orders'

@app.route('/get_orders')  # ✅ New route for fetching orders as JSON
def get_orders():
    return jsonify(orders)  # Return JSON data

@app.route('/place_order', methods=['POST'])
def place_order():
    global orders
    data = request.get_json()
    if data:
        # Add the current date when placing the order
        data['date'] = datetime.now().strftime('%Y-%m-%d')  # ✅ Adding today's date
        orders.append(data)
        return jsonify({"message": "Order placed successfully!"}), 200
    return jsonify({"error": "Invalid order data"}), 400

@app.route('/remove_order/<int:index>', methods=['DELETE'])
def remove_order(index):
    if 0 <= index < len(orders):
        orders.pop(index)
        return jsonify({"message": "Order removed successfully!"})
    return jsonify({"error": "Order not found"}), 404


@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("You need to log in first.", 'warning')
        return redirect(url_for('login'))

    # Using sessionmaker to avoid deprecated query.get method
    Session = sessionmaker(bind=db.engine)
    session_obj = Session()

    user = session_obj.get(User, session['user_id'])  # Fetch user based on session ID

    if user is None:
        flash("User not found. Please log in again.", 'danger')
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash("You need to log in first.", 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])  # Get the logged-in user
    if not user:
        flash("User not found. Please log in again.", 'danger')
        return redirect(url_for('login'))

    user.username = request.form['username']
    user.name = request.form['name']
    user.email = request.form['email']
    user.phone = request.form['phone']
    user.address = request.form['address']
    
    # Save changes to the database
    db.session.commit()

    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']  # Capture name field

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, name=name, password=hashed_password)  # Add name here
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Login successful!", 'success')
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password", 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/add_to_wishlist/<int:product_id>')
def add_to_wishlist(product_id):
    product = Product.query.get(product_id)
    if product:
        if 'wishlist' not in session:
            session['wishlist'] = []
        session['wishlist'].append({
            'name': product.name,
            'price': product.price,
            'image': product.image_url
        })
        flash(f"Product '{product.name}' added to your wishlist.", 'success')
    return redirect(url_for('wishlist'))

@app.route('/wishlist')
def wishlist():
    wishlist_items = session.get('wishlist', [])
    return render_template('wishlist.html', wishlist=wishlist_items)


if __name__ == "__main__":
    print("Starting the server...")  # This should print before the server starts
    app.run(debug=True)
