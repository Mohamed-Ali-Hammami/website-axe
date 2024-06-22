from flask import Flask, flash, request, jsonify, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_CALLBACK_URL
from model import  train_linear_regression_model, predict_approval_time_for_transaction
from datetime import datetime, date
from auth0.authentication import GetToken, Users
import logging

from database_config import db, User, AdminUser, Transaction, SuperUser, get_pending_transactions, get_confirmed_transactions, create_transaction, confirm_pending_transaction, save_user_to_db, get_rejected_transactions, delete_user,get_unassigned_users

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
db.init_app(app)

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/superuser_register', methods=['GET', 'POST'])
def superuser_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_superuser = SuperUser(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_superuser)
        db.session.commit()
        flash('Superuser registration successful!', 'success')
        return redirect(url_for('superuser_login'))
    return render_template('superuser_register.html')

def is_superuser(email):
    return SuperUser.query.filter_by(email=email).first() is not None

@app.route('/assign_user_to_admin', methods=['POST'])
def assign_user_to_admin():
    user_id = request.form.get('user_id')
    admin_id = request.form.get('admin_id')

    if user_id and admin_id:
        user = User.query.get(user_id)
        admin = AdminUser.query.get(admin_id)

        if user and admin:
            user.admins.append(admin)
            db.session.commit()
            flash('User assigned to admin successfully', 'success')
        else:
            flash('User or admin not found', 'error')
    else:
        flash('Invalid user_id or admin_id', 'error')

    return redirect(url_for('superuser_dashboard'))

@app.route('/superuser_login', methods=['GET', 'POST'])
def superuser_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        superuser = SuperUser.query.filter_by(email=email).first()
        if superuser and check_password_hash(superuser.password_hash, password):
            session['superuser_email'] = email
            session['superuser_id'] = superuser.superuser_id
            return redirect(url_for('superuser_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('superuser_login.html')

@app.route('/superuser_dashboard')
def superuser_dashboard():
    if 'superuser_email' not in session or not is_superuser(session['superuser_email']):
        return jsonify({'error': 'Unauthorized access'}), 401
    admins = AdminUser.query.all()
    users = User.query.all()
    return render_template('superuser_dashboard.html', admins=admins, users=users)

@app.route('/unassigned_users')
def unassigned_users():
    if 'superuser_email' not in session or not is_superuser(session['superuser_email']):
        return jsonify({'error': 'Unauthorized access'}), 401
    unassigned_users = get_unassigned_users()
    users_list = [{'user_id': user.user_id, 'username': user.username, 'email': user.email} for user in unassigned_users]
    return jsonify(users_list)


@app.route('/superuser/add_admin', methods=['GET', 'POST'])
def add_admin():
    if 'superuser_email' not in session or not is_superuser(session['superuser_email']):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_admin = AdminUser(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_admin)
        db.session.commit()
        flash('Admin added successfully!', 'success')
        return redirect(url_for('superuser_dashboard'))
    
    return render_template('add_admin.html')

@app.route('/superuser/train_model', methods=['POST'])
def train_model_route():
    try:
        mse, rmse, r2, plot_data = train_linear_regression_model()
        if mse is None or rmse is None or r2 is None or plot_data is None:
            return jsonify({'error': 'Model training failed or no data available.'}), 500

        model_statistics = {'mse': mse, 'rmse': rmse, 'r2': r2}
        plot_data_encoded = {
            'distribution': plot_data,
            'actual_vs_predicted': plot_data
        }

        return jsonify({'model_statistics': model_statistics, 'plot_data': plot_data_encoded})

    except Exception as e:
        error_message = f"Error during model training: {str(e)}"
        print(f"Debugging: {error_message}")
        app.logger.error(error_message)
        return jsonify({'error': error_message}), 500
    
    
@app.route('/superuser/add_superuser', methods=['GET', 'POST'])
def add_superuser():
    if 'superuser_email' not in session or not is_superuser(session['superuser_email']):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_superuser = SuperUser(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_superuser)
        db.session.commit()
        flash('Superuser added successfully!', 'success')
        return redirect(url_for('superuser_dashboard'))
    
    return render_template('add_superuser.html')

@app.route('/superuser/delete_admin', methods=['POST'])
def delete_admin():
    if 'superuser_email' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    admin_id = request.form.get('admin_id')
    admin = AdminUser.query.get(admin_id)
    
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    db.session.delete(admin)
    db.session.commit()
    
    flash('Admin deleted successfully', 'success')
    return redirect(url_for('superuser_dashboard'))

@app.route('/superuser/delete_user', methods=['POST'])
def delete_user_route():
    if 'superuser_email' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    user_id = request.form.get('user_id')
    if delete_user(user_id):
        flash('User deleted successfully', 'success')
        return redirect(url_for('superuser_dashboard'))
    else:
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        admin = AdminUser.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['email'] = email
            session['user_id'] = user.user_id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        elif admin and check_password_hash(admin.password_hash, password):
            session['email'] = email
            session['username'] = admin.username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/auth0-login')
def auth0_login():
    return redirect(f"https://{AUTH0_DOMAIN}/authorize?response_type=code&client_id={AUTH0_CLIENT_ID}&redirect_uri={AUTH0_CALLBACK_URL}&scope=openid profile email")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Authorization code not provided'}), 400

    try:
        get_token = GetToken(AUTH0_DOMAIN, client_id=AUTH0_CLIENT_ID, client_secret=AUTH0_CLIENT_SECRET)
        token = get_token.authorization_code(code=code, redirect_uri=AUTH0_CALLBACK_URL)

        auth0_users = Users(AUTH0_DOMAIN)
        user_info = auth0_users.userinfo(token['access_token'])

        user_email = user_info['email']
        user_name = user_info['nickname']

        user = User.query.filter_by(email=user_email).first()
        if not user:
            new_user = User(username=user_name, email=user_email)
            db.session.add(new_user)
            db.session.commit()
            user = new_user

        session['jwt_token'] = token['access_token']
        session['user_info'] = user_info
        session['username'] = user.username
        session['user_id'] = user.user_id

        return redirect(url_for('dashboard'))

    except Exception as e:
        error_message = f"Error during Auth0 callback: {e}"
        app.logger.error(error_message)
        return jsonify({'error': 'Failed to handle Auth0 callback', 'details': error_message}), 500


def is_admin(username):
    admin = AdminUser.query.filter_by(username=username).first()
    return admin is not None
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' not in session or not is_admin(session['username']):
        return jsonify({'error': 'Unauthorized access'}), 401

    # Fetch the currently logged-in admin
    admin = AdminUser.query.filter_by(username=session['username']).first()

    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    usernames = session['username']
    # Fetch users associated with this admin and their transactions
    users_with_transactions = User.query.filter(User.admins.any(admin_id=admin.admin_id)).all()
    user_data = []

    for user in users_with_transactions:
        transactions = Transaction.query.filter(
            (Transaction.sender_id == user.user_id) | (Transaction.recipient_id == user.user_id)
        ).all()

        user_data.append({
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'transactions': [transaction.serialize() for transaction in transactions]
        })

    return render_template('admin_dashboard.html', users=user_data,usernames = usernames)


@app.route('/admin_users/<admin_id>')
def get_admin_users(admin_id):
    admin = AdminUser.query.get(admin_id)

    if not admin:
        return jsonify({'message': 'Admin not found.'}), 404

    admin_users = admin.users.all()
    users_data = []

    for user in admin_users:
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email
            # Add more user details as needed
        }
        users_data.append(user_data)

    return jsonify(users_data), 200

@app.route('/about_us')
def about():
    return render_template('about_us.html')

@app.route('/about_ai')
def about_ai():
    return render_template('about_ai.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_id = session['user_id']
    pending_transactions = get_pending_transactions(user_id)
    confirmed_transactions = get_confirmed_transactions(user_id)
    rejected_transactions = get_rejected_transactions(user_id)

    # Format transaction dates
    for transaction in pending_transactions:
        transaction.formatted_transaction_date = transaction.transaction_date.strftime('%Y-%m-%d %H:%M')
        # Example for estimation time formatting (adjust as per your model's output)
        transaction.formatted_estimation_time = transaction.estimation_time.strftime('%Y-%m-%d %H:%M') if transaction.estimation_time else None

    for transaction in confirmed_transactions:
        transaction.formatted_transaction_date = transaction.transaction_date.strftime('%Y-%m-%d %H:%M')
    
    for transaction in rejected_transactions:
        transaction.formatted_transaction_date = transaction.transaction_date.strftime('%Y-%m-%d %H:%M')

    return render_template('dashboard.html', username=username, transactions=pending_transactions, confirmed_transactions=confirmed_transactions,rejected_transactions=rejected_transactions)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if password:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        else:
            hashed_password = None  
        try:
            if save_user_to_db(username, email, hashed_password):
                flash('Registration successful!', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed. Please try again.', 'error')
        except Exception as e:
            error_message = f"Error during user registration: {e}"
            app.logger.error(error_message)
            flash('Registration failed. Please try again.', 'error')

    return render_template('register.html')

@app.route('/initiate_transaction', methods=['POST'])
def handle_create_transaction():
    sender_id = session.get('user_id')
    recipient = request.form['recipient']
    amount = request.form['amount']
    transaction_type = request.form['transaction-type']

    recipient_user = User.query.filter_by(username=recipient).first()
    if not recipient_user:
        flash('Destinataire introuvable.', 'error')
        return redirect(url_for('dashboard'))

    transaction = create_transaction(sender_id, recipient_user.user_id, amount, transaction_type)
    if transaction:
        predicted_approval_time = predict_approval_time_for_transaction(transaction)
        
        # Update the estimation_time in the transaction object
        transaction.update_estimation_time(predicted_approval_time)
        
        flash('Transaction créée avec succès!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Échec de la création de la transaction.', 'error')
        return redirect(url_for('dashboard'))
    
@app.route('/user_list')
def user_list():
    users = User.query.all()
    user_list = [{'user_id': user.user_id, 'username': user.username} for user in users]
    return jsonify({'users': user_list})

@app.route('/user_transactions/<int:user_id>')
def user_transactions(user_id):
    transactions = Transaction.query.filter(
        (Transaction.sender_id == user_id) | (Transaction.recipient_id == user_id)
    ).all()
    transaction_list = [{
        'transaction_id': transaction.transaction_id,
        'sender_id': transaction.sender_id,
        'recipient_id': transaction.recipient_id,
        'amount': float(transaction.amount),
        'transaction_type': transaction.transaction_type,
        'status': transaction.status,
        'transaction_date': transaction.transaction_date.isoformat()
    } for transaction in transactions]
    return jsonify({'transactions': transaction_list})

@app.route('/admin/transactions/approve', methods=['PUT'])
def approve_transaction():
    transaction_id = request.args.get('transaction_id')
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    if transaction.status != 'pending':
        return jsonify({'error': 'Transaction is not pending'}), 400

    transaction.update_status(datetime.now().isoformat())
    flash('Transaction approuvée avec succès.', 'success')
    return jsonify({'message': 'Transaction approved successfully'})

@app.route('/admin/transactions/reject', methods=['PUT'])
def reject_transaction():
    transaction_id = request.args.get('transaction_id')
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    if transaction.status != 'pending':
        return jsonify({'error': 'Transaction is not pending'}), 400

    transaction.status = 'rejected'
    db.session.commit()
    flash('Transaction rejetée.', 'error')
    return jsonify({'message': 'Transaction rejected successfully'})
@app.route('/initiate_trx')
def initiate_transaction_page():
    today = date.today()
    today_year = today.year
    today_month = today.month
    today_day = today.day

    username = session.get('username', 'Guest')
    return render_template('initiate_trx.html', today_year=today_year, today_month=today_month, today_day=today_day, username=username)

@app.route('/confirm_transaction', methods=['POST'])
def confirm_transaction():
    transaction_id = request.form['transaction_id']
    confirm_pending_transaction(transaction_id)
    return redirect(url_for('admin_dashboard'))

@app.route('/save_estimation', methods=['POST'])
def save_estimation():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    task_id = request.form['task_id']
    estimation_time = request.form['estimation_time']

    task = Transaction.query.get(task_id)
    if task:
        # Convert estimation_time to datetime if necessary
        if isinstance(estimation_time, (int, float)):
            estimation_time = datetime.fromtimestamp(estimation_time / 1000.0)

        task.estimation_time = estimation_time
        db.session.commit()

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
