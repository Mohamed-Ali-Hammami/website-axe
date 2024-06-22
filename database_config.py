from flask import  flash
import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


user_admin_association = db.Table('user_admin_association',
    db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), primary_key=True),
    db.Column('admin_id', db.Integer, db.ForeignKey('admin_users.admin_id'), primary_key=True)
)

class SuperUser(db.Model):
    __tablename__ = 'superusers'
    superuser_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    admins = db.relationship('AdminUser', secondary=user_admin_association, backref='users')

    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_id', backref='sender', cascade='all, delete-orphan')
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.recipient_id', backref='recipient', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User {self.username}>"

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f"<AdminUser {self.username}>"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp())
    status = db.Column(db.String(250), default='pending')
    estimation_time = db.Column(db.DateTime)  # Correctly defined as DateTime

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"

    def serialize(self):
        return {
            'transaction_id': self.transaction_id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'amount': float(self.amount),
            'transaction_type': self.transaction_type,
            'transaction_date': self.transaction_date.isoformat(),
            'status': self.status,
            'estimation_time': self.estimation_time.isoformat() if self.estimation_time else None,
        }

    def update_estimation_time(self, new_estimation_time):
        if isinstance(new_estimation_time, (int, float)):
            new_estimation_time = datetime.fromtimestamp(new_estimation_time / 1000.0)  # Convert timestamp to datetime if necessary

        self.estimation_time = new_estimation_time
        db.session.commit()

    def update_status(self, new_status):
        self.status = new_status
        db.session.commit()


def create_transaction(sender_id, recipient_id, amount, transaction_type):
    transaction_date = datetime.utcnow()
    transaction_id = str(uuid.uuid4())
    transaction = Transaction(
        transaction_id=transaction_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        amount=amount,
        transaction_type=transaction_type
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction

def get_all_users_with_transactions():
    users = User.query.all()
    users_data = []
    for user in users:
        user_transactions = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'transactions': []
        }
        transactions = Transaction.query.filter(
            (Transaction.sender_id == user.user_id) | (Transaction.recipient_id == user.user_id)
        ).all()
        for transaction in transactions:
            user_transactions['transactions'].append({
                'transaction_id': transaction.transaction_id,
                'sender_id': transaction.sender_id,
                'recipient_id': transaction.recipient_id,
                'amount': float(transaction.amount),
                'transaction_type': transaction.transaction_type,
                'transaction_date': transaction.transaction_date.isoformat(),
                'status': transaction.status
            })
        users_data.append(user_transactions)
    return users_data

def save_user_to_db(username, email, password_hash):
    user = User(username=username, email=email, password_hash=password_hash)
    try:
        db.session.add(user)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving user to database: {e}")
        return False

def get_pending_transactions(user_id):
    pending_transactions = Transaction.query.filter_by(sender_id=user_id, status='pending').all()
    return pending_transactions

def get_confirmed_transactions(user_id):
    confirmed_transactions = Transaction.query.filter(
        (Transaction.sender_id == user_id) & (Transaction.status.like('%T%'))
    ).all()
    return confirmed_transactions

def get_rejected_transactions(user_id):
    rejected_transactions = Transaction.query.filter_by(sender_id=user_id, status='rejected').all()
    return rejected_transactions


def confirm_pending_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if transaction and transaction.status == 'pending':
        transaction.status = 'confirmed'
        db.session.commit()
        return True
    else:
        return False

def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            flash('User not found.', 'error')
            return False

        # Delete all related transactions (sent and received)
        Transaction.query.filter(
            (Transaction.sender_id == user_id) | (Transaction.recipient_id == user_id)
        ).delete()

        # Now delete the user
        db.session.delete(user)
        db.session.commit()

        flash(f'User {user.username} deleted successfully.', 'success')
        return True

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return False

def create_superuser(username, email, password):
    password_hash = generate_password_hash(password)
    superuser = SuperUser(username=username, email=email, password_hash=password_hash)
    try:
        db.session.add(superuser)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating superuser: {e}")
        return False

def create_admin_user(username, email, password):
    password_hash = generate_password_hash(password)
    admin_user = AdminUser(username=username, email=email, password_hash=password_hash)
    try:
        db.session.add(admin_user)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating admin user: {e}")
        return False
def get_unassigned_users():
    unassigned_users = User.query.outerjoin(user_admin_association).filter(user_admin_association.c.admin_id == None).all()
    return unassigned_users
