from __future__ import annotations
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, session
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'images')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///poems.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'change-me'  # set via env in production
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin123')  # override in env

db = SQLAlchemy(app)

# Models
class Writer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text, default='')
    email = db.Column(db.String(120), default='')
    social = db.Column(db.String(200), default='')
    avatar_url = db.Column(db.String(300), default='')

class Poem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    background_image = db.Column(db.String(300), default='')
    view_count = db.Column(db.Integer, default=0)

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(120), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poem_id = db.Column(db.Integer, db.ForeignKey('poem.id'), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscriber.id'), nullable=False)
    is_like = db.Column(db.Boolean, nullable=False)
    __table_args__ = (UniqueConstraint('poem_id', 'subscriber_id', name='uniq_reaction'),)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poem_id = db.Column(db.Integer, db.ForeignKey('poem.id'), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscriber.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SiteStat(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    count = db.Column(db.Integer, default=0)

# Utilities

def get_current_subscriber():
    sid = request.cookies.get('subscriber_id')
    if not sid:
        return None
    try:
        sid_int = int(sid)
    except ValueError:
        return None
    return Subscriber.query.get(sid_int)

def admin_required(fn):
    @wraps(fn)
    def _wrap(*args, **kwargs):
        if not session.get('is_admin'):
            flash('केवल व्यवस्थापक नई कविता जोड़ सकते हैं।', 'error')
            return redirect(url_for('admin_login', next=request.path))
        return fn(*args, **kwargs)
    return _wrap

# Routes
@app.route('/')
def index():
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 12  # show more poems per page
    q = (request.args.get('q') or '').strip()
    base_query = Poem.query
    if q:
        like = f"%{q}%"
        base_query = base_query.filter((Poem.title.ilike(like)) | (Poem.body.ilike(like)))
    total = base_query.count()
    poems = (base_query
             .order_by(Poem.date_added.desc())
             .offset((page-1)*per_page)
             .limit(per_page)
             .all())
    writer = Writer.query.first()
    # page hit count for home
    stat = SiteStat.query.get('home_hits')
    if not stat:
        stat = SiteStat(key='home_hits', count=0)
        db.session.add(stat)
    stat.count = (stat.count or 0) + 1
    db.session.commit()
    total_pages = (total + per_page - 1)//per_page
    return render_template('index.html', poems=poems, writer=writer, home_hits=stat.count,
                           page=page, per_page=per_page, total=total, total_pages=total_pages,
                           q=q)

@app.route('/poem/<int:poem_id>')
def poem_detail(poem_id: int):
    poem = Poem.query.get_or_404(poem_id)
    poem.view_count = (poem.view_count or 0) + 1
    db.session.commit()
    sub = get_current_subscriber()
    likes = Reaction.query.filter_by(poem_id=poem.id, is_like=True).count()
    dislikes = Reaction.query.filter_by(poem_id=poem.id, is_like=False).count()
    comments = Comment.query.filter_by(poem_id=poem.id).order_by(Comment.created_at.desc()).all()
    return render_template('poem_detail.html', poem=poem, likes=likes, dislikes=dislikes, comments=comments, subscriber=sub)

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        if not email:
            flash('Please enter your email to subscribe.', 'error')
            return redirect(url_for('subscribe'))
        sub = Subscriber.query.filter_by(email=email).first()
        if not sub:
            sub = Subscriber(email=email, name=name)
            db.session.add(sub)
            db.session.commit()
        resp = make_response(redirect(url_for('index')))
        resp.set_cookie('subscriber_id', str(sub.id), max_age=60*60*24*365)
        flash('Subscription successful! You can now like and comment.', 'success')
        return resp
    return render_template('subscribe.html')

@app.route('/add-poem', methods=['GET', 'POST'])
@admin_required
def add_poem():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        date_str = request.form.get('date_added', '').strip()
        img_url = request.form.get('image_url', '').strip()
        image_file = request.files.get('image_file')
        if not title or not body:
            flash('Title and poem content are required.', 'error')
            return redirect(url_for('add_poem'))
        when = None
        if date_str:
            try:
                when = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', 'error')
        filename = ''
        if image_file and image_file.filename:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            safe_name = f"{int(datetime.utcnow().timestamp())}_{image_file.filename.replace(' ', '_')}"
            dest = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
            image_file.save(dest)
            filename = f"/static/images/{safe_name}"
        elif img_url:
            filename = img_url
        poem = Poem(title=title, body=body, date_added=when or datetime.utcnow(), background_image=filename)
        db.session.add(poem)
        db.session.commit()
        flash('कविता जोड़ दी गई!', 'success')
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/delete-poem/<int:poem_id>', methods=['POST'])
@admin_required
def delete_poem(poem_id: int):
    poem = Poem.query.get_or_404(poem_id)
    # Delete associated reactions and comments
    Reaction.query.filter_by(poem_id=poem.id).delete()
    Comment.query.filter_by(poem_id=poem.id).delete()
    
    db.session.delete(poem)
    db.session.commit()
    flash('कविता हटा दी गई!', 'success')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        nxt = request.args.get('next') or url_for('index')
        if pwd == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            flash('एडमिन लॉगिन सफल।', 'success')
            return redirect(nxt)
        flash('गलत पासवर्ड।', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('आप लॉगआउट हो गए हैं।', 'success')
    return redirect(url_for('index'))

@app.route('/poem/<int:poem_id>/react', methods=['POST'])
def react(poem_id: int):
    action = request.form.get('action')
    poem = Poem.query.get_or_404(poem_id)
    sub = get_current_subscriber()
    if not sub:
        flash('Please subscribe to react.', 'error')
        return redirect(url_for('poem_detail', poem_id=poem_id))
    is_like = True if action == 'like' else False
    existing = Reaction.query.filter_by(poem_id=poem.id, subscriber_id=sub.id).first()
    if existing:
        existing.is_like = is_like
    else:
        db.session.add(Reaction(poem_id=poem.id, subscriber_id=sub.id, is_like=is_like))
    db.session.commit()
    return redirect(url_for('poem_detail', poem_id=poem.id))

@app.route('/poem/<int:poem_id>/comment', methods=['POST'])
def comment(poem_id: int):
    poem = Poem.query.get_or_404(poem_id)
    sub = get_current_subscriber()
    if not sub:
        flash('Please subscribe to comment.', 'error')
        return redirect(url_for('poem_detail', poem_id=poem.id))
    text = request.form.get('text', '').strip()
    if not text:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('poem_detail', poem_id=poem.id))
    db.session.add(Comment(poem_id=poem.id, subscriber_id=sub.id, text=text))
    db.session.commit()
    return redirect(url_for('poem_detail', poem_id=poem.id))

@app.route('/init-db')
def init_db():
    db.create_all()
    if not Writer.query.first():
        writer = Writer(name='डॉ. मनस्विनी श्रीवास्तव', bio='यहाँ लेखिका के बारे में जानकारी जोड़ें। उनकी प्रेरणा, यात्रा और साहित्यिक योगदान का संक्षेप।', email='', social='', avatar_url='')
        db.session.add(writer)
        db.session.commit()
    return 'Initialized.'

if __name__ == '__main__':
    import sys
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with app.app_context():
        db.create_all()
        if not Writer.query.first():
            db.session.add(Writer(name='डॉ. मनस्विनी श्रीवास्तव'))
            db.session.commit()
    
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}. Using default port 5000.")

    app.run(host='0.0.0.0', port=port, debug=True)
