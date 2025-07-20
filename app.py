from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
import random
import csv
import os
import time  # for tracking time

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for session tracking

# ---- Password Page Route ----

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == '1':
            session['authenticated'] = True
            return redirect(url_for('home'))
        else:
            flash('Incorrect password, please try again.')
    return render_template('login.html')

# ---- Random Generators ----

def random_constraint_name():
    prefix = random.choice(["SCOTTEX", "SCOTTIMP"])
    number = random.randint(1, 80)
    return f"{prefix}-{number}"

def random_margin_value():
    return random.randint(-10, 40)

def random_time_to_breach():
    return random.randint(0, 20)

def generate_items():
    items = []
    seen_ids = set()

    urgent_count = 0
    warning_count = 0
    system_tag_count = 0

    special_healthy_needed = 2
    margin_zero_or_less_needed = 1
    margin_1_5_and_ttb_1_5_needed = 1
    ttb_9_13_needed = 2

    while len(items) < 6:
        constraint_name = random_constraint_name()
        if constraint_name in seen_ids:
            continue
        seen_ids.add(constraint_name)

        is_system_tag = constraint_name.startswith("SCOTTIMP")
        if is_system_tag:
            if system_tag_count >= 1:
                continue
            system_tag_count += 1

        if special_healthy_needed > 0 and not is_system_tag:
            margin = random.randint(12, 40)
            time_breach = random.randint(15, 20)
            meter_flow_state = "healthy"
            special_healthy_needed -= 1

        elif margin_zero_or_less_needed > 0:
            margin = random.randint(-10, 0)
            time_breach = 0
            meter_flow_state = "urgent"
            margin_zero_or_less_needed -= 1
            urgent_count += 1

        elif margin_1_5_and_ttb_1_5_needed > 0:
            margin = random.randint(1, 5)
            time_breach = random.randint(1, 5)
            if warning_count < 1:
                meter_flow_state = "warning"
                warning_count += 1
            else:
                meter_flow_state = "healthy"
            margin_1_5_and_ttb_1_5_needed -= 1

        elif ttb_9_13_needed > 0:
            margin = random_margin_value()
            time_breach = 0 if margin <= 0 else random.randint(9, 13)
            if margin <= 0 and urgent_count < 1:
                meter_flow_state = "urgent"
                urgent_count += 1
            elif margin <= 0:
                meter_flow_state = "healthy"
            elif 1 <= margin <= 10 and warning_count < 1:
                meter_flow_state = "warning"
                warning_count += 1
            else:
                meter_flow_state = "healthy"
            ttb_9_13_needed -= 1

        else:
            margin = random_margin_value()
            time_breach = 0 if margin <= 0 else random_time_to_breach()

            if margin <= 0 and urgent_count < 1:
                meter_flow_state = "urgent"
                urgent_count += 1
            elif margin <= 0:
                meter_flow_state = "healthy"
            elif 1 <= margin <= 10 and warning_count < 1:
                meter_flow_state = "warning"
                warning_count += 1
            else:
                meter_flow_state = "healthy"

        items.append({
            "id": constraint_name,
            "meter_flow_state": meter_flow_state,
            "constraint_name": constraint_name,
            "is_system_tag": is_system_tag,
            "margin": margin,
            "time_to_breach": time_breach,
        })

    return items

# ---- Routes ----

@app.route('/', methods=['GET', 'POST'])
def home():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        role = request.form.get('role', '').strip()
        if not name or not role:
            error = "Please fill in both name and role."
            return render_template('home.html', error=error, name=name, role=role)
        
        session['name'] = name
        session['role'] = role
        session['round_order'] = random.sample([1, 2, 3, 4, 5], 5)
        session['round_index'] = 0
        session['results'] = []
        return redirect(url_for('game'))
    
    return render_template('home.html')

@app.route('/game')
def game():
    if 'name' not in session or 'role' not in session:
        return redirect(url_for('home'))

    round_index = session.get('round_index', 0)
    round_order = session.get('round_order', [])
    
    if round_index >= len(round_order):
        return redirect(url_for('complete'))

    round_num = round_order[round_index]
    items = generate_items()
    session['current_items'] = items
    session['round_start_time'] = time.time()  # ⏱️ Start time of the round

    return render_template('game.html', round=round_num, items=items, round_counter=round_index + 1)

@app.route('/submit_round', methods=['POST'])
def submit_round():
    if 'name' not in session or 'role' not in session:
        return jsonify({'finished': True})

    order = request.json.get('order')
    round_index = session.get('round_index', 0)
    round_order = session.get('round_order', [])
    round_num = round_order[round_index] if round_index < len(round_order) else None

    name = session.get('name')
    role = session.get('role')

    start_time = session.get('round_start_time', time.time())
    time_taken = round(time.time() - start_time, 2)  # ⏱️ duration in seconds

    session['results'].append({
        'round': round_num,
        'order': order,
        'name': name,
        'role': role,
        'time_taken': time_taken
    })

    session['round_index'] += 1

    if session['round_index'] >= len(round_order):
        save_results_to_csv(session['results'])
        session.clear()
        return jsonify({'finished': True})
    else:
        return jsonify({'finished': False})

def save_results_to_csv(results):
    csv_file = 'results.csv'
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, 'a', newline='') as csvfile:
        fieldnames = [
            'round', 'name', 'role', 'item_id', 'meter_flow_state', 
            'constraint_name', 'is_system_tag', 'margin', 
            'time_to_breach', 'time_taken_sec'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for round_result in results:
            round_num = round_result['round']
            name = round_result.get('name', '')
            role = round_result.get('role', '')
            time_taken = round_result.get('time_taken', 0)
            for item in round_result['order']:
                writer.writerow({
                    'round': round_num,
                    'name': name,
                    'role': role,
                    'item_id': item['id'],
                    'meter_flow_state': item['meter_flow_state'],
                    'constraint_name': item['constraint_name'],
                    'is_system_tag': item['is_system_tag'],
                    'margin': item['margin'],
                    'time_to_breach': item['time_to_breach'],
                    'time_taken_sec': time_taken
                })

@app.route('/complete')
def complete():
    return "<h1>Thank you! The game is complete.</h1>"

if __name__ == '__main__':
    app.run(debug=True)
