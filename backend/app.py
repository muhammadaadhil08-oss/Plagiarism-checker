import os
import json
import uuid
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
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_credentials(email, password, name=None):
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump({'email': email, 'password': password, 'name': name}, f, indent=4)

def get_initials(email, name=None):
    """Calculate initials from name or email."""
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

def get_history():
    """Load history and ensure all items have iso_date for filtering."""
    history = load_history()
    updated = False
    for item in history:
        if 'iso_date' not in item:
            try:
                # Convert "March 15, 2026" to "2026-03-15"
                dt = datetime.strptime(item['date'], "%B %d, %Y")
                item['iso_date'] = dt.strftime("%Y-%m-%d")
                updated = True
            except:
                item['iso_date'] = ""
    
    if updated:
        save_history(history)
    return history

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)


@app.route('/')
def dashboard():
    """Render the main dashboard."""
    if 'user' not in session:
        return redirect(url_for('login'))
        
    history_data = get_history()
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
            
    metrics = {
        'total': total_analyses,
        'human': human_written,
        'ai': ai_detected,
        'mixed': mixed_content,
        'human_pct': round((human_written / total_analyses * 100), 1) if total_analyses > 0 else 0,
        'ai_pct': round((ai_detected / total_analyses * 100), 1) if total_analyses > 0 else 0,
        'mixed_pct': round((mixed_content / total_analyses * 100), 1) if total_analyses > 0 else 0,
    }

    initials = get_initials(session.get('user'), session.get('name'))
    return render_template('index.html', recent_checks=recent_checks, metrics=metrics, initials=initials)

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
            if email == creds.get('email') and password == creds.get('password'):
                session['user'] = email
                session['name'] = creds.get('name')
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
    if email == creds.get('email'):
        save_credentials(email, new_password, creds.get('name'))
        return jsonify({'status': 'success', 'message': 'Password reset successful.'})
    return jsonify({'status': 'error', 'message': 'Email not found.'}), 404

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email')
    otp = request.form.get('otp')
    new_password = request.form.get('new_password')
    
    if email in otp_storage and otp_storage[email]['otp'] == otp:
        creds = load_credentials()
        save_credentials(email, new_password, creds.get('name'))
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
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/new_check')
def new_check():
    """Render the submit assignment page."""
    if 'user' not in session:
        return redirect(url_for('login'))
    initials = get_initials(session.get('user'))
    return render_template('new_check.html', initials=initials)

@app.route('/history')
def history():
    """Render the history page with dynamic data."""
    if 'user' not in session:
        return redirect(url_for('login'))
        
    history_data = load_history()
    initials = get_initials(session.get('user'))
    
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
            
    return render_template('history.html', history=history_data, metrics=metrics, initials=initials)

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
    Heuristic-based AI detection:
    - Reduce sensitivity
    - Long sentences increase score
    - Formal words increase score
    - Human pronouns decrease score
    """
    if not text:
        return 0
        
    # Normalize for word counting (remove punctuation for consistent matching)
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = clean_text.split()
    total_words = len(words)
    if total_words < 10:
        return 5 # Neutral low score for very short text
        
    score = 15 # Starting base score (reduced sensitivity)
    
    # 1. Sentence Length check
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_len = total_words / len(sentences)
        # AI often writes consistently long sentences
        if avg_len > 18:
            score += (avg_len - 18) * 4
        elif avg_len < 10:
            score -= 10 # Very short sentences feel human
            
    # 2. Formal Words (Increase score)
    formal_words = ["therefore", "moreover", "consequently", "furthermore", "additionally", 
                    "nevertheless", "nonetheless", "notwithstanding", "accordingly", "thus"]
    found_formal = 0
    for word in formal_words:
        if word in words:
            count = words.count(word)
            score += count * 10
            found_formal += count
            
    # 3. Human Pronouns (Decrease score)
    human_words = ["i", "my", "me", "we", "our", "us", "myself", "ourselves", "you"]
    for word in human_words:
        if word in words:
            # Multiplier for pronouns is high to reduce sensitivity
            score -= words.count(word) * 12
            
    # 4. Sentence Level Variation
    if len(sentences) > 2:
        lengths = [len(s.split()) for s in sentences]
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg)**2 for l in lengths) / len(lengths)
        # Low variance (uniform lengths) -> Higher AI score
        if variance < 10:
            score += 20
        elif variance > 40:
            score -= 15
            
    # Apply a boost if multiple formal signals are present
    if found_formal >= 3:
        score += 20

    # Clamp results to 0-100
    final_score = max(0, min(100, round(score)))
    
    # If the score is high, it's very likely AI
    # If the score is low, it's very likely human
    return final_score

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
    history_data = load_history()
    for item in history_data:
        if item.get('id') == item_id:
            return jsonify(item)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/history/<item_id>', methods=['DELETE'])
def delete_history_item(item_id):
    history_data = load_history()
    initial_len = len(history_data)
    history_data = [item for item in history_data if item.get('id') != item_id]
    
    if len(history_data) < initial_len:
        save_history(history_data)
        return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8001)
