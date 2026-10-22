"""Seed reference data + demo users + 500+ realistic sample requests (spread over the last 90 days).

Usage:  python -m app.seed                   (creates schema via Alembic, then seeds)
        python -m app.seed --reset           (drops all tables first)
        python -m app.seed --reset --demo    (Sprint 4 review: model versions v1.1 / v1.2 + 260 new labels)
"""
import argparse
import random
import shutil
from datetime import timedelta

from sqlalchemy.orm import Session

from . import kb_seed, schemas
from .config import get_settings
from .db import Base, SessionLocal, engine, utcnow
from .ml import dataset, embeddings
from .ml.classifier import ALGORITHM, load_or_train
from .models import (CSAT, AIFeedback, AuditLog, Category, EmailOutbox, FAQArticle, FAQArticleVersion, Message,
                     ModelRegistry, Notification, Priority, ReplyTemplate, Request, Role, RoutingLog, RoutingRule,
                     SLAPolicy, Status, StatusHistory, TrainingRun, Unit, UrgencyKeyword, User)
from .security import hash_password
from .services import pipeline, routing, sla, urgency

DEMO_PASSWORD = "Qoldau123!"

UNITS = [
    ("Dean's Office", "deans", "deans@qoldau.edu.kz"),
    ("Registrar Office", "registrar", "registrar@qoldau.edu.kz"),
    ("Finance Office", "finance", "finance@qoldau.edu.kz"),
    ("IT Help Desk", "it", "it@qoldau.edu.kz"),
    ("Student Housing Office", "housing", "housing@qoldau.edu.kz"),
    ("Main Library Desk", "library", "library@qoldau.edu.kz"),
    ("Medical & Counselling Center", "medical", "medical@qoldau.edu.kz"),
    ("International Office", "international", "intl@qoldau.edu.kz"),
    ("Triage Queue (Student Services)", "triage", "services@qoldau.edu.kz"),
]

# category, unit, default workflow, base priority weight
CATEGORIES = [
    ("Academic", "Dean's Office", "standard", 35),
    ("Registration & Enrollment", "Registrar Office", "standard", 35),
    ("Finance & Scholarships", "Finance Office", "approval", 38),
    ("IT Support", "IT Help Desk", "standard", 33),
    ("Dormitory & Housing", "Student Housing Office", "standard", 33),
    ("Documents & Certificates", "Registrar Office", "document", 30),
    ("Library", "Main Library Desk", "standard", 25),
    ("Health & Wellbeing", "Medical & Counselling Center", "urgent", 50),
    ("International Office", "International Office", "approval", 33),
    ("Other", "Triage Queue (Student Services)", "triage", 15),
]

AGENT_NAMES = ["Aigerim Sadykova", "Daniyar Omarov", "Madina Tulegenova", "Nurlan Abenov", "Saule Kassymova",
               "Yerlan Mukhamedov", "Dana Zhaksylykova", "Timur Bekov", "Aliya Serikova", "Ruslan Iskakov",
               "Gulnara Akhmetova", "Arman Nurpeisov", "Zarina Baimukhanova", "Askar Tokhtarov", "Kamila Ospanova",
               "Bauyrzhan Kenzhebek", "Assel Karimova", "Olzhas Sultanov", "Togzhan Mussina", "Erasyl Zhunusov",
               "Laura Dzhaksybekova", "Medet Amanov", "Ainur Bekzhanova", "Sanzhar Rakhimov"]
HEAD_NAMES = ["Prof. Kairat Zhanuzakov", "Dr. Gulmira Abdrakhmanova", "Marat Seitkali", "Dr. Yerbol Kassenov",
              "Zhanna Utepova", "Bakhyt Ismailova", "Dr. Almas Nurmagambetov", "Indira Kulzhanova",
              "Saltanat Yesmukhanova"]
STUDENT_NAMES = ["Aruzhan Bekova", "Alikhan Serik", "Dilnaz Omarova", "Nursultan Ali", "Aisha Kenes", "Dias Nurlanuly",
                 "Tomiris Zhan", "Adil Bolat", "Zhansaya Murat", "Miras Askaruly", "Amina Daurenkyzy",
                 "Sultan Yerlanuly", "Ayaulym Sapar", "Beibarys Timur", "Kamila Arman", "Ansar Dulat",
                 "Malika Nurbol", "Yernur Kanat", "Inkar Bakyt", "Abylai Marat", "Aidana Serikbay",
                 "Rauan Ermek", "Saida Ilyas", "Temirlan Aidos", "Moldir Talgat", "Arsen Nurzhan",
                 "Asylzhan Beken", "Diana Kim", "Ivan Petrov", "Elena Smirnova"]

CATEGORY_MIX = {"Academic": 12, "Registration & Enrollment": 11, "Finance & Scholarships": 13, "IT Support": 16,
                "Dormitory & Housing": 11, "Documents & Certificates": 12, "Library": 7, "Health & Wellbeing": 6,
                "International Office": 6, "Other": 6}

# Vague texts the classifier cannot route on its own -> Needs Review / triage demo data.
VAGUE = [("Question", "help please"), ("Help", "I have a problem"), ("Вопрос", "помогите пожалуйста"),
         ("Сұрақ", "көмектесіңізші"), ("Urgent", "please help asap!!")]
STUDENT_REPLIES = ["Thank you!", "Here are the details you asked for.", "It works now, thanks.",
                   "Спасибо, всё понятно.", "Рахмет!", "I attached the screenshot."]


def reset_db() -> None:
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    # Versioned artifacts from retraining belong to the dropped registry; the default model stays.
    for sub in ("classifier", "priority"):
        shutil.rmtree(get_settings().model_dir / sub, ignore_errors=True)


def create_schema() -> None:
    try:
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        command.upgrade(cfg, "head")
    except Exception as exc:  # pragma: no cover - fallback for environments without alembic files
        print(f"Alembic upgrade failed ({exc}); falling back to metadata.create_all")
        Base.metadata.create_all(engine)


def seed_reference(db: Session) -> dict:
    units = {}
    for name, slug, email in UNITS:
        u = Unit(name=name, email=email, is_triage=slug == "triage",
                 working_hours="Mon-Fri 09:00-18:00" if slug != "medical" else "Mon-Sun 00:00-23:59")
        db.add(u)
        units[slug] = u
    db.flush()
    by_name = {u.name: u for u in units.values()}
    for name, unit_name, wf, weight in CATEGORIES:
        c = Category(name=name, unit_id=by_name[unit_name].id, default_workflow=wf, base_priority_weight=weight)
        db.add(c)
        db.flush()
        db.add(RoutingRule(category_id=c.id, unit_id=by_name[unit_name].id))
    for prio, (fr, res) in sla.DEFAULT_POLICIES.items():
        db.add(SLAPolicy(priority=prio, first_response_hours=fr, resolution_hours=res, use_working_hours=False))
    for kw, w, crit, lang in urgency.DEFAULT_KEYWORDS:
        db.add(UrgencyKeyword(keyword=kw, weight=w, is_critical=crit, language=lang))
    db.flush()
    return units


def seed_users(db: Session, units: dict, rng: random.Random) -> dict:
    pw = hash_password(DEMO_PASSWORD)
    admin = User(name="System Administrator", email="admin@qoldau.edu.kz", password_hash=pw, role=Role.ADMIN)
    db.add(admin)
    agents_by_unit: dict[int, list[User]] = {}
    names = iter(AGENT_NAMES)
    for i, (name, slug, _) in enumerate(UNITS):
        unit = units[slug]
        head = User(name=HEAD_NAMES[i], email=f"head.{slug}@qoldau.edu.kz", password_hash=pw, role=Role.UNIT_HEAD,
                    unit_id=unit.id)
        db.add(head)
        db.flush()
        unit.head_user_id = head.id
        n_agents = 3 if slug in ("finance", "it", "registrar") else 2
        agents_by_unit[unit.id] = []
        for k in range(n_agents):
            a = User(name=next(names), email=f"agent{k + 1}.{slug}@qoldau.edu.kz", password_hash=pw,
                     role=Role.AGENT, unit_id=unit.id, language=rng.choice(["en", "ru", "kz"]))
            db.add(a)
            agents_by_unit[unit.id].append(a)
    students = []
    for i, name in enumerate(STUDENT_NAMES):
        email = "student@qoldau.edu.kz" if i == 0 else f"student{i + 1}@qoldau.edu.kz"
        s = User(name=name, email=email, password_hash=pw, role=Role.STUDENT, language=rng.choice(["en", "ru", "kz"]))
        db.add(s)
        students.append(s)
    db.flush()
    return {"admin": admin, "students": students, "agents_by_unit": agents_by_unit}


def _stamp(db: Session, req: Request, when) -> None:
    """Backdate the latest history/routing rows of a request to the simulated time."""
    db.flush()
    for model in (StatusHistory, RoutingLog):
        row = db.query(model).filter_by(request_id=req.id).order_by(model.id.desc()).first()
        if row and row.created_at > when:
            row.created_at = when


def _move(db, req, to, actor, when, note=None):
    from .services import workflow
    workflow.transition(db, req, to, actor=actor, reason="manual", note=note, notify_student=False)
    if to == Status.RESOLVED:
        req.resolved_at = when
    if to == Status.CLOSED:
        req.closed_at = when
    if to == Status.WAITING:
        req.sla_paused_at = when
    _stamp(db, req, when)
    req.updated_at = when


def seed_requests(db: Session, people: dict, rng: random.Random, n: int = 520) -> None:
    now = utcnow()
    cats = {c.name: c for c in db.query(Category)}
    weights = list(CATEGORY_MIX.items())
    recent = min(45, n // 10)  # a busier last day and a half keeps the Kanban "New" column populated
    times = sorted([now - timedelta(days=rng.uniform(1.5, 90)) for _ in range(n - recent)]
                   + [now - timedelta(hours=rng.uniform(0.2, 36)) for _ in range(recent)])
    times[-1] = now - timedelta(minutes=20)
    for i, created in enumerate(times):
        cat_name = rng.choices([w[0] for w in weights], [w[1] for w in weights])[0]
        subject, description = dataset.sample_subject(cat_name, rng)
        if rng.random() < 0.04:
            subject, description = rng.choice(VAGUE)
        if rng.random() < 0.08 and cat_name not in ("Other", "Library"):
            description += rng.choice([" The deadline is tomorrow.", " I need it today, it's urgent.",
                                       " Срочно, завтра дедлайн."])
        # REQ-2026-00123 belongs to the main demo student (US11 acceptance scenario).
        student = people["students"][0] if i == 122 else rng.choice(people["students"])
        student_cat = cats[cat_name].id if rng.random() < 0.6 else None
        req = pipeline.submit(db, student, subject, description, student_cat, now=created)
        db.flush()
        for model in (StatusHistory, RoutingLog):
            for row in db.query(model).filter_by(request_id=req.id):
                row.created_at = created + timedelta(seconds=1)
        db.query(StatusHistory).filter_by(request_id=req.id, from_status=None).update({"created_at": created})

        age_h = (now - created).total_seconds() / 3600
        unit_agents = people["agents_by_unit"].get(req.unit_id or -1, [])
        agent = req.assignee or (rng.choice(unit_agents) if unit_agents else None)

        # Needs Review -> agent confirms the true category (sometimes different from the AI guess).
        if req.status == Status.NEEDS_REVIEW:
            if age_h < 24:
                continue
            triage_agent = rng.choice(people["agents_by_unit"][routing.triage_unit(db).id])
            t = created + timedelta(minutes=rng.uniform(10, 240))
            pipeline.override(db, req, triage_agent, "confirmed after reading the request", category_id=cats[cat_name].id)
            _stamp(db, req, t)
            agent = req.assignee or (rng.choice(people["agents_by_unit"].get(req.unit_id, [triage_agent])))
        elif req.ai_category and age_h > 3 and (req.ai_category.name != cat_name or rng.random() < 0.06):
            if req.ai_category.name == cat_name:
                # Simulated real-world miss: the agent judges the runner-up category to be the right one.
                cat_name = (req.ai_alternatives or [{}, {"category": "Other"}])[1]["category"]
            # Misclassification corrected by an agent -> ai_feedback (drives the AI accuracy KPI).
            t = created + timedelta(minutes=rng.uniform(5, 120))
            pipeline.override(db, req, agent or people["admin"], "wrong category", category_id=cats[cat_name].id)
            _stamp(db, req, t)
            agent = req.assignee or agent

        if req.status != Status.ROUTED or agent is None:
            continue
        if req.assignee_id is None and age_h > 2:
            req.assignee_id, req.assignee = agent.id, agent
        if age_h < 10 and rng.random() < 0.6:
            continue  # fresh requests still waiting in the queue

        fr_hours, res_hours = sla.policy_hours(db)[req.priority]
        late = rng.random() < 0.12
        t_start = created + timedelta(hours=rng.uniform(0.05, fr_hours * (1.4 if late else 0.7)))
        if t_start > now:
            continue
        _move(db, req, Status.IN_PROGRESS, agent, t_start)
        reply_t = t_start + timedelta(minutes=rng.uniform(1, 30))
        if reply_t < now:
            db.add(Message(request_id=req.id, author_id=agent.id, body=_agent_reply(req, rng),
                           created_at=reply_t, read_at=reply_t + timedelta(minutes=30)))
            req.first_response_at = reply_t
        if rng.random() < 0.25:
            t_wait = reply_t + timedelta(minutes=rng.uniform(5, 60))
            if t_wait > now:
                continue
            _move(db, req, Status.WAITING, agent, t_wait)
            if age_h < 30 and rng.random() < 0.6:
                continue
            t_back = t_wait + timedelta(hours=rng.uniform(0.5, 20))
            if t_back > now:
                continue
            db.add(Message(request_id=req.id, author_id=req.student_id, body=rng.choice(STUDENT_REPLIES),
                           created_at=t_back))
            sla.resume(req, t_back)
            _move(db, req, Status.IN_PROGRESS, req.student, t_back, note="Student replied")
        t_res = t_start + timedelta(hours=rng.uniform(0.5, res_hours * (1.5 if late else 0.6)))
        if t_res > now or rng.random() < 0.08:
            continue
        _move(db, req, Status.RESOLVED, agent, t_res)
        if req.sla_resolution_due and t_res > req.sla_resolution_due:
            req.sla_breached = True
        if (req.sla_first_response_due and req.first_response_at
                and req.first_response_at > req.sla_first_response_due):
            req.sla_breached = True
        if rng.random() < 0.65:
            rating = rng.choices([5, 4, 3, 2, 1], [48, 30, 12, 6, 4])[0]
            db.add(CSAT(request_id=req.id, rating=rating, comment=rng.choice(["", "", "Fast and helpful",
                                                                              "Thanks!", "Took too long"]),
                        created_at=t_res + timedelta(hours=2)))
        if (now - t_res).days >= 7:
            _move(db, req, Status.CLOSED, None, t_res + timedelta(days=7))
        if i % 100 == 0:
            db.flush()
    db.flush()
    # Two fresh vague requests so the Triage queue has something to review.
    pipeline.submit(db, people["students"][0], "Help", "help please", None, now=now - timedelta(minutes=50))
    pipeline.submit(db, people["students"][3], "Вопрос", "помогите пожалуйста", None, now=now - timedelta(minutes=15))
    # Demo: escalate breached open requests so the SLA badges & escalation views have data.
    sla.run_tick(db, now=now)


def _agent_reply(req: Request, rng: random.Random) -> str:
    """Category answer in the request's language, sometimes greeting the student by name (masked when reused)."""
    lang = embeddings.detect_language(f"{req.subject} {req.description}")
    cat = req.category.name if req.category else "Other"
    text = kb_seed.CATEGORY_REPLIES.get(cat, kb_seed.CATEGORY_REPLIES["Other"])[lang]
    if rng.random() < 0.5 and req.student:
        text = kb_seed.GREETING[lang].format(name=req.student.name.split()[0]) + " " + text
    return text


def register_model(db: Session) -> None:
    clf, metrics = load_or_train()
    metrics = metrics or {}
    db.query(ModelRegistry).update({ModelRegistry.is_active: False, ModelRegistry.status: "archived"})
    db.add(ModelRegistry(version=clf.version, model_type="classifier", algorithm=ALGORITHM,
                         accuracy=metrics.get("accuracy", 0), macro_f1=metrics.get("macro_f1", 0),
                         metrics={k: v for k, v in metrics.items() if k != "per_class"},
                         train_size=metrics.get("train_size", 0), status="active", is_active=True,
                         artifact_path=None, trained_at=utcnow() - timedelta(days=60)))


def seed_knowledge_base(db: Session, rng: random.Random) -> None:
    """20 published FAQ topics x KZ/RU/EN, authored by the unit head of the responsible unit, + 15 reply templates."""
    admin = db.query(User).filter_by(role=Role.ADMIN).first()
    cats = {c.name: c for c in db.query(Category)}
    now = utcnow()
    for slug, (cat_name, langs) in kb_seed.FAQ.items():
        cat = cats[cat_name]
        unit = db.get(Unit, cat.unit_id) if cat.unit_id else None
        author = unit.head_user_id if unit and unit.head_user_id else admin.id
        when = now - timedelta(days=rng.uniform(20, 60))
        for lang, (title, body, tags) in langs.items():
            views = rng.randint(5, 180)
            a = FAQArticle(slug=slug, title=title, body=schemas.sanitize_html(body), category_id=cat.id,
                           unit_id=unit.id if unit else None, language=lang, tags=tags, status="published", version=1,
                           views=views, helpful_yes=int(views * rng.uniform(0.2, 0.5)),
                           helpful_no=int(views * rng.uniform(0.0, 0.08)), author_id=author, approved_by=author,
                           created_at=when, updated_at=when, published_at=when)
            db.add(a)
            db.flush()
            db.add(FAQArticleVersion(article_id=a.id, version=1, title=a.title, body=a.body, category_id=cat.id,
                                     language=lang, tags=tags, status="published", editor_id=author, created_at=when))
    for cat_name, lang, title, body in kb_seed.TEMPLATES:
        cat = cats[cat_name]
        db.add(ReplyTemplate(title=title, body=body, category_id=cat.id, unit_id=cat.unit_id, language=lang,
                             usage_count=rng.randint(0, 40), author_id=admin.id, created_at=now - timedelta(days=30),
                             updated_at=now - timedelta(days=30)))
    db.flush()


def seed_demo_models(db: Session, rng: random.Random) -> None:
    """Sprint 4 Review: classifier v1.1 (archived) and v1.2 (active) trained by the real pipeline, then 260
    agent-reviewed labels (confirmations + corrections) collected since v1.2, so "Retrain" produces v1.3."""
    from .ml import training
    now = utcnow()
    # Seed overrides happened when the requests were handled, not now.
    for fb in db.query(AIFeedback):
        req = db.get(Request, fb.request_id)
        fb.created_at = req.created_at + timedelta(minutes=rng.uniform(5, 120))
    db.commit()
    for age in (30, 14):
        run = TrainingRun(status="queued", trigger="manual", force=True, created_at=now - timedelta(days=age))
        db.add(run)
        db.commit()
        training.run_training(run.id)
        db.expire_all()
        for model_type in ("classifier", "priority"):
            reg = db.query(ModelRegistry).filter_by(model_type=model_type, training_run_id=run.id).first()
            if reg is None:
                continue
            if not reg.is_active:
                training.activate(db, reg, None, action="promote")
            reg.trained_at = reg.activated_at = now - timedelta(days=age)
        run.started_at, run.finished_at = now - timedelta(days=age), now - timedelta(days=age) + timedelta(seconds=4)
        db.commit()
    db.query(AuditLog).filter(AuditLog.entity == "model").update({AuditLog.created_at: now - timedelta(days=14)})

    reviewed = (db.query(Request).filter(Request.ai_category_id.isnot(None), Request.category_id.isnot(None))
                .order_by(Request.created_at.desc()).limit(600).all())
    agents = db.query(User).filter(User.role == Role.AGENT).all()
    for req in rng.sample(reviewed, min(260, len(reviewed))):
        same = req.category_id == req.ai_category_id
        db.add(AIFeedback(request_id=req.id, text=f"{req.subject}\n{req.description}",
                          predicted_category=req.ai_category.name, corrected_category=req.category.name,
                          predicted_priority=req.ai_priority, agent_id=(req.assignee or rng.choice(agents)).id,
                          reason="quality review: label confirmed" if same else "quality review: category corrected",
                          model_version=req.model_version, created_at=now - timedelta(days=rng.uniform(0.1, 13))))
    db.commit()


def run(reset: bool = False, n: int = 520, demo: bool = False) -> None:
    if reset:
        reset_db()
    create_schema()
    rng = random.Random(2026)
    db = SessionLocal()
    original_is_online = routing.is_online
    routing.is_online = lambda u: True  # every agent counts as online while generating history
    embeddings.AUTO_INDEX = False  # index once at the end instead of per resolved request
    try:
        if db.query(Unit).count():
            if not db.query(FAQArticle).count():  # database from Sprints 1-3: add the Sprint 4 knowledge base
                seed_knowledge_base(db, rng)
                print(f"Added knowledge base; embeddings: {embeddings.reindex_all(db)}")
                db.commit()
            else:
                print("Database already seeded. Use --reset to re-seed.")
            return
        units = seed_reference(db)
        people = seed_users(db, units, rng)
        register_model(db)
        db.commit()
        seed_requests(db, people, rng, n)
        seed_knowledge_base(db, rng)
        # Seeding generates thousands of notifications/emails; keep the demo inboxes clean.
        db.query(Notification).delete()
        db.query(EmailOutbox).delete()
        db.commit()
        if demo:
            seed_demo_models(db, rng)
        counts = embeddings.reindex_all(db)
        db.commit()
        total = db.query(Request).count()
        print(f"Seeded {total} requests, {db.query(User).count()} users, {db.query(AIFeedback).count()} AI feedback rows.")
        print(f"Knowledge base: {db.query(FAQArticle).count()} FAQ articles, {db.query(ReplyTemplate).count()} "
              f"reply templates; embeddings {counts}.")
        if demo:
            versions = ", ".join(f"{m.model_type} {m.version} ({m.status})" for m in
                                 db.query(ModelRegistry).order_by(ModelRegistry.model_type, ModelRegistry.id))
            print(f"Models: {versions}")
        print(f"Demo logins (password {DEMO_PASSWORD}): student@qoldau.edu.kz, agent1.it@qoldau.edu.kz, "
              f"head.library@qoldau.edu.kz, admin@qoldau.edu.kz")
    finally:
        routing.is_online = original_is_online
        embeddings.AUTO_INDEX = True
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("-n", type=int, default=520)
    ap.add_argument("--demo", action="store_true", help="Sprint 4 Review data: model versions + 260 new labels")
    args = ap.parse_args()
    run(reset=args.reset, n=args.n, demo=args.demo)
