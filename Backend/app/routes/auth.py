# app/routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime
import logging
import traceback

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth_v1', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        logger.info(">>> AUTH: Register endpoint reached")
        logger.info(f">>> Origin: {request.headers.get('Origin')}")
        logger.info(f">>> Method: {request.method}")
        
        if current_app.db is None:
            logger.error("Database is None")
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500
        
        logger.info(f"Request Content-Type: {request.content_type}")
        logger.info(f"Request Data (raw): {request.data}")
        
        logger.info(f">>> Body length: {request.content_length}")
        
        data = request.get_json(silent=True)
        logger.info(f">>> Parsed JSON data: {data}")
        
        # Validate required fields
        if not data or not all(k in data for k in ('username', 'email', 'password')):
            logger.warning("Missing required fields")
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Username, email, and password are required'
            }), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        phone = data.get('phone', '').strip()
        
        logger.info(f"Validating username: {username}")
        
        # Basic validation
        if len(username) < 3 or len(username) > 50:
            logger.warning(f"Invalid username length: {username}")
            return jsonify({
                'error': 'Invalid username',
                'message': 'Username must be between 3 and 50 characters'
            }), 400
        
        logger.info(f"Validating email: {email}")
        if '@' not in email or '.' not in email:
            logger.warning(f"Invalid email format: {email}")
            return jsonify({
                'error': 'Invalid email',
                'message': 'Please provide a valid email address'
            }), 400

        if phone:
            logger.info(f"Validating phone: {phone}")
            # Basic phone validation could go here, for now just storing it
            pass
        
        logger.info(f"Validating password")
        if len(password) < 6:
            logger.warning(f"Invalid password length")
            return jsonify({
                'error': 'Invalid password',
                'message': 'Password must be at least 6 characters'
            }), 400
        
        logger.info(f"Checking if user exists")
        # Check if user already exists
        existing_user = current_app.db.users.find_one({
            '$or': [
                {'username': username},
                {'email': email}
            ]
        })
        
        if existing_user:
            logger.warning(f"User already exists: {username} or {email}")
            return jsonify({
                'error': 'User already exists',
                'message': 'Username or email already registered'
            }), 409
        
        logger.info(f"Hashing password")
        # Hash password
        hashed_password = generate_password_hash(password)
        
        logger.info(f"Creating user in database")
        # Create user document
        now = datetime.utcnow()
        user_doc = {
            'username': username,
            'email': email,
            'phone': phone,
            'password_hash': hashed_password,
            'role': 'user',
            'created_at': now,
            'last_login': now,
            'is_active': True,
            'settings': {
                'theme': 'light',
                'language': 'en',
                'notifications': True
            }
        }
        
        result = current_app.db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        logger.info(f"Generating JWT token for user: {user_id}")
        # Create JWT token
        access_token = create_access_token(identity=user_id)
        
        logger.info(f"User registered successfully: {username}")
        
        return jsonify({
            'message': 'User registered successfully',
            'data': {
                'token': access_token,
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email
                }
            },
            'status': 'success'
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Registration failed',
            'message': f'An error occurred during registration: {str(e)}'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        logger.info("=== LOGIN REQUEST RECEIVED ===")
        
        if current_app.db is None:
            logger.error("Database is None")
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500
        
        data = request.get_json()
        logger.info(f"Login data received for user: {data.get('username') if data else 'None'}")
        
        # Validate required fields
        if not data or not all(k in data for k in ('username', 'password')):
            logger.warning("Missing required fields for login")
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Username and password are required'
            }), 400
        
        username = data['username'].strip()
        password = data['password']
        
        logger.info(f"Finding user: {username}")
        # Find user by username
        user = current_app.db.users.find_one({'username': username})
        
        if not user:
            logger.warning(f"User not found: {username}")
            return jsonify({
                'error': 'Invalid credentials',
                'message': 'Username or password is incorrect'
            }), 401
        
        logger.info(f"Checking password for user: {username}")
        # Check password
        if not check_password_hash(user['password_hash'], password):
            logger.warning(f"Invalid password for user: {username}")
            return jsonify({
                'error': 'Invalid credentials',
                'message': 'Username or password is incorrect'
            }), 401
        
        logger.info(f"Updating last_login for user: {username}")
        # Update last_login
        current_app.db.users.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        logger.info(f"Generating JWT token for user: {user['_id']}")
        # Create JWT token
        access_token = create_access_token(identity=str(user['_id']))
        
        logger.info(f"Login successful for user: {username}")
        
        return jsonify({
            'message': 'Login successful',
            'data': {
                'token': access_token,
                'user': {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email'],
                    'role': user.get('role', 'user'),
                    'created_at': str(user.get('created_at', '')),
                    'last_login': str(user.get('last_login', ''))
                }
            },
            'status': 'success'
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Login failed',
            'message': f'An error occurred during login: {str(e)}'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info (protected route)"""
    try:
        logger.info("=== GET CURRENT USER REQUEST RECEIVED ===")
        
        if current_app.db is None:
            logger.error("Database is None")
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500
        
        # Get user ID from JWT
        user_id = get_jwt_identity()
        logger.info(f"Getting user info for ID: {user_id}")
        
        # Find user in database
        user = current_app.db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return jsonify({
                'error': 'User not found',
                'message': 'User not found in database'
            }), 404
        
        logger.info(f"User found: {user['username']}")
        
        return jsonify({
            'message': 'User data retrieved successfully',
            'data': {
                'user': {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email'],
                    'role': user.get('role', 'user'),
                    'created_at': str(user.get('created_at', '')),
                    'last_login': str(user.get('last_login', ''))
                }
            },
            'status': 'success'
        }), 200
        
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Failed to retrieve user',
            'message': f'An error occurred: {str(e)}'
        }), 500
@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
        # Allowed fields for update
        allowed_fields = ['username', 'phone', 'bio']
        update_doc = {}
        
        for field in allowed_fields:
            if field in data:
                update_doc[field] = data[field]
                
        if not update_doc:
            return jsonify({'status': 'error', 'message': 'No valid fields for update'}), 400
            
        result = current_app.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_doc}
        )
        
        if result.matched_count == 0:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
        return jsonify({
            'status': 'success',
            'message': 'Profile updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not all(k in data for k in ('old_password', 'new_password')):
            return jsonify({
                'status': 'error', 
                'message': 'Old and new passwords are required'
            }), 400
            
        user = current_app.db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
        # Verify old password
        if not check_password_hash(user['password_hash'], data['old_password']):
            return jsonify({
                'status': 'error', 
                'message': 'Current password incorrect'
            }), 401
            
        # Hash new password
        new_hash = generate_password_hash(data['new_password'])
        
        current_app.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'password_hash': new_hash}}
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Google OAuth authentication endpoint"""
    try:
        logger.info(">>> Google OAuth endpoint reached")
        
        if current_app.db is None:
            logger.error("Database is None")
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500
        
        data = request.get_json()
        if not data or not data.get('credential'):
            return jsonify({
                'error': 'Missing credential',
                'message': 'Google credential token is required'
            }), 400
        
        # Verify Google token
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        import os
        
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                data['credential'],
                google_requests.Request(),
                os.getenv('GOOGLE_CLIENT_ID')
            )
            
            # Extract user information
            email = idinfo.get('email')
            name = idinfo.get('name', '')
            google_id = idinfo.get('sub')
            picture = idinfo.get('picture', '')
            
            if not email:
                return jsonify({
                    'error': 'Invalid token',
                    'message': 'Email not found in Google token'
                }), 400
            
            logger.info(f"Google auth successful for: {email}")
            
            # Check if user exists
            users_collection = current_app.db.users
            user = users_collection.find_one({'email': email.lower()})
            
            if user:
                # Update Google ID if not set
                if not user.get('google_id'):
                    users_collection.update_one(
                        {'_id': user['_id']},
                        {'$set': {'google_id': google_id, 'picture': picture}}
                    )
                logger.info(f"Existing user logged in: {email}")
            else:
                # Create new user
                username = email.split('@')[0]
                # Ensure unique username
                base_username = username
                counter = 1
                while users_collection.find_one({'username': username}):
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = {
                    'username': username,
                    'email': email.lower(),
                    'google_id': google_id,
                    'picture': picture,
                    'created_at': datetime.utcnow(),
                    'phone': '',
                    'bio': ''
                }
                result = users_collection.insert_one(user)
                user['_id'] = result.inserted_id
                logger.info(f"New user created via Google: {email}")
            
            # Generate JWT token
            access_token = create_access_token(identity=str(user['_id']))
            
            return jsonify({
                'status': 'success',
                'token': access_token,
                'user': {
                    'username': user['username'],
                    'email': user['email'],
                    'picture': user.get('picture', '')
                }
            }), 200
            
        except ValueError as e:
            logger.error(f"Invalid Google token: {str(e)}")
            return jsonify({
                'error': 'Invalid token',
                'message': 'Google token verification failed'
            }), 401
        
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500
