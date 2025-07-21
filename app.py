from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
import random, csv, os, time
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"  # ⚠️ replace in production

# ─────────────────────────────  AUTH  ──────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == "1":
            session["authenticated"] = True
            return redirect(url_for("context"))  # 👈 go to context first
        flash("Incorrect password, please try again.")
    return render_template("login.html")


@app.route("/context", methods=["GET", "POST"])
def context():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    if request.method == "POST":
        return redirect(url_for("instructions"))

    return render_template("context.html")

@app.route("/instructions", methods=["GET", "POST"])
def instructions():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    if request.method == "POST":
        return redirect(url_for("home"))

    return render_template("instructions.html")


# ──────────────────────  UTILITY – DATA GENERATION  ─────────────────
def random_constraint_name():
    return f'{random.choice(["SCOTTEX", "SCOTTIMP"])}-{random.randint(1,80)}'

def random_margin_value(): return random.randint(-10, 40)
def random_time_to_breach(): return random.randint(0, 20)


def generate_items():
    seen_ids = set()
    items = []

    def new_id():
        while True:
            cid = random_constraint_name()
            if cid not in seen_ids:
                seen_ids.add(cid)
                return cid

    def add_item(margin, ttb):
        # Enforce ttb = 0 if margin <= 0
        if margin <= 0:
            ttb = 0
        items.append({
            "id": new_id(),
            "meter_flow_state": "healthy",
            "constraint_name": list(seen_ids)[-1],
            "is_system_tag": False,
            "margin": margin,
            "time_to_breach": ttb
        })

    # 1. One item with margin -5 to 0 and TTB = 0
    add_item(random.randint(-5, 0), 0)

    # 2. Two items with margin 2–10 and TTB 0–5
    for _ in range(2):
        add_item(random.randint(2, 10), random.randint(0, 5))

    # 3. One item with margin 11 and TTB 6–14
    add_item(11, random.randint(6, 14))

    # 4. Two items with margin 16–30 and TTB 15–30
    for _ in range(2):
        add_item(random.randint(16, 30), random.randint(15, 30))

    # 5. Shuffle so order is randomized
    random.shuffle(items)
    return items







# ─────────────────────────────  ROUTES  ────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name, role = request.form.get("name", "").strip(), request.form.get("role", "").strip()
        if not name or not role:
            return render_template("home.html", error="Please fill in both name and role.",
                                   name=name, role=role)

        session.update({
            "name": name,
            "role": role,
            "round_order": random.sample([1, 2, 3, 4, 5], 5),
            "round_index": 0,
            "results": [],
            "comments": []
        })
        return redirect(url_for("game"))
    return render_template("home.html")

@app.route("/game")
def game():
    if "name" not in session:
        return redirect(url_for("home"))

    idx, order = session["round_index"], session["round_order"]
    if idx >= len(order):
        return redirect(url_for("complete"))

    rnd = order[idx]
    items = generate_items()
    session["current_items"] = items
    session["round_start_ts"] = time.time()

    return render_template("game.html",
                           round=rnd,
                           items=items,
                           round_counter=idx + 1)

@app.route("/submit_round", methods=["POST"])
def submit_round():
    if "name" not in session:
        return jsonify(finished=True)

    order = request.json["order"]
    idx = session["round_index"]
    rnd = session["round_order"][idx]

    result = {
        "round": rnd,
        "order": order,
        "name": session["name"],
        "role": session["role"],
        "time_taken": round(time.time() - session["round_start_ts"], 2)
    }
    session["results"].append(result)
    session.modified = True

    # Save the result immediately here
    save_results([result])

    return jsonify(finished=False, redirect_url=url_for("comment"))


@app.route("/comment", methods=["GET", "POST"])
def comment():
    if "name" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        comment_text = request.form.get("comment", "").strip()
        session["comments"].append(comment_text)
        session.modified = True

        if session.get("results"):
            latest_result = session["results"][-1]

            round_num = latest_result["round"]
            name = session["name"]
            role = session["role"]
            ui_tested = f"UI{round_num}"

            save_comments(round_num, name, role, ui_tested, comment_text)

        # ✅ Increment after saving
        session["round_index"] += 1

        if session["round_index"] >= len(session["round_order"]):
            return redirect(url_for("complete"))

        return redirect(url_for("game"))

    # ✅ For GET: get the round just completed
    round_idx = session["round_index"]
    current_round = session["round_order"][round_idx]

    return render_template("comment.html", round_counter=round_idx + 1, round=current_round)




@app.route("/complete", methods=["GET"])
def complete():
    # Do NOT clear session here so we can access name and role
    name = session.get("name", "")
    role = session.get("role", "")
    return render_template("complete.html", name=name, role=role)

@app.route("/submit_complete_comment", methods=["POST"])
def submit_complete_comment():
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    comment = request.form.get("comment", "").strip()

    if not name or not role or not comment:
        # You might want to flash an error or redirect back with a message
        return redirect(url_for("complete"))

    # Save comment to morecomments.csv
    path = "morecomments.csv"
    exists = os.path.isfile(path)
    with open(path, "a", newline="") as f:
        cols = ["name", "role", "comment"]
        writer = csv.DictWriter(f, fieldnames=cols)
        if not exists:
            writer.writeheader()
        writer.writerow({
            "name": name,
            "role": role,
            "comment": comment
        })

    # After saving clear the session and thank user or redirect to a thank you page
    session.clear()
    return render_template("thankyou.html", name=name)

# ───────────────────────  CSV PERSISTENCE  ─────────────────────────
def save_results(results):
    path = "results.csv"
    exists = os.path.isfile(path)
    with open(path, "a", newline="") as f:
        cols = ["round", "name", "role", "item_id", "meter_flow_state", "constraint_name",
                "is_system_tag", "margin", "time_to_breach", "time_taken_sec"]
        writer = csv.DictWriter(f, fieldnames=cols)
        if not exists:
            writer.writeheader()

        for r in results:
            for item in r["order"]:
                writer.writerow({
                    "round": r["round"],
                    "name": r["name"],
                    "role": r["role"],
                    "item_id": item["id"],
                    "meter_flow_state": item["meter_flow_state"],
                    "constraint_name": item["constraint_name"],
                    "is_system_tag": item["is_system_tag"],
                    "margin": item["margin"],
                    "time_to_breach": item["time_to_breach"],
                    "time_taken_sec": r["time_taken"]
                })

def save_comments(round_num, name, role, ui_tested, comment):
    path = "usercomments.csv"
    print(f"Saving comment to file: {os.path.abspath(path)}")  # Debug print with full path
    exists = os.path.isfile(path)
    with open(path, "a", newline="") as f:
        cols = ["round", "name", "role", "ui_tested", "comment"]
        writer = csv.DictWriter(f, fieldnames=cols)
        if not exists:
            writer.writeheader()

        writer.writerow({
            "round": round_num,
            "name": name,
            "role": role,
            "ui_tested": ui_tested,
            "comment": comment
        })


# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
