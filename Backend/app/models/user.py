# app/models/user.py
from datetime import datetime
from bson import ObjectId

class User:
    """User model for MongoDB"""
    
    @staticmethod
    def create_user_doc(username, email, password_hash):
        """Create a new user document"""
        return {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': 'user',
            'created_at': datetime.utcnow(),
            'last_login': None,
            'is_active': True,
            'settings': {
                'theme': 'light',
                'language': 'en',
                'notifications': True
            }
        }
    
    @staticmethod
    def find_by_username_or_email(db, username):
        """Find user by username or email"""
        return db.users.find_one({
            '$or': [
                {'username': username},
                {'email': username}
            ]
        })
    
    @staticmethod
    def find_by_id(db, user_id):
        """Find user by ID"""
        try:
            return db.users.find_one({
                '_id': ObjectId(user_id)
            })
        except:
            return None
    
    @staticmethod
    def find_by_email(db, email):
        """Find user by email"""
        return db.users.find_one({'email': email.lower()})
    
    @staticmethod
    def find_by_username(db, username):
        """Find user by username"""
        return db.users.find_one({'username': username})
    
    @staticmethod
    def create(db, username, email, password_hash):
        """Insert new user"""
        user_doc = User.create_user_doc(username, email, password_hash)
        result = db.users.insert_one(user_doc)
        return str(result.inserted_id)
    
    @staticmethod
    def update_last_login(db, user_id):
        """Update user's last login timestamp"""
        try:
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'last_login': datetime.utcnow()}}
            )
        except:
            pass
    
    @staticmethod
    def to_dict(user_doc):
        """Convert MongoDB document to dictionary"""
        return {
            'id': str(user_doc['_id']),
            'username': user_doc['username'],
            'email': user_doc['email'],
            'role': user_doc['role'],
            'created_at': user_doc['created_at'].isoformat(),
            'last_login': user_doc.get('last_login').isoformat() if user_doc.get('last_login') else None
        }
