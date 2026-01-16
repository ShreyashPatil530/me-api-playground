from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///profile.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    education = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'education': self.education,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), default='Intermediate')
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level
        }

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description
        }

class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))  # github, linkedin, portfolio
    url = db.Column(db.String(255))
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'url': self.url
        }

# Create tables
with app.app_context():
    db.create_all()

# Serve Frontend
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# API Endpoints

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'API is running'}), 200

@app.route('/api/profile', methods=['GET'])
def get_profile():
    profile = Profile.query.first()
    if profile:
        skills = Skill.query.filter_by(profile_id=profile.id).all()
        projects = Project.query.filter_by(profile_id=profile.id).all()
        links = Link.query.filter_by(profile_id=profile.id).all()
        
        data = profile.to_dict()
        data['skills'] = [s.to_dict() for s in skills]
        data['projects'] = [p.to_dict() for p in projects]
        data['links'] = [l.to_dict() for l in links]
        return jsonify(data), 200
    return jsonify({'message': 'No profile found'}), 404

@app.route('/api/profile', methods=['POST'])
def create_profile():
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({'message': 'Name and email are required'}), 400
        
        # Check if profile already exists
        existing = Profile.query.first()
        if existing:
            # Update existing profile instead
            existing.name = data.get('name')
            existing.email = data.get('email')
            existing.education = data.get('education', '')
            db.session.commit()
            return jsonify(existing.to_dict()), 200
        
        # Create new profile
        profile = Profile(
            name=data.get('name'),
            email=data.get('email'),
            education=data.get('education', '')
        )
        
        db.session.add(profile)
        db.session.commit()
        
        return jsonify(profile.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    profile = Profile.query.first()
    if not profile:
        return jsonify({'message': 'No profile found'}), 404
    
    data = request.get_json()
    profile.name = data.get('name', profile.name)
    profile.email = data.get('email', profile.email)
    profile.education = data.get('education', profile.education)
    
    db.session.commit()
    return jsonify(profile.to_dict()), 200

@app.route('/api/skills', methods=['GET'])
def get_skills():
    profile = Profile.query.first()
    if not profile:
        return jsonify({'message': 'No profile found'}), 404
    
    skills = Skill.query.filter_by(profile_id=profile.id).all()
    return jsonify([s.to_dict() for s in skills]), 200

@app.route('/api/skills', methods=['POST'])
def add_skill():
    try:
        profile = Profile.query.first()
        if not profile:
            return jsonify({'message': 'Please create a profile first'}), 400
        
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'message': 'Skill name is required'}), 400
        
        skill = Skill(
            name=data.get('name'),
            level=data.get('level', 'Intermediate'),
            profile_id=profile.id
        )
        
        db.session.add(skill)
        db.session.commit()
        return jsonify(skill.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/skills/<int:skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    skill = Skill.query.get(skill_id)
    if not skill:
        return jsonify({'message': 'Skill not found'}), 404
    
    db.session.delete(skill)
    db.session.commit()
    return jsonify({'message': 'Skill deleted'}), 200

@app.route('/api/projects', methods=['GET'])
def get_projects():
    profile = Profile.query.first()
    if not profile:
        return jsonify({'message': 'No profile found'}), 404
    
    projects = Project.query.filter_by(profile_id=profile.id).all()
    return jsonify([p.to_dict() for p in projects]), 200

@app.route('/api/projects', methods=['POST'])
def add_project():
    try:
        profile = Profile.query.first()
        if not profile:
            return jsonify({'message': 'Please create a profile first'}), 400
        
        data = request.get_json()
        if not data or not data.get('title'):
            return jsonify({'message': 'Project title is required'}), 400
        
        project = Project(
            title=data.get('title'),
            description=data.get('description', ''),
            profile_id=profile.id
        )
        
        db.session.add(project)
        db.session.commit()
        return jsonify(project.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted'}), 200

@app.route('/api/skills/top', methods=['GET'])
def get_top_skills():
    profile = Profile.query.first()
    if not profile:
        return jsonify({'message': 'No profile found'}), 404
    
    skills = Skill.query.filter_by(profile_id=profile.id).limit(5).all()
    return jsonify([s.to_dict() for s in skills]), 200

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    profile = Profile.query.first()
    if not profile:
        return jsonify({'message': 'No profile found'}), 404
    
    skills = Skill.query.filter(Skill.name.ilike(f'%{query}%'), Skill.profile_id == profile.id).all()
    projects = Project.query.filter(Project.title.ilike(f'%{query}%'), Project.profile_id == profile.id).all()
    
    return jsonify({
        'skills': [s.to_dict() for s in skills],
        'projects': [p.to_dict() for p in projects]
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, port=port, host='0.0.0.0')