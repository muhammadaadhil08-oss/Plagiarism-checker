import os
import json
import uuid
import tempfile
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash

# Import the custom analysis modules (Only plagiarism is kept)
from web_verifier import search_web

# Initialize Flask App
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'history.json')
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')

app = Flask(__name__, 
            template_folder=os.path.join(frontend_dir, 'templates'),
            static_folder=os.path.join(frontend_dir, 'statics'))
app.secret_key = 'your-secret-key-here' # In a real app, use a secure random key

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                data = json.load(f)
                # Migration: if old single-user format is found, wrap it
                if 'email' in data and isinstance(data.get('email'), str) and 'password' in data:
                    return {data['email']: data}
                return data
        except:
            return {}
    return {}

def atomic_save_json(filepath, data):
    """Save JSON atomicaly using a temporary file to prevent corruption and hangs."""
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        shutil.move(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"FAILED TO SAVE {filepath}: {e}")

def save_credentials(email, password, name=None):
    creds = load_credentials()
    creds[email] = {'email': email, 'password': password, 'name': name}
    atomic_save_json(CREDENTIALS_FILE, creds)

def get_initials(email, name=None):
    """Calculate initials from name or email."""
    if email == "nmuhammadaadhil0@gmail.com": return "MA"
    if email == "shierkaadhil0@gmail.com": return "SA"
        
    source = name if name else email
    if not source:
        return "U"
        
    if name:
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return parts[0][0].upper()
        
    # Email fallback logic
    clean_email = email.split('@')[0]
    # Replace common separators with spaces to use the same logic
    for sep in ['.', '_', '-']:
        clean_email = clean_email.replace(sep, ' ')
        
    parts = clean_email.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif len(parts[0]) >= 2:
        # Try to find CamelCase or just take first two
        return (parts[0][0] + parts[0][1]).upper()
    return parts[0][0].upper()

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def get_user_history():
    """Load history and filter by logged-in user."""
    history = load_history()
    user_email = session.get('user')
    updated = False
    for item in history:
        if 'iso_date' not in item:
            try:
                # Convert "March 15, 2026" to "2026-03-15"
                dt = datetime.strptime(item.get('date', ''), "%B %d, %Y")
                item['iso_date'] = dt.strftime("%Y-%m-%d")
                updated = True
            except:
                item['iso_date'] = ""
    
    if updated:
        save_history(history)
        
    if not user_email:
        return []
    
    # Filter strictly by logged-in user email
    return [item for item in history if item.get('email') == user_email]

def save_history(history):
    atomic_save_json(HISTORY_FILE, history)


@app.route('/')
def dashboard():
    """Render the main dashboard."""
    print(f"DEBUG: Entering Dashboard route for user: {session.get('user')}")
    if 'user' not in session:
        return redirect(url_for('login'))
        
    history_data = get_user_history()
    recent_checks = history_data[:5] # Get last 5 checks
    
    # Calculate metrics
    total_analyses = len(history_data)
    human_written = 0
    ai_detected = 0
    mixed_content = 0
    
    for item in history_data:
        plag_score = item.get('plagiarism_score', 0)
        ai_score = item.get('ai_score', 0)
        if ai_score > 60 or plag_score > 60:
            ai_detected += 1
        elif ai_score < 20 and plag_score < 20:
            human_written += 1
        else:
            mixed_content += 1
            
    try:
        metrics = {
            'total': total_analyses,
            'human': human_written,
            'ai': ai_detected,
            'mixed': mixed_content,
            'human_pct': round((human_written / total_analyses * 100), 1) if total_analyses > 0 else 0,
            'ai_pct': round((ai_detected / total_analyses * 100), 1) if total_analyses > 0 else 0,
            'mixed_pct': round((mixed_content / total_analyses * 100), 1) if total_analyses > 0 else 0,
        }
    except Exception as e:
        print(f"Metric calculation error: {e}")
        metrics = {'total': 0, 'human': 0, 'ai': 0, 'mixed': 0, 'human_pct': 0, 'ai_pct': 0, 'mixed_pct': 0}

    initials = get_initials(session.get('user'), session.get('name'))
    user_email = session.get('user')
    return render_template('index.html', recent_checks=recent_checks, metrics=metrics, initials=initials, user_email=user_email)

import random

# Mock OTP storage: {email: {"otp": code, "expiry": timestamp}}
otp_storage = {}

def send_otp(email):
    """Generate and 'send' OTP (mock)."""
    otp = str(random.randint(100000, 999999))
    otp_storage[email] = {
        'otp': otp,
        'timestamp': datetime.now()
    }
    # In a real app, send actual email here.
    print(f"\n[MOCK EMAIL] To: {email}")
    print(f"[MOCK EMAIL] Your OTP is: {otp}\n")
    return otp

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login page and handle authentication."""
    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email')
        password = request.form.get('password')
        
        creds = load_credentials()
        
        # Action 1: Initial Login Step (Email/Password)
        if action == 'login':
            # If no credentials exist, first successful "login" creates the master account
            if not creds:
                save_credentials(email, password)
                session['user'] = email
                return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
            
            # Validate against stored credentials
            user_cred = creds.get(email)
            if user_cred and password == user_cred.get('password'):
                session['user'] = email
                session['name'] = user_cred.get('name')
                return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
            else:
                return jsonify({'status': 'error', 'message': 'Invalid email or password.'}), 401

        # Action 2: OTP Verification
        elif action == 'verify_otp':
            otp_entered = request.form.get('otp')
            if email in otp_storage and otp_storage[email]['otp'] == otp_entered:
                # Check expiry (mock: 10 mins)
                # Success
                session['user'] = email
                session['name'] = creds.get('name')
                otp_storage.pop(email)
                return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
            else:
                return jsonify({'status': 'error', 'message': 'Invalid OTP.'}), 400
                
    return render_template('login.html')

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.form.get('email')
    new_password = request.form.get('new_password')
    creds = load_credentials()
    user_cred = creds.get(email)
    if user_cred:
        save_credentials(email, new_password, user_cred.get('name'))
        return jsonify({'status': 'success', 'message': 'Password reset successful.'})
    return jsonify({'status': 'error', 'message': 'Email not found.'}), 404

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email')
    otp = request.form.get('otp')
    new_password = request.form.get('new_password')
    
    if email in otp_storage and otp_storage[email]['otp'] == otp:
        creds = load_credentials()
        user_cred = creds.get(email, {})
        save_credentials(email, new_password, user_cred.get('name'))
        otp_storage.pop(email)
        return jsonify({'status': 'success', 'message': 'Password reset successful.'})
    return jsonify({'status': 'error', 'message': 'Invalid OTP.'}), 400

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return redirect(url_for('login', mode='signup'))
        
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')
    
    if email and password:
        # Save master credentials with name
        save_credentials(email, password, name)
        session['user'] = email
        session['name'] = name
        return redirect(url_for('dashboard'))
    
    return render_template('login.html', error='Sign Up Failed.')

@app.route('/logout')
def logout():
    print(f"DEBUG: Logging out user: {session.get('user')}")
    session.clear() # Completely clear session for safety
    return redirect(url_for('login'))

@app.route('/new_check')
def new_check():
    """Render the submit assignment page."""
    if 'user' not in session:
        return redirect(url_for('login'))
    initials = get_initials(session.get('user'))
    user_email = session.get('user')
    return render_template('new_check.html', initials=initials, user_email=user_email)

@app.route('/history')
def history():
    """Render the history page with dynamic data."""
    print(f"DEBUG: Entering History route for user: {session.get('user')}")
    if 'user' not in session:
        return redirect(url_for('login'))
        
    history_data = get_user_history()
    initials = get_initials(session.get('user'), session.get('name'))
    user_email = session.get('user')
    
    # Calculate metrics
    total_analyses = len(history_data)
    human_written = 0
    ai_detected = 0
    mixed_content = 0
    
    for item in history_data:
        plag_score = item.get('plagiarism_score', 0)
        ai_score = item.get('ai_score', 0)
        if ai_score > 60 or plag_score > 60:
            ai_detected += 1
        elif ai_score < 20 and plag_score < 20:
            human_written += 1
        else:
            mixed_content += 1
            
    metrics = {
        'total': total_analyses,
        'human': human_written,
        'ai': ai_detected,
        'mixed': mixed_content
    }
            
    return render_template('history.html', history=history_data, metrics=metrics, initials=initials, user_email=user_email)

import re
from collections import Counter

def calculate_repetition_score(text):
    """
    Calculate plagiarism based on repeated words and phrases vs total.
    Includes both word-level and 3-word phrase-level checks for high sensitivity.
    """
    if not text:
        return 0
        
    # Normalize text: lowercase and remove punctuation
    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    words = clean_text.split()
    if len(words) < 5:
        return 0
        
    # 1. Word Level Repetition (Significant Words)
    stop_words = {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", 
        "at", "from", "by", "for", "with", "about", "against", "between", 
        "into", "through", "during", "before", "after", "is", "are", "was", "were", 
        "be", "been", "being", "have", "has", "had", "do", "does", "did", "of", "to", "in"
    }
    sig_words = [w for w in words if w not in stop_words]
    if not sig_words:
        return 0
        
    word_counts = Counter(sig_words)
    repeated_words = sum(count - 1 for count in word_counts.values() if count > 1)
    word_score = (repeated_words / len(sig_words)) * 100 * 2.0
    
    # 2. Phrase Level Repetition (3-word phrases / N-grams)
    # This detects "common sentences" or copied structures
    phrases = []
    for i in range(len(words) - 2):
        phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
    if not phrases:
        return round(word_score)
        
    phrase_counts = Counter(phrases)
    # If the same 3-word phrase appears multiple times, it's very suspicious
    repeated_phrases = sum(count - 1 for count in phrase_counts.values() if count > 1)
    phrase_score = (repeated_phrases / len(phrases)) * 100 * 4.0
    
    # Combine scores with high sensitivity
    final_score = max(word_score, phrase_score)
    return min(100, round(final_score))

def calculate_ai_score(text):
    """
    Robust Heuristic-based AI detection:
    - Highly sensitive to ChatGPT buzzwords
    - Analyzes sentence length and variance
    - Detects typical AI structural transitions
    """
    if not text:
        return 0
        
    lower_text = text.lower()
    clean_text = re.sub(r'[^\w\s]', ' ', lower_text)
    words = clean_text.split()
    total_words = len(words)
    
    if total_words < 10:
        return 0
        
    score = 0 # Base score is 0% for pure human text!
    
    # 1. AI Buzzwords & Cliches
    ai_buzzwords = [
        "delve", "landscape", "underscore", "seamlessly", "realm", "multifaceted", 
        "testament", "tapestry", "foster", "meticulously", "synergy", "optimal",
        "holistic", "empower", "nuanced", "cornerstone", "navigating", "evolving"
    ]
    
    found_buzzwords = sum(1 for w in ai_buzzwords if w in lower_text)
    if found_buzzwords > 0:
        score += found_buzzwords * 22 # Increased from 18
            
    # 2. Structural Transitions
    transitions = [
        "it is important to note", "to summarize", "in summary", "overall", 
        "firstly", "in conclusion", "conversely", "furthermore", "moreover"
    ]
    found_trans = sum(1 for t in transitions if t in lower_text)
    score += found_trans * 30 # Increased from 25
            
    # 3. Sentence Length check
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_len = total_words / len(sentences)
        # AI often writes consistently around 12-25 words per sentence
        if 12 < avg_len < 25:
            score += 15
            
    # 4. Sentence Level Variation
    if len(sentences) > 2:
        lengths = [len(s.split()) for s in sentences]
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg)**2 for l in lengths) / len(lengths)
        # Low variance (uniform lengths) -> Higher AI score
        if variance < 15:
            score += 30
            
    # 5. Human Pronouns
    human_count = sum(words.count(w) for w in ["i", "my", "me", "myself", "we", "our"])
    score -= human_count * 8
            
    # Clamp results to 0-100
    return max(0, min(100, round(score)))

# --- PLAGIARISM CHECKER ROUTE ---
@app.route('/plagiarism', methods=['POST'])
def check_plagiarism():
    """Endpoint to perform web searches for plagiarism and save to history."""
    data = request.json
    text = data.get('text', '')
    filename = data.get('filename', 'Pasted Text')
    
    if not text or len(text.split()) < 15:
         return jsonify({'error': 'Please provide at least 15 words for plagiarism checking.'}), 400
         
    # Call the web verifier tool
    result = search_web(text)
    
    if not result.get('error'):
        # 1. Improve plagiarism detection: Combine web score and repetition score
        web_score = result.get('web_score', 0)
        repetition_score = calculate_repetition_score(text)
        
        # Final plagiarism score: Higher of the two, or a weighted blend
        # If web detects copying, that's primary. Else repetition suggests non-original content.
        plag_score = max(web_score, repetition_score)
        
        # 2. Improve AI detection: Use the heuristic function
        ai_score = calculate_ai_score(text)
        
        word_count = len(text.split())
        now = datetime.now()
        
        history_item = {
            'id': str(uuid.uuid4()),
            'email': session.get('user'),
            'title': filename,
            'date': now.strftime("%B %d, %Y"),
            'time': now.strftime("%I:%M %p"),
            'iso_date': now.strftime("%Y-%m-%d"),
            'word_count': word_count,
            'plagiarism_score': plag_score,
            'ai_score': ai_score,
            'text': text
        }
        
        history_data = load_history()
        history_data.insert(0, history_item) # Prepend newest
        save_history(history_data)
        
        result['history_item'] = history_item
        result['ai_score'] = ai_score
        result['web_score'] = web_score
        result['repetition_score'] = repetition_score # Add for detail
    
    return jsonify(result)

# --- HISTORY API ROUTES ---
@app.route('/api/history/<item_id>', methods=['GET'])
def get_history_item(item_id):
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    history_data = get_user_history()
    for item in history_data:
        if item.get('id') == item_id:
            return jsonify(item)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/history/<item_id>', methods=['DELETE'])
def delete_history_item(item_id):
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    history_data = load_history()
    user_email = session.get('user')
    
    # Verify ownership before deleting
    target_item = next((item for item in history_data if item.get('id') == item_id), None)
    if not target_item or target_item.get('email') != user_email:
        return jsonify({'error': 'Not found or unauthorized'}), 404
        
    history_data = [item for item in history_data if item.get('id') != item_id]
    save_history(history_data)
    return jsonify({'success': True})
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8001)
