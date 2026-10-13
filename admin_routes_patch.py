# Merge this snippet into your existing app.py. Do not replace the whole app.py.
import csv, io
from flask import request, make_response

def _admin_required():
    return "admin_id" in session

@app.route("/admin/dashboard")
def admin_dashboard():
    if not _admin_required(): return redirect(url_for("admin_login"))
    with get_database() as c:
        admin_count=c.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        user_count=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        document_count=c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        activity_count=c.execute("SELECT COUNT(*) FROM activity_logs").fetchone()[0]
        saved_result_count=c.execute("SELECT COUNT(*) FROM saved_results").fetchone()[0]
        recent_activities=c.execute("""SELECT a.action,a.details,a.created_at,u.username
          FROM activity_logs a LEFT JOIN users u ON u.id=a.user_id
          ORDER BY a.id DESC LIMIT 12""").fetchall()
    return render_template("admin_dashboard.html",admin_username=session.get("admin_username","Admin"),
      admin_count=admin_count,user_count=user_count,document_count=document_count,
      activity_count=activity_count,saved_result_count=saved_result_count,recent_activities=recent_activities)

@app.route("/admin/users")
def admin_users():
    if not _admin_required(): return redirect(url_for("admin_login"))
    q=request.args.get("q","").strip()
    sql="SELECT id,username,email,created_at FROM users"; params=[]
    if q: sql+=" WHERE username LIKE ? OR email LIKE ?"; params=[f"%{q}%",f"%{q}%"]
    with get_database() as c: users=c.execute(sql+" ORDER BY id DESC",params).fetchall()
    return render_template("admin_users.html",users=users,search_query=q)

@app.route("/admin/documents")
def admin_documents():
    if not _admin_required(): return redirect(url_for("admin_login"))
    q=request.args.get("q","").strip()
    sql="""SELECT d.id,d.filename,d.uploaded_at,u.username,u.email FROM documents d
      LEFT JOIN users u ON u.id=d.user_id"""; params=[]
    if q: sql+=" WHERE d.filename LIKE ? OR u.username LIKE ?"; params=[f"%{q}%",f"%{q}%"]
    with get_database() as c: documents=c.execute(sql+" ORDER BY d.id DESC",params).fetchall()
    return render_template("admin_documents.html",documents=documents,search_query=q)

@app.route("/admin/activity/export")
def admin_activity_export():
    if not _admin_required(): return redirect(url_for("admin_login"))
    with get_database() as c:
        rows=c.execute("""SELECT a.id,u.username,a.action,a.details,a.created_at
          FROM activity_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC""").fetchall()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["id","username","action","details","created_at"])
    for r in rows: w.writerow([r["id"],r["username"],r["action"],r["details"],r["created_at"]])
    response=make_response(out.getvalue()); response.headers["Content-Type"]="text/csv; charset=utf-8"
    response.headers["Content-Disposition"]='attachment; filename="summarix_activity.csv"'
    return response
