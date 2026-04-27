# Serveur A2SUP QCM
# Flask + session pour l'authentification

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
)
import json, os, random, threading
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = "a2sup_qcm_secret_key_2026"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Lock pour la sécurité des accès concurrents au fichier history.json
history_lock = threading.Lock()

# Chargement de la base de données depuis le fichier JSON
DB_PATH = os.path.join(os.path.dirname(__file__), "db.json")
with open(DB_PATH, "r", encoding="utf-8") as f:
    DB = json.load(f)

# Fichier où on stocke l'historique des quiz par utilisateur
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.json")


def load_history():
    """Récupère l'historique depuis le fichier, ou crée un fichier vide"""
    with history_lock:
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}


def save_history(history):
    """Sauvegarde l'historique dans le fichier"""
    with history_lock:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


# Comptes utilisateurs du tutorat
USERS = {
    "a2sup": {"name": "A2SUP Tutorat"},
    "etudiant": {"name": "Étudiant"},
    "louai": {"name": "Louaï"},
}


@app.route("/logo.jpg")
def logo():
    return send_from_directory(os.path.dirname(__file__), "logo.jpg")


@app.route("/")
def index():
    """Redirige vers la connexion si pas connecté, sinon vers le tableau de bord"""
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion — vérifie l'identifiant et ouvre la session"""
    error = None
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip().lower()
        if user_id in USERS:
            session["user"] = user_id
            session["user_name"] = USERS[user_id]["name"]
            return redirect(url_for("dashboard"))
        else:
            error = "Identifiant incorrect"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Déconnexion — on vide la session et on renvoie à l'accueil"""
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    """Tableau de bord — affiche les UE disponibles"""
    if "user" not in session:
        return redirect(url_for("login"))
    ues = DB["ues"]
    history = load_history()
    user_history = history.get(session["user"], {})
    return render_template(
        "dashboard.html",
        ues=ues,
        user_name=session.get("user_name", ""),
        user_history=user_history,
    )


@app.route("/ue/<ue_id>")
def ue_view(ue_id):
    """Page d'une UE — grille des chapitres avec le nombre de questions"""
    if "user" not in session:
        return redirect(url_for("login"))
    ue = DB["ues"].get(ue_id)
    if not ue:
        return redirect(url_for("dashboard"))

    # On récupère l'historique de l'utilisateur pour afficher les quiz déjà faits
    history = load_history()
    user_history = history.get(session["user"], {})

    return render_template(
        "ue.html",
        ue=ue,
        ue_id=ue_id,
        user_name=session.get("user_name", ""),
        user_history=user_history,
    )


@app.route("/quiz/<ue_id>/<int:chapter_id>")
def quiz_view(ue_id, chapter_id):
    """Page de quiz — charge les questions du chapitre choisi"""
    if "user" not in session:
        return redirect(url_for("login"))
    ue = DB["ues"].get(ue_id)
    if not ue:
        return redirect(url_for("dashboard"))

    # On cherche le chapitre dans l'UE
    chapter = None
    for ch in ue["chapters"]:
        if ch["id"] == chapter_id:
            chapter = ch
            break
    if not chapter:
        return redirect(url_for("ue_view", ue_id=ue_id))

    return render_template(
        "quiz.html",
        ue=ue,
        ue_id=ue_id,
        chapter=chapter,
        user_name=session.get("user_name", ""),
    )


@app.route("/api/questions/<ue_id>/<int:chapter_id>")
def api_questions(ue_id, chapter_id):
    """API qui renvoie les questions d'un chapitre, mélangées"""
    questions = [
        q
        for q in DB["questions"].values()
        if q["chapter_id"] == chapter_id and q["enabled"]
    ]

    mode = request.args.get("mode", "all")
    count = int(request.args.get("count", 0))

    random.shuffle(questions)

    if mode in ("random", "exam") and count > 0:
        questions = questions[:count]

    if count > 0 and len(questions) > count:
        questions = questions[:count]

    result = []
    for q in questions:
        result.append(
            {
                "id": q["id"],
                "statement": q["statement"],
                "items": q["items"],
                "answer_str": q["answer_str"],
                "corrections": q["corrections"],
                "false_correct": q.get("false_correct", False),
            }
        )

    return jsonify(result)


@app.route("/api/history", methods=["POST"])
def api_save_history():
    """Sauvegarde le résultat d'un quiz terminé ou la progression"""
    if "user" not in session:
        logging.warning("POST /api/history: utilisateur non connecté")
        return jsonify({"error": "non connecté"}), 401

    data = request.json
    logging.info(f"POST /api/history: data={data}, user={session.get('user')}")
    ue_id = data.get("ue_id")
    chapter_id = data.get("chapter_id")
    mode = data.get("mode", "all")
    correct = data.get("correct", 0)
    total = data.get("total", 0)
    progressive = data.get("progressive", False)

    if not ue_id or chapter_id is None:
        return jsonify({"error": "données manquantes"}), 400

    history = load_history()
    user_id = session["user"]

    if user_id not in history:
        history[user_id] = {}

    key = f"{ue_id.lower()}_{chapter_id}"

    existing = history[user_id].get(key)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # acc_correct / acc_total = cumul de toutes les sessions TERMINÉES
    # correct / total = valeurs affichées (cumul + session en cours)
    # Rétro-compatibilité : si pas de acc_*, on utilise correct/total comme base
    if existing:
        acc_correct = existing.get("acc_correct", existing.get("correct", 0))
        acc_total = existing.get("acc_total", existing.get("total", 0))
    else:
        acc_correct = 0
        acc_total = 0

    if progressive:
        # Sauvegarde intermédiaire : affiche cumul + progression session en cours
        display_correct = acc_correct + correct
        display_total = acc_total + total
        display_pct = round((display_correct / display_total) * 20, 2) if display_total > 0 else 0

        if existing:
            history[user_id][key].update({
                "correct": display_correct,
                "total": display_total,
                "pct": display_pct,
                "last_date": now,
            })
        else:
            history[user_id][key] = {
                "ue_id": ue_id,
                "chapter_id": chapter_id,
                "mode": mode,
                "correct": display_correct,
                "total": display_total,
                "acc_correct": 0,
                "acc_total": 0,
                "pct": display_pct,
                "date": now,
                "attempts": 1,
            }
    else:
        # Sauvegarde finale : on ajoute la session au cumul
        new_acc_correct = acc_correct + correct
        new_acc_total = acc_total + total
        new_pct = round((new_acc_correct / new_acc_total) * 20, 2) if new_acc_total > 0 else 0

        if existing:
            history[user_id][key].update({
                "correct": new_acc_correct,
                "total": new_acc_total,
                "acc_correct": new_acc_correct,
                "acc_total": new_acc_total,
                "pct": new_pct,
                "attempts": existing.get("attempts", 1) + 1,
                "last_date": now,
            })
        else:
            history[user_id][key] = {
                "ue_id": ue_id,
                "chapter_id": chapter_id,
                "mode": mode,
                "correct": correct,
                "total": total,
                "acc_correct": correct,
                "acc_total": total,
                "pct": round((correct / total) * 20, 2) if total > 0 else 0,
                "date": now,
                "attempts": 1,
            }

    save_history(history)
    return jsonify({"status": "ok"})


@app.route("/api/history")
def api_get_history():
    """Récupère l'historique de l'utilisateur connecté"""
    if "user" not in session:
        return jsonify({})

    history = load_history()
    return jsonify(history.get(session["user"], {}))


if __name__ == "__main__":
    # Pour la prod : 'pip install waitress'
    try:
        from waitress import serve
        logging.info("Lancement du serveur avec Waitress (Production)")
        serve(app, host="0.0.0.0", port=5000)
    except ImportError:
        logging.info("Lancement du serveur avec Flask Dev (Développement)")
        app.run(host="0.0.0.0", port=5000, debug=True)
