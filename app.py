from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache  
import pandas as pd  
from sklearn.feature_extraction.text import CountVectorizer  
from sklearn.metrics.pairwise import cosine_similarity
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  
import os
from PIL import Image
from flask_login import login_user, logout_user, login_manager, LoginManager
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

# MY db connection
local_server = True
app = Flask(__name__)
app.secret_key = 'harshithbhaskar'

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Change to your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bismarkasomani92@gmail.com'  # Your email
app.config['MAIL_PASSWORD'] = 'alpy nurb cccb xgrf kva6 jq6l qhme avry'  # Your app password

# Password reset token serializer
serializer = URLSafeTimedSerializer(app.secret_key)

# this is for getting unique user access
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
app.config['CACHE_TYPE'] = 'SimpleCache' 

db = SQLAlchemy(app)
cache = Cache(app)

# Database Models
class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class User(UserMixin, db.Model):  
    id = db.Column(db.Integer, primary_key=True)  
    username = db.Column(db.String(50), unique=True)  
    email = db.Column(db.String(50), unique=True)  
    phone = db.Column(db.String(20))  
    location = db.Column(db.String(50))  
    password = db.Column(db.String(1000))  
    is_supplier = db.Column(db.Boolean, default=False)  
    is_admin = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(1000), nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

class Addagroproducts(db.Model):
    username = db.Column(db.String(50))
    email = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    pid = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(100))
    productdesc = db.Column(db.String(300))
    price = db.Column(db.Integer)
    status = db.Column(db.String(20))
    recommend = db.Column(db.String(20))
    product_picture = db.Column(db.String(1000), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  
    supplier = db.relationship('User', backref=db.backref('addagroproducts'))

class Animal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    housing_per_unit = db.Column(db.Float, nullable=False)
    housing_unit = db.Column(db.String(50), nullable=False)
    feed_requirement = db.Column(db.Float, nullable=False)
    average_weight = db.Column(db.Float, nullable=False)
    recommended_feed = db.Column(db.String(200), nullable=False)
    vaccination_schedule = db.Column(db.String(200), nullable=False)
    cost_per_unit = db.Column(db.Float, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price_per_seedling = db.Column(db.Float, nullable=False)
    seedlings_per_hectare = db.Column(db.Float, nullable=False)
    planting_interval = db.Column(db.String(100))
    weedicides = db.Column(db.String(100))
    weedicides_notes = db.Column(db.String(1000))
    pesticides = db.Column(db.String(100))
    pesticides_notes = db.Column(db.String(1000))
    fertilizers = db.Column(db.String(100))
    fertilizers_notes = db.Column(db.String(1000))

class Complaint(db.Model):  
    id = db.Column(db.Integer, primary_key=True)  
    user_name = db.Column(db.String(100), nullable=False)  
    supplier_name = db.Column(db.String(100), nullable=False)  
    supplier_phone = db.Column(db.String(15), nullable=False)  
    product_name = db.Column(db.String(100), nullable=False)  
    product_id = db.Column(db.Integer, db.ForeignKey('addagroproducts.pid'), nullable=False)
    supplierRating = db.Column(db.String(5), nullable=False)
    complaint_text = db.Column(db.Text, nullable=False)

class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', backref=db.backref('forum_posts', lazy=True))

class Comment(db.Model):  
    id = db.Column(db.Integer, primary_key=True)  
    content = db.Column(db.Text, nullable=False)  
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  
    author = db.relationship('User', backref=db.backref('comments', lazy=True))  
    post = db.relationship('ForumPost', backref=db.backref('comments', lazy=True))


# Email sending function
def send_email(recipient, subject, body):
    """Send email function"""
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    

# create admin user if not exists
def create_admin_user():
    """Create default admin user"""
    admin_user = User.query.filter_by(email='admin@example.com').first()
    if not admin_user:
        try:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                phone='1234567890',
                location='Admin Location',
                password=generate_password_hash('adminpassword'),
                is_admin=True,
            )
            db.session.add(admin_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")

with app.app_context():
    db.create_all()
    create_admin_user()

# Admin Dashboard Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get statistics
    total_users = User.query.count()
    total_products = Addagroproducts.query.count()
    total_complaints = Complaint.query.count()
    total_forum_posts = ForumPost.query.count()
    
    stats = {
        'users': total_users,
        'products': total_products,
        'complaints': total_complaints,
        'forum_posts': total_forum_posts
    }
    
    return render_template('admin/dashboard.html', stats=stats)


# Flask Routes for Forum CRUD Operations

@app.route('/admin/forum_posts')
@login_required
def admin_forum():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    forums = ForumPost.query.order_by(ForumPost.timestamp.desc()).all()
    users = User.query.all()  # For dropdown in create/edit forms
    return render_template('admin/forum.html', forums=forums, users=users)

@app.route('/admin/forum_posts/create', methods=['POST'])
@login_required
def admin_forum_create():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        author_id = request.form.get('author_id')
        
        if not title or not content or not author_id:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        forum_post = ForumPost(
            title=title,
            content=content,
            author_id=author_id
        )
        
        db.session.add(forum_post)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Forum post created successfully',
            'post': {
                'id': forum_post.id,
                'title': forum_post.title,
                'content': forum_post.content,
                'author_name': forum_post.author.username,
                'timestamp': forum_post.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/forum_posts/<int:post_id>/edit', methods=['GET'])
@login_required
def admin_forum_get(post_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    forum_post = ForumPost.query.get_or_404(post_id)
    return jsonify({
        'success': True,
        'post': {
            'id': forum_post.id,
            'title': forum_post.title,
            'content': forum_post.content,
            'author_id': forum_post.author_id,
            'author_name': forum_post.author.username,
            'timestamp': forum_post.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
    })

@app.route('/admin/forum_posts/<int:post_id>/edit', methods=['POST'])
@login_required
def admin_forum_edit(post_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        forum_post = ForumPost.query.get_or_404(post_id)
        
        title = request.form.get('title')
        content = request.form.get('content')
        author_id = request.form.get('author_id')
        
        if not title or not content or not author_id:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        forum_post.title = title
        forum_post.content = content
        forum_post.author_id = author_id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Forum post updated successfully',
            'post': {
                'id': forum_post.id,
                'title': forum_post.title,
                'content': forum_post.content,
                'author_name': forum_post.author.username,
                'timestamp': forum_post.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/forum_posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_forum_delete(post_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        forum_post = ForumPost.query.get_or_404(post_id)
        db.session.delete(forum_post)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Forum post deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Flask Routes for Comments CRUD Operations

@app.route('/admin/comments')
@login_required
def admin_comments():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    comments = Comment.query.order_by(Comment.timestamp.desc()).all()
    users = User.query.all()  # For dropdown in create/edit forms
    forum_posts = ForumPost.query.all()  # For dropdown in create/edit forms
    return render_template('admin/comments.html', comments=comments, users=users, forum_posts=forum_posts)

@app.route('/admin/comments/create', methods=['POST'])
@login_required
def admin_comments_create():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        content = request.form.get('content')
        author_id = request.form.get('author_id')
        post_id = request.form.get('post_id')
        
        if not content or not author_id or not post_id:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        comment = Comment(
            content=content,
            author_id=author_id,
            post_id=post_id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Comment created successfully',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.username,
                'post_title': comment.post.title,
                'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/comments/<int:comment_id>/edit', methods=['GET'])
@login_required
def admin_comments_get(comment_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    comment = Comment.query.get_or_404(comment_id)
    return jsonify({
        'success': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author_id': comment.author_id,
            'author_name': comment.author.username,
            'post_id': comment.post_id,
            'post_title': comment.post.title,
            'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
    })

@app.route('/admin/comments/<int:comment_id>/edit', methods=['POST'])
@login_required
def admin_comments_edit(comment_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        content = request.form.get('content')
        author_id = request.form.get('author_id')
        post_id = request.form.get('post_id')
        
        if not content or not author_id or not post_id:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        comment.content = content
        comment.author_id = author_id
        comment.post_id = post_id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment updated successfully',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.username,
                'post_title': comment.post.title,
                'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def admin_comments_delete(comment_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        comment = Comment.query.get_or_404(comment_id)
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

#Admin Crop Management Routes
@app.route('/admin/add_crops')
@login_required
def admin_add_crops():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    crops = Product.query.all()
    return render_template('admin/add_crops.html', crops=crops)

@app.route('/admin/crops/create', methods=['POST'])
@login_required
def admin_create_crop():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    price_per_seedling = float(request.form.get('price_per_seedling'))
    seedlings_per_hectare = float(request.form.get('seedlings_per_hectare'))
    planting_interval = request.form.get('planting_interval')
    weedicides = request.form.get('weedicides')
    weedicides_notes = request.form.get('weedicides_notes')
    pesticides = request.form.get('pesticides')
    pesticides_notes = request.form.get('pesticides_notes')
    fertilizers = request.form.get('fertilizers')
    fertilizers_notes = request.form.get('fertilizers_notes')
    
    # Check if crop name already exists
    existing_crop = Product.query.filter_by(name=name).first()
    if existing_crop:
        flash('Crop name already exists', 'danger')
        return redirect(url_for('admin_add_crops'))
    
    new_crop = Product(
        name=name,
        price_per_seedling=price_per_seedling,
        seedlings_per_hectare=seedlings_per_hectare,
        planting_interval=planting_interval,
        weedicides=weedicides,
        weedicides_notes=weedicides_notes,
        pesticides=pesticides,
        pesticides_notes=pesticides_notes,
        fertilizers=fertilizers,
        fertilizers_notes=fertilizers_notes
    )
    
    db.session.add(new_crop)
    db.session.commit()
    flash('Crop created successfully', 'success')
    return redirect(url_for('admin_add_crops'))

@app.route('/admin/crops/edit/<int:crop_id>', methods=['POST'])
@login_required
def admin_edit_crop(crop_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    crop = Product.query.get_or_404(crop_id)
    
    # Check if new name conflicts with existing crop (excluding current crop)
    name = request.form.get('name')
    existing_crop = Product.query.filter(Product.name == name, Product.id != crop_id).first()
    if existing_crop:
        flash('Crop name already exists', 'danger')
        return redirect(url_for('admin_add_crops'))
    
    crop.name = name
    crop.price_per_seedling = float(request.form.get('price_per_seedling'))
    crop.seedlings_per_hectare = float(request.form.get('seedlings_per_hectare'))
    crop.planting_interval = request.form.get('planting_interval')
    crop.weedicides = request.form.get('weedicides')
    crop.weedicides_notes = request.form.get('weedicides_notes')
    crop.pesticides = request.form.get('pesticides')
    crop.pesticides_notes = request.form.get('pesticides_notes')
    crop.fertilizers = request.form.get('fertilizers')
    crop.fertilizers_notes = request.form.get('fertilizers_notes')
    
    db.session.commit()
    flash('Crop updated successfully', 'success')
    return redirect(url_for('admin_add_crops'))

@app.route('/admin/crops/delete/<int:crop_id>')
@login_required
def admin_delete_crop(crop_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    crop = Product.query.get_or_404(crop_id)
    
    db.session.delete(crop)
    db.session.commit()
    flash('Crop deleted successfully', 'success')
    return redirect(url_for('admin_add_crops'))


# Flask Routes for Livestock CRUD Operations

@app.route('/admin/add_livestock')
@login_required
def admin_add_livestock():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    animals = Animal.query.order_by(Animal.name.asc()).all()
    return render_template('admin/add_livestock.html', animals=animals)

@app.route('/admin/livestock/create', methods=['POST'])
@login_required
def admin_livestock_create():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        name = request.form.get('name')
        housing_per_unit = request.form.get('housing_per_unit')
        housing_unit = request.form.get('housing_unit')
        feed_requirement = request.form.get('feed_requirement')
        average_weight = request.form.get('average_weight')
        recommended_feed = request.form.get('recommended_feed')
        vaccination_schedule = request.form.get('vaccination_schedule')
        cost_per_unit = request.form.get('cost_per_unit')
        
        # Validate required fields
        if not all([name, housing_per_unit, housing_unit, feed_requirement, 
                   average_weight, recommended_feed, vaccination_schedule, cost_per_unit]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Convert numeric fields
        try:
            housing_per_unit = float(housing_per_unit)
            feed_requirement = float(feed_requirement)
            average_weight = float(average_weight)
            cost_per_unit = float(cost_per_unit)
        except ValueError:
            return jsonify({'success': False, 'message': 'Please enter valid numeric values'}), 400
        
        # Check if animal name already exists
        existing_animal = Animal.query.filter_by(name=name).first()
        if existing_animal:
            return jsonify({'success': False, 'message': 'An animal with this name already exists'}), 400
        
        animal = Animal(
            name=name,
            housing_per_unit=housing_per_unit,
            housing_unit=housing_unit,
            feed_requirement=feed_requirement,
            average_weight=average_weight,
            recommended_feed=recommended_feed,
            vaccination_schedule=vaccination_schedule,
            cost_per_unit=cost_per_unit
        )
        
        db.session.add(animal)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Livestock added successfully',
            'animal': {
                'id': animal.id,
                'name': animal.name,
                'housing_per_unit': animal.housing_per_unit,
                'housing_unit': animal.housing_unit,
                'feed_requirement': animal.feed_requirement,
                'average_weight': animal.average_weight,
                'recommended_feed': animal.recommended_feed,
                'vaccination_schedule': animal.vaccination_schedule,
                'cost_per_unit': animal.cost_per_unit
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/livestock/<int:animal_id>/edit', methods=['GET'])
@login_required
def admin_livestock_get(animal_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    animal = Animal.query.get_or_404(animal_id)
    return jsonify({
        'success': True,
        'animal': {
            'id': animal.id,
            'name': animal.name,
            'housing_per_unit': animal.housing_per_unit,
            'housing_unit': animal.housing_unit,
            'feed_requirement': animal.feed_requirement,
            'average_weight': animal.average_weight,
            'recommended_feed': animal.recommended_feed,
            'vaccination_schedule': animal.vaccination_schedule,
            'cost_per_unit': animal.cost_per_unit
        }
    })

@app.route('/admin/livestock/<int:animal_id>/edit', methods=['POST'])
@login_required
def admin_livestock_edit(animal_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        animal = Animal.query.get_or_404(animal_id)
        
        name = request.form.get('name')
        housing_per_unit = request.form.get('housing_per_unit')
        housing_unit = request.form.get('housing_unit')
        feed_requirement = request.form.get('feed_requirement')
        average_weight = request.form.get('average_weight')
        recommended_feed = request.form.get('recommended_feed')
        vaccination_schedule = request.form.get('vaccination_schedule')
        cost_per_unit = request.form.get('cost_per_unit')
        
        # Validate required fields
        if not all([name, housing_per_unit, housing_unit, feed_requirement, 
                   average_weight, recommended_feed, vaccination_schedule, cost_per_unit]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Convert numeric fields
        try:
            housing_per_unit = float(housing_per_unit)
            feed_requirement = float(feed_requirement)
            average_weight = float(average_weight)
            cost_per_unit = float(cost_per_unit)
        except ValueError:
            return jsonify({'success': False, 'message': 'Please enter valid numeric values'}), 400
        
        # Check if animal name already exists (excluding current animal)
        existing_animal = Animal.query.filter(Animal.name == name, Animal.id != animal_id).first()
        if existing_animal:
            return jsonify({'success': False, 'message': 'An animal with this name already exists'}), 400
        
        # Update animal fields
        animal.name = name
        animal.housing_per_unit = housing_per_unit
        animal.housing_unit = housing_unit
        animal.feed_requirement = feed_requirement
        animal.average_weight = average_weight
        animal.recommended_feed = recommended_feed
        animal.vaccination_schedule = vaccination_schedule
        animal.cost_per_unit = cost_per_unit
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Livestock updated successfully',
            'animal': {
                'id': animal.id,
                'name': animal.name,
                'housing_per_unit': animal.housing_per_unit,
                'housing_unit': animal.housing_unit,
                'feed_requirement': animal.feed_requirement,
                'average_weight': animal.average_weight,
                'recommended_feed': animal.recommended_feed,
                'vaccination_schedule': animal.vaccination_schedule,
                'cost_per_unit': animal.cost_per_unit
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/livestock/<int:animal_id>/delete', methods=['POST'])
@login_required
def admin_livestock_delete(animal_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        animal = Animal.query.get_or_404(animal_id)
        animal_name = animal.name  # Store name for response message
        db.session.delete(animal)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Livestock "{animal_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Admin User Management Routes
@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        location = request.form.get('location')
        password = request.form.get('password')
        is_supplier = request.form.get('is_supplier') == 'on'
        is_admin = request.form.get('is_admin') == 'on'
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists', 'danger')
            return render_template('admin/create_user.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            location=location,
            password=hashed_password,
            is_supplier=is_supplier,
            is_admin=is_admin
        )
        
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/create_user.html')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.location = request.form.get('location')
        user.is_supplier = request.form.get('is_supplier') == 'on'
        user.is_admin = request.form.get('is_admin') == 'on'
        
        password = request.form.get('password')
        if password:
            user.password = generate_password_hash(password)
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Don't allow deletion of the current admin user
    if user.id == current_user.id:
        flash('Cannot delete your own account', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))


#Admin Products management
@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    products = Addagroproducts.query.join(User).all()
    users = User.query.filter_by(is_supplier=True).all()  # Get all suppliers
    return render_template('admin/products.html', products=products, users=users)

@app.route('/admin/products/delete/<int:product_id>')
@login_required
def admin_delete_product(product_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    product = Addagroproducts.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/create', methods=['POST'])
@login_required
def admin_create_product():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    productname = request.form.get('productname')
    price = request.form.get('price')
    status = request.form.get('status', 'available')
    supplier_id = request.form.get('supplier_id')
    email = request.form.get('email')
    phone = request.form.get('phone')
    productdesc = request.form.get('productdesc')
    product_picture = request.form.get('product_picture')
    recommend = 'yes' if request.form.get('recommend') == 'on' else 'no'
    
    # Get supplier details
    supplier = User.query.get(supplier_id)
    username = supplier.username if supplier else ''
    
    new_product = Addagroproducts(
        productname=productname,
        price=int(price),
        status=status,
        supplier_id=supplier_id,
        username=username,
        email=email or (supplier.email if supplier else ''),
        phone=phone or (supplier.phone if supplier else ''),
        productdesc=productdesc,
        product_picture=product_picture,
        recommend=recommend
    )
    
    db.session.add(new_product)
    db.session.commit()
    flash('Product created successfully', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/edit/<int:product_id>', methods=['POST'])
@login_required
def admin_edit_product(product_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    product = Addagroproducts.query.get_or_404(product_id)
    
    product.productname = request.form.get('productname')
    product.price = int(request.form.get('price'))
    product.status = request.form.get('status')
    product.supplier_id = request.form.get('supplier_id')
    product.email = request.form.get('email')
    product.phone = request.form.get('phone')
    product.productdesc = request.form.get('productdesc')
    product.product_picture = request.form.get('product_picture')
    product.recommend = 'yes' if request.form.get('recommend') == 'on' else 'no'
    
    # Update supplier username
    supplier = User.query.get(product.supplier_id)
    product.username = supplier.username if supplier else ''
    
    db.session.commit()
    flash('Product updated successfully', 'success')
    return redirect(url_for('admin_products'))

# Admin Complaint Management Routes
@app.route('/admin/complaints')
@login_required
def admin_complaints():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    complaints = Complaint.query.all()
    products = Addagroproducts.query.all()  # For the product dropdown
    return render_template('admin/complaints.html', complaints=complaints, products=products)

@app.route('/admin/complaints/create', methods=['POST'])
@login_required
def admin_create_complaint():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user_name = request.form.get('user_name')
    supplier_name = request.form.get('supplier_name')
    supplier_phone = request.form.get('supplier_phone')
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    supplier_rating = request.form.get('supplierRating')
    complaint_text = request.form.get('complaint_text')
    
    # Validate that the product exists
    product = Addagroproducts.query.get(product_id)
    if not product:
        flash('Selected product does not exist', 'danger')
        return redirect(url_for('admin_complaints'))
    
    new_complaint = Complaint(
        user_name=user_name,
        supplier_name=supplier_name,
        supplier_phone=supplier_phone,
        product_id=int(product_id),
        product_name=product_name,
        supplierRating=supplier_rating,
        complaint_text=complaint_text
    )
    
    db.session.add(new_complaint)
    db.session.commit()
    flash('Complaint created successfully', 'success')
    return redirect(url_for('admin_complaints'))

@app.route('/admin/complaints/edit/<int:complaint_id>', methods=['POST'])
@login_required
def admin_edit_complaint(complaint_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    user_name = request.form.get('user_name')
    supplier_name = request.form.get('supplier_name')
    supplier_phone = request.form.get('supplier_phone')
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    supplier_rating = request.form.get('supplierRating')
    complaint_text = request.form.get('complaint_text')
    
    # Validate that the product exists
    product = Addagroproducts.query.get(product_id)
    if not product:
        flash('Selected product does not exist', 'danger')
        return redirect(url_for('admin_complaints'))
    
    complaint.user_name = user_name
    complaint.supplier_name = supplier_name
    complaint.supplier_phone = supplier_phone
    complaint.product_id = int(product_id)
    complaint.product_name = product_name
    complaint.supplierRating = supplier_rating
    complaint.complaint_text = complaint_text
    
    db.session.commit()
    flash('Complaint updated successfully', 'success')
    return redirect(url_for('admin_complaints'))

@app.route('/admin/complaints/delete/<int:complaint_id>')
@login_required
def admin_delete_complaint(complaint_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    db.session.delete(complaint)
    db.session.commit()
    flash('Complaint deleted successfully', 'success')
    return redirect(url_for('admin_complaints'))

# Optional: API endpoint to get product details for auto-fill
@app.route('/api/products/<int:product_id>')
@login_required
def get_product_details(product_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product = Addagroproducts.query.get_or_404(product_id)
    return jsonify({
        'pid': product.pid,
        'productname': product.productname,
        'supplier_name': product.supplier.username if product.supplier else product.username,
        'supplier_phone': product.supplier.phone if product.supplier else product.phone
    })

# Password Reset Routes
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = serializer.dumps(email, salt='password-reset-salt')
            
            # Store token in database with expiry
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email
            reset_url = url_for('reset_password', token=token, _external=True)
            html_body = f'''
            <h2>Password Reset Request</h2>
            <p>Hello {user.username},</p>
            <p>You have requested to reset your password. Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you did not request this reset, please ignore this email.</p>
            '''
            
            if send_email(email, 'Password Reset Request', html_body):
                flash('Password reset link has been sent to your email', 'success')
            else:
                flash('Error sending email. Please try again.', 'danger')
        else:
            flash('Email not found', 'danger')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('/auth/forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verify token
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
        user = User.query.filter_by(email=email).first()
        
        if not user or user.reset_token != token:
            flash('Invalid or expired token', 'danger')
            return redirect(url_for('login'))
        
        if user.reset_token_expiry < datetime.utcnow():
            flash('Token has expired', 'danger')
            return redirect(url_for('forgot_password'))
        
        if request.method == 'POST':
            new_password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('auth/reset_password.html', token=token)
            
            # Update password and clear reset token
            user.password = generate_password_hash(new_password)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            
            flash('Password has been reset successfully', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/reset_password.html', token=token)
        
    except SignatureExpired:
        flash('Token has expired', 'danger')
        return redirect(url_for('forgot_password'))
    except BadTimeSignature:
        flash('Invalid token', 'danger')
        return redirect(url_for('login'))

# Index page route
@app.route('/')
def index(): 
    return render_template('index.html')

# this route display all products from the database and display them
@app.route('/agroproducts')
@login_required
def agroproducts():
    query = Addagroproducts.query.join(User, Addagroproducts.supplier_id == User.id)
    
    if current_user.is_authenticated:
        user_location = current_user.location
        # Order by matching location first, then other locations
        # Using SQLAlchemy case function through db object
        query = query.order_by(
            db.case(
                (User.location == user_location, 0),
                else_=1
            ).asc(),
            Addagroproducts.productname.asc()  # Secondary sort by product name
        )
    else:
        # For non-logged in users, just order by product name
        query = query.order_by(Addagroproducts.productname.asc())
    
    return render_template('agroproducts.html', query=query.all())
# this route allow a supplier to add their products to the system.
@app.route('/addagroproducts', methods=['POST', 'GET'])
@login_required
def addagroproduct():
    if not current_user.is_supplier:
        flash('You are not authorized to add products.', 'danger')
        return render_template('addagroproducts.html')  # Stay on the same page
    
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        productname = request.form.get('productname')
        productdesc = request.form.get('productdesc')
        price = request.form.get('price')
        
        product_picture_path = None
        product_picture = request.files.get('product_picture')
        
        if product_picture:
            if not product_picture.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                flash("Only JPG and PNG files are allowed.", "warning")
                return render_template('addagroproducts.html')
            
            uploads_dir = os.path.abspath("uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = secure_filename(product_picture.filename)
            product_picture_path = os.path.join(uploads_dir, filename)
            
            try:
                with Image.open(product_picture) as img:
                    img.thumbnail((800, 800))
                    img.save(product_picture_path)
            except Exception as e:
                print(f"An error occurred while saving the image: {e}")
                flash("An error occurred while uploading the image.", "danger")
                return render_template('addagroproducts.html')

        products = Addagroproducts(
            username=username,
            email=email,
            phone=phone,
            productname=productname,
            productdesc=productdesc,
            price=price,
            product_picture=filename,
            supplier_id=current_user.id
        )
        db.session.add(products)
        db.session.commit()
        flash("Product added successfully!", "success")
        return render_template('addagroproducts.html')  # Stay on the same page to show the flash message
    
    return render_template('addagroproducts.html')
# this rooute allow users to lodge complaints and compliment against suppli
@app.route('/complaint/<string:product_id>', methods=['GET', 'POST'])
@login_required
def complaint(product_id):
    product = Addagroproducts.query.get_or_404(product_id)
    if request.method == 'POST':
        user_name = request.form.get('username')
        supplier_name = request.form.get('supplier_name')
        supplier_phone = request.form.get('supplier_phone')
        product_name = request.form.get('product_name')
        supplierRating = request.form.get('supplierRating')
        complaint_text = request.form.get('complaint_text')

        new_complaint = Complaint(
            user_name=user_name,
            supplier_name=supplier_name,
            supplier_phone=supplier_phone,
            product_name=product_name,
            product_id=product.pid,
            supplierRating=supplierRating,
            complaint_text=complaint_text
        )

        db.session.add(new_complaint)
        db.session.commit()
        flash('Your complaint has been submitted successfully!', 'success')
        return render_template('complaint.html', product=product)  # Render complaint.html to show flash message

    return render_template('complaint.html', product=product)

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query')
    products = Addagroproducts.query.filter(Addagroproducts.productname.ilike(f'%{query}%')).all()
    return render_template('search.html', products=products)

# this route handle bill of material both crops and livestocks
@app.route("/bom", methods=["GET", "POST"])
@login_required
def bom():
    products = Product.query.all()
    animals = Animal.query.all()

    selected_product = None
    total_price = None
    total_seedlings = None
    hectares = None
    animal_type = None
    quantity = None
    animal_data = None
    housing_requirement = None
    feed_requirement = None
    vaccination_schedule = None
    total_cost = None

    if request.method == "POST":
        farming_type = request.form.get("farming_type", "crops")

        if farming_type == "livestock":
            animal_type_id = request.form.get("animal_type")
            try:
                quantity = int(request.form.get("quantity", 0))
                if quantity <= 0:
                    raise ValueError
            except ValueError:
                flash("Quantity must be a positive integer", "danger")
                return redirect(url_for('bom'))

            animal = Animal.query.filter_by(id=animal_type_id).first()
            if not animal:
                flash("Animal type not found", "danger")
                return redirect(url_for('bom'))

            # Calculate values
            housing_requirement = f"{quantity} animals need {quantity * animal.housing_per_unit} {animal.housing_unit}"
            feed_requirement = quantity * animal.feed_requirement
            vaccination_schedule = animal.vaccination_schedule
            total_cost = quantity * animal.cost_per_unit
            animal_type = animal.name

            # Create animal_data dictionary with ALL fields
            animal_data = {
                "name": animal.name,
                "average_weight": animal.average_weight,
                "recommended_feed": animal.recommended_feed,
                "housing_requirement": housing_requirement,
                "feed_requirement": feed_requirement,
                "vaccination_schedule": vaccination_schedule,
                "housing_per_unit": animal.housing_per_unit,
                "housing_unit": animal.housing_unit
            }

            return render_template("bom.html",
                products=products,
                animals=animals,
                farming_type=farming_type,
                animal_type=animal_type,
                quantity=quantity,
                animal_data=animal_data,
                housing_requirement=housing_requirement,
                feed_requirement=feed_requirement,
                vaccination_schedule=vaccination_schedule,
                total_cost=total_cost,
                total_price=None,
                total_seedlings=None,
                hectares=None,
                selected_product=None)
        else:
            try:
                hectares = float(request.form["hectares"])
                product_id = request.form["product"]
                selected_product = Product.query.get(product_id)

                if selected_product:
                    total_seedlings = hectares * selected_product.seedlings_per_hectare
                    total_price = total_seedlings * selected_product.price_per_seedling
            except (ValueError, TypeError):
                flash("Invalid input for hectares or product selection", "danger")
                return redirect(url_for('bom'))

            return render_template("bom.html",
                products=products,
                animals=animals,
                total_price=total_price,
                total_seedlings=total_seedlings,
                hectares=hectares,
                selected_product=selected_product,
                farming_type=farming_type,
                animal_type=None,
                quantity=None,
                animal_data=None,
                housing_requirement=None,
                feed_requirement=None,
                vaccination_schedule=None,
                total_cost=None)

    return render_template("bom.html",
        products=products,
        animals=animals,
        selected_product=None,
        animal_type=None,
        quantity=None,
        animal_data=None,
        housing_requirement=None,
        feed_requirement=None,
        vaccination_schedule=None,
        total_cost=None,
        farming_type='crops')
# this route handle image upload and save it into a folder uploads
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)
# This route handle user profile
@app.route('/profile')
@login_required
def profile():
    user = User.query.get(current_user.id)
    return render_template('profile.html', user=user)
# this route handle user profile update
@app.route('/update_profile_picture', methods=['POST'])
@login_required
def update_profile_picture():
    profile_picture = request.files.get('profile_picture')
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    location = request.form.get('location')

    if profile_picture:
        uploads_dir = os.path.abspath("uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        filename = secure_filename(profile_picture.filename)
        
        try:
            with Image.open(profile_picture) as img:
                img.thumbnail((800, 800))
                img.save(os.path.join(uploads_dir, filename))

            current_user.profile_picture = filename
            current_user.username = username
            current_user.email = email
            current_user.phone = phone
            current_user.location = location
            db.session.commit()
            flash("Profile picture updated successfully!", "success")
        except Exception as e:
            flash("An error occurred while uploading the image.", "danger")
            print(e)

    return redirect(url_for('profile'))
# Route for User Registration.
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        location = request.form.get('location')
        password = request.form.get('password')
        is_supplier = request.form.get('is_supplier') == 'on'

        profile_picture_path = None
        profile_picture = request.files.get('profile_picture')

        if profile_picture:
            if not (profile_picture.filename.lower().endswith(('.png', '.jpg', '.jpeg'))):
                flash("Only JPG and PNG files are allowed", "warning")
                return render_template('/signup.html')

            uploads_dir = os.path.abspath("uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = secure_filename(profile_picture.filename)
            profile_picture_path = os.path.join(uploads_dir, filename)

            try:
                with Image.open(profile_picture) as img:
                    img.thumbnail((800, 800))
                    img.save(profile_picture_path)
            except Exception as e:
                print(f"An error occurred while saving the image: {e}")
                flash("An error occurred while uploading the image.", "danger")
                return render_template('/signup.html')

        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email Already Exist", "warning")
            return render_template('/signup.html')

        hashed_password = generate_password_hash(password)
        newuser = User(
            username=username,
            email=email,
            password=hashed_password,
            phone=phone,
            location=location,
            is_supplier=is_supplier,
            profile_picture=filename
        )
        db.session.add(newuser)
        db.session.commit()
        flash("Signup Successful! Please Login", "success")
        return redirect(url_for('login'))
        
    return render_template('signup.html')

    
# Loging route with role management
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_supplier'] = user.is_supplier
            flash("Login Success", "primary")
            
            # Redirect admin users to admin dashboard
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            
            return redirect(url_for('index'))
        else:
            flash("invalid credentials", "warning")
            return render_template('login.html')

    return render_template('login.html')
# route for community forum.
@app.route('/forum', methods=['GET', 'POST'])
@login_required
def forum():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        new_post = ForumPost(title=title, content=content, author_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        flash('Your post has been added!', 'success')
        return redirect(url_for('forum'))
    
    posts = ForumPost.query.order_by(ForumPost.timestamp.desc()).all()
    return render_template('forum.html', posts=posts)
# This route allow users to add coments to a post
@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    post = ForumPost.query.get_or_404(post_id)
    content = request.form.get('comment_content')
    if content:
        new_comment = Comment(content=content, author_id=current_user.id, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
    return redirect(url_for('forum'))
# this route end all user session in the system
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout SuccessFul", "warning")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)