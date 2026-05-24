import sys
import os
import asyncio
import shutil
import logging
from datetime import datetime
from typing import List, Dict

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox, QSplitter,
    QGroupBox, QStatusBar, QInputDialog, QProgressBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon

# Add parent dir to path so src.* imports work when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import init_db, Session, UserProfile, Resume, JobPosting, TailoredResume, Application
from src.mcp_client import MCPClient
from src.ats_tailor import ATSTailor
from src.browser_bot import BrowserBot
from src.utils import setup_logging, load_config

setup_logging()
config = load_config()

# ──────────────────────────────────────────────
# Dark-mode stylesheet
# ──────────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #16213e;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    background-color: #16213e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #0f3460;
    font-weight: bold;
    font-size: 13px;
}
QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover  { background-color: #e94560; }
QPushButton:pressed { background-color: #c73652; }
QPushButton:disabled { background-color: #444; color: #888; }
QLineEdit {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e0e0e0;
}
QLineEdit:focus { border: 1px solid #e94560; }
QListWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 5px;
    alternate-background-color: #1a1a2e;
}
QListWidget::item:selected { background-color: #e94560; color: white; }
QListWidget::item:hover    { background-color: #0f3460; }
QTextEdit {
    background-color: #0d0d1a;
    border: 1px solid #0f3460;
    border-radius: 5px;
    color: #00ff88;
    font-family: 'Consolas', monospace;
    font-size: 12px;
}
QTabWidget::pane  { border: 1px solid #0f3460; background-color: #16213e; }
QTabBar::tab      { background-color: #16213e; color: #aaa; padding: 8px 16px; border-radius: 4px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #e94560; color: white; }
QTabBar::tab:hover    { background-color: #0f3460; color: white; }
QTableWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    gridline-color: #0f3460;
    color: #e0e0e0;
}
QTableWidget::item:selected { background-color: #e94560; }
QHeaderView::section {
    background-color: #0f3460;
    color: white;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #0f3460;
    border-radius: 4px;
    background-color: #16213e;
    text-align: center;
    color: white;
}
QProgressBar::chunk { background-color: #e94560; border-radius: 4px; }
QStatusBar { background-color: #0f3460; color: #e0e0e0; }
QScrollBar:vertical {
    background: #16213e; width: 10px; border-radius: 5px;
}
QScrollBar::handle:vertical { background: #0f3460; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #e94560; }
"""


# ──────────────────────────────────────────────
# Background worker thread
# ──────────────────────────────────────────────
class Worker(QThread):
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func   = func
        self.args   = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = asyncio.run(self.func(*self.args, **self.kwargs))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────
# Main Application Window
# ──────────────────────────────────────────────
class JobAutomatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🤖 Automated Job Application Software")
        self.setMinimumSize(1300, 820)

        self.session     = Session()
        self.mcp_client  = MCPClient()
        self.ats_tailor  = ATSTailor()
        self.browser_bot = BrowserBot(headless=False)
        self._workers    = []   # keep references to prevent GC

        self.setStyleSheet(DARK_STYLE)
        self._init_ui()
        self._init_status_bar()
        init_db()
        self._load_profiles()
        self._refresh_applications_table()

    # ── UI Layout ────────────────────────────────
    def _init_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(8)
        root_layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header = QLabel("🤖  Automated Job Application Software")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #e94560; padding: 8px;")
        root_layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        root_layout.addWidget(tabs)

        tabs.addTab(self._build_dashboard_tab(),    "📋  Dashboard")
        tabs.addTab(self._build_jobs_tab(),         "🔍  Job Search")
        tabs.addTab(self._build_applications_tab(), "📨  Applications")
        tabs.addTab(self._build_log_tab(),          "📜  Log")

    def _build_dashboard_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setSpacing(10)

        # ── Left: Profile Management ──
        left = QGroupBox("👤  User Profiles")
        ll = QVBoxLayout(left)
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        btn_add_profile = QPushButton("➕  Add Profile")
        btn_add_profile.clicked.connect(self._add_profile)
        btn_del_profile = QPushButton("🗑  Delete Profile")
        btn_del_profile.clicked.connect(self._delete_profile)
        ll.addWidget(self.profile_list)
        ll.addWidget(btn_add_profile)
        ll.addWidget(btn_del_profile)

        # ── Centre: Resume Management ──
        centre = QGroupBox("📄  Resumes")
        cl = QVBoxLayout(centre)
        self.resume_list = QListWidget()
        btn_upload = QPushButton("📤  Upload Resume")
        btn_upload.clicked.connect(self._upload_resume)
        btn_del_resume = QPushButton("🗑  Delete Resume")
        btn_del_resume.clicked.connect(self._delete_resume)
        cl.addWidget(self.resume_list)
        cl.addWidget(btn_upload)
        cl.addWidget(btn_del_resume)

        # ── Right: Quick Stats ──
        right = QGroupBox("📊  Quick Stats")
        rl = QVBoxLayout(right)
        self.stat_profiles   = QLabel("Profiles: 0")
        self.stat_resumes    = QLabel("Resumes: 0")
        self.stat_jobs       = QLabel("Jobs Found: 0")
        self.stat_applied    = QLabel("Applications: 0")
        for lbl in (self.stat_profiles, self.stat_resumes, self.stat_jobs, self.stat_applied):
            lbl.setFont(QFont("Segoe UI", 13))
            lbl.setStyleSheet("padding: 10px; border: 1px solid #0f3460; border-radius:6px; margin:4px;")
            rl.addWidget(lbl)
        rl.addStretch()

        layout.addWidget(left,   2)
        layout.addWidget(centre, 2)
        layout.addWidget(right,  1)
        return w

    def _build_jobs_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Search bar row
        search_row = QHBoxLayout()
        self.kw_input  = QLineEdit(); self.kw_input.setPlaceholderText("🔑  Keywords  (e.g. Python Developer)")
        self.loc_input = QLineEdit(); self.loc_input.setPlaceholderText("📍  Location  (e.g. Remote, Bangalore)")
        self.limit_input = QLineEdit("5"); self.limit_input.setFixedWidth(60)
        btn_search = QPushButton("🔍  Search")
        btn_search.clicked.connect(self._search_jobs)
        search_row.addWidget(self.kw_input, 3)
        search_row.addWidget(self.loc_input, 2)
        search_row.addWidget(QLabel("Limit:")); search_row.addWidget(self.limit_input)
        search_row.addWidget(btn_search)
        layout.addLayout(search_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Job results list + detail panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.job_list = QListWidget()
        self.job_list.currentItemChanged.connect(self._on_job_selected)
        self.job_list.itemDoubleClicked.connect(self._show_job_detail_dialog)

        self.job_detail = QTextEdit()
        self.job_detail.setReadOnly(True)
        self.job_detail.setPlaceholderText("Double-click a job to see details…")

        splitter.addWidget(self.job_list)
        splitter.addWidget(self.job_detail)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter, 1)

        btn_apply = QPushButton("🚀  Tailor Resume & Apply to Selected Job")
        btn_apply.setFixedHeight(40)
        btn_apply.clicked.connect(self._tailor_and_apply)
        layout.addWidget(btn_apply)
        return w

    def _build_applications_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.app_table = QTableWidget(0, 6)
        self.app_table.setHorizontalHeaderLabels(["Job Title", "Company", "Source", "Status", "Match Score", "Applied At"])
        self.app_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.app_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.app_table.setAlternatingRowColors(True)
        layout.addWidget(self.app_table)

        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.clicked.connect(self._refresh_applications_table)
        layout.addWidget(btn_refresh)
        return w

    def _build_log_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Activity log will appear here…")
        btn_clear = QPushButton("🧹  Clear Log")
        btn_clear.clicked.connect(self.log_view.clear)
        layout.addWidget(self.log_view, 1)
        layout.addWidget(btn_clear)
        return w

    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    # ── Helpers ──────────────────────────────────
    def _log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        colours = {"INFO": "#00ff88", "WARN": "#ffcc00", "ERROR": "#ff4444"}
        colour  = colours.get(level, "#00ff88")
        self.log_view.append(f'<span style="color:#888">[{ts}]</span> <span style="color:{colour}">{msg}</span>')
        self.status_bar.showMessage(msg, 5000)
        logging.info(msg)

    def _current_profile(self) -> Optional[UserProfile]:
        item = self.profile_list.currentItem()
        if not item:
            return None
        email = item.data(Qt.ItemDataRole.UserRole)
        return self.session.query(UserProfile).filter_by(email=email).first()

    def _current_resume(self) -> Optional[Resume]:
        profile = self._current_profile()
        item    = self.resume_list.currentItem()
        if not profile or not item:
            return None
        resume_id = item.data(Qt.ItemDataRole.UserRole)
        return self.session.query(Resume).get(resume_id)

    def _current_job(self) -> Optional[JobPosting]:
        item = self.job_list.currentItem()
        if not item:
            return None
        return self.session.query(JobPosting).get(item.data(Qt.ItemDataRole.UserRole))

    def _update_stats(self):
        self.stat_profiles.setText(f"👤  Profiles: {self.session.query(UserProfile).count()}")
        self.stat_resumes.setText(f"📄  Resumes: {self.session.query(Resume).count()}")
        self.stat_jobs.setText(f"📋  Jobs Found: {self.session.query(JobPosting).count()}")
        self.stat_applied.setText(f"📨  Applications: {self.session.query(Application).count()}")

    # ── Profile ───────────────────────────────────
    def _load_profiles(self):
        self.profile_list.clear()
        for p in self.session.query(UserProfile).all():
            item = QListWidgetItem(f"👤  {p.name}  ({p.email})")
            item.setData(Qt.ItemDataRole.UserRole, p.email)
            self.profile_list.addItem(item)
        self._update_stats()

    def _on_profile_selected(self):
        self._load_resumes()

    def _add_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Full Name:")
        if not ok or not name.strip():
            return
        email, ok = QInputDialog.getText(self, "New Profile", "Email Address:")
        if not ok or not email.strip():
            return
        phone, ok = QInputDialog.getText(self, "New Profile", "Phone (optional):")
        if self.session.query(UserProfile).filter_by(email=email.strip()).first():
            QMessageBox.warning(self, "Duplicate", "A profile with this email already exists.")
            return
        p = UserProfile(name=name.strip(), email=email.strip(), phone=phone.strip())
        self.session.add(p)
        self.session.commit()
        self._log(f"Profile created: {name}")
        self._load_profiles()

    def _delete_profile(self):
        profile = self._current_profile()
        if not profile:
            QMessageBox.warning(self, "Warning", "Select a profile first.")
            return
        reply = QMessageBox.question(self, "Confirm", f"Delete profile '{profile.name}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.session.delete(profile)
            self.session.commit()
            self._log(f"Profile deleted: {profile.name}", "WARN")
            self._load_profiles()

    # ── Resumes ───────────────────────────────────
    def _load_resumes(self):
        self.resume_list.clear()
        profile = self._current_profile()
        if not profile:
            return
        for r in profile.resumes:
            label = f"📄  {r.title}" + ("  ★ Primary" if r.is_primary else "")
            item  = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, r.id)
            self.resume_list.addItem(item)

    def _upload_resume(self):
        profile = self._current_profile()
        if not profile:
            QMessageBox.warning(self, "Warning", "Select a profile first.")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Resume", "", "Documents (*.pdf *.docx *.txt)"
        )
        if not file_path:
            return
        title, ok = QInputDialog.getText(self, "Resume Title", "Enter a title for this resume:")
        if not ok or not title.strip():
            return
        resume_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'resumes')
        os.makedirs(resume_dir, exist_ok=True)
        dest = os.path.join(resume_dir, f"{profile.id}_{os.path.basename(file_path)}")
        shutil.copy(file_path, dest)
        is_primary = not bool(profile.resumes)
        r = Resume(user_profile_id=profile.id, title=title.strip(), file_path=dest, is_primary=is_primary)
        self.session.add(r)
        self.session.commit()
        self._log(f"Resume '{title}' uploaded for {profile.name}")
        self._load_resumes()
        self._update_stats()

    def _delete_resume(self):
        resume = self._current_resume()
        if not resume:
            QMessageBox.warning(self, "Warning", "Select a resume first.")
            return
        reply = QMessageBox.question(self, "Confirm", f"Delete resume '{resume.title}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.session.delete(resume)
            self.session.commit()
            self._log(f"Resume deleted: {resume.title}", "WARN")
            self._load_resumes()
            self._update_stats()

    # ── Job Search ────────────────────────────────
    def _search_jobs(self):
        keywords = self.kw_input.text().strip()
        if not keywords:
            QMessageBox.warning(self, "Warning", "Enter at least one keyword.")
            return
        location = self.loc_input.text().strip() or None
        try:
            limit = int(self.limit_input.text().strip())
        except ValueError:
            limit = 5

        self.job_list.clear()
        self.job_detail.clear()
        self.progress_bar.setVisible(True)
        self._log(f"Searching: '{keywords}' | location: '{location}' | limit: {limit}")

        async def _run():
            return self.mcp_client.search_jobs(keywords, location, limit)

        w = Worker(_run)
        w.finished.connect(self._on_jobs_received)
        w.error.connect(lambda e: (self._log(f"Search error: {e}", "ERROR"), self.progress_bar.setVisible(False)))
        self._workers.append(w)
        w.start()

    def _on_jobs_received(self, jobs: List[Dict]):
        self.progress_bar.setVisible(False)
        if not jobs:
            self._log("No jobs found.", "WARN")
            return
        for jd in jobs:
            existing = self.session.query(JobPosting).filter_by(
                job_id_on_source=jd['job_id_on_source'], source=jd['source']
            ).first()
            if not existing:
                jp = JobPosting(
                    source            = jd['source'],
                    job_id_on_source  = jd['job_id_on_source'],
                    title             = jd['title'],
                    company           = jd['company'],
                    location          = jd.get('location', ''),
                    description       = jd.get('description', ''),
                    job_url           = jd['job_url'],
                    posted_date       = datetime.fromisoformat(jd['posted_date']) if 'posted_date' in jd else None,
                )
                self.session.add(jp)
                self.session.commit()
                job_db_id = jp.id
            else:
                job_db_id = existing.id

            item = QListWidgetItem(f"[{jd['source']}]  {jd['title']}  @  {jd['company']}")
            item.setData(Qt.ItemDataRole.UserRole, job_db_id)
            self.job_list.addItem(item)

        self._log(f"Found {len(jobs)} job(s).")
        self._update_stats()

    def _on_job_selected(self):
        job = self._current_job()
        if job:
            self.job_detail.setHtml(
                f"<h2 style='color:#e94560'>{job.title}</h2>"
                f"<b>Company:</b> {job.company}<br>"
                f"<b>Location:</b> {job.location}<br>"
                f"<b>Source:</b> {job.source}<br>"
                f"<b>URL:</b> <a href='{job.job_url}' style='color:#00ff88'>{job.job_url}</a><br><br>"
                f"<b>Description:</b><br><pre style='white-space:pre-wrap;color:#ccc'>{job.description}</pre>"
            )

    def _show_job_detail_dialog(self, item):
        job = self._current_job()
        if job:
            QMessageBox.information(
                self, "Job Details",
                f"Title:    {job.title}\nCompany:  {job.company}\n"
                f"Location: {job.location}\nSource:   {job.source}\n"
                f"URL:      {job.job_url}\n\nDescription:\n{job.description}"
            )

    # ── Tailor & Apply ────────────────────────────
    def _tailor_and_apply(self):
        profile = self._current_profile()
        resume  = self._current_resume()
        job     = self._current_job()

        if not profile:
            QMessageBox.warning(self, "Warning", "Select a user profile on the Dashboard tab.")
            return
        if not resume:
            QMessageBox.warning(self, "Warning", "Select a resume on the Dashboard tab.")
            return
        if not job:
            QMessageBox.warning(self, "Warning", "Select a job from the search results.")
            return

        self._log(f"Starting tailor & apply: '{job.title}' @ {job.company}")
        self.progress_bar.setVisible(True)

        async def _run():
            return await self._perform_application(profile.id, resume.id, job.id)

        w = Worker(_run)
        w.finished.connect(lambda ok: (
            self._log("✅ Application complete!" if ok else "❌ Application failed.", "INFO" if ok else "ERROR"),
            self.progress_bar.setVisible(False),
            self._refresh_applications_table(),
            self._update_stats()
        ))
        w.error.connect(lambda e: (
            self._log(f"Application error: {e}", "ERROR"),
            self.progress_bar.setVisible(False)
        ))
        self._workers.append(w)
        w.start()

    async def _perform_application(self, profile_id: int, resume_id: int, job_id: int) -> bool:
        # Re-fetch inside worker thread session
        profile = self.session.query(UserProfile).get(profile_id)
        resume  = self.session.query(Resume).get(resume_id)
        job     = self.session.query(JobPosting).get(job_id)

        # Read resume file
        try:
            with open(resume.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                resume_content = f.read()
        except Exception:
            resume_content = f"{profile.name}\nSoftware Developer\nSkills: Python, SQL"

        # Tailor
        analysis = self.ats_tailor.analyze_job_description(job.description)
        tailored_content, score = self.ats_tailor.tailor_resume(resume_content, analysis)

        # Save tailored resume
        tailored_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'resumes', 'tailored')
        os.makedirs(tailored_dir, exist_ok=True)
        tailored_path = os.path.join(tailored_dir, f"tailored_{job.job_id_on_source}_{profile.id}.txt")
        with open(tailored_path, 'w', encoding='utf-8') as f:
            f.write(tailored_content)

        tr = TailoredResume(
            base_resume_id  = resume.id,
            job_posting_id  = job.id,
            tailored_file_path = tailored_path,
            match_score     = score,
        )
        self.session.add(tr)
        self.session.commit()

        # Browser automation
        status  = 'Applied'
        success = False
        bot = BrowserBot(headless=False)
        try:
            await bot.launch_browser()
            await bot.navigate(job.job_url)

            form_data = {
                'input[name="name"]':  profile.name,
                'input[name="email"]': profile.email,
            }
            await bot.fill_form(form_data, resume_file_path=tailored_path)

            if await bot.check_for_captcha():
                status  = 'CAPTCHA Required'
                success = False
            else:
                ok = await bot.submit_form()
                status  = 'Applied' if ok else 'Submission Failed'
                success = ok
        except Exception as e:
            status  = 'Automation Error'
            success = False
            logging.error(f"Browser error: {e}")
        finally:
            await bot.close_browser()

        app_rec = Application(
            user_profile_id   = profile.id,
            job_posting_id    = job.id,
            tailored_resume_id= tr.id,
            status            = status,
            notes             = f"ATS Match Score: {score}%",
        )
        self.session.add(app_rec)
        self.session.commit()
        return success

    # ── Applications Table ────────────────────────
    def _refresh_applications_table(self):
        apps = self.session.query(Application).all()
        self.app_table.setRowCount(0)
        for app in apps:
            row = self.app_table.rowCount()
            self.app_table.insertRow(row)
            jp  = app.job_posting
            tr  = app.tailored_resume
            self.app_table.setItem(row, 0, QTableWidgetItem(jp.title if jp else "—"))
            self.app_table.setItem(row, 1, QTableWidgetItem(jp.company if jp else "—"))
            self.app_table.setItem(row, 2, QTableWidgetItem(jp.source if jp else "—"))
            status_item = QTableWidgetItem(app.status)
            colour = {"Applied": "#00ff88", "CAPTCHA Required": "#ffcc00"}.get(app.status, "#ff4444")
            status_item.setForeground(QColor(colour))
            self.app_table.setItem(row, 3, status_item)
            self.app_table.setItem(row, 4, QTableWidgetItem(f"{tr.match_score}%" if tr else "—"))
            self.app_table.setItem(row, 5, QTableWidgetItem(
                app.applied_at.strftime("%Y-%m-%d %H:%M") if app.applied_at else "—"
            ))
        self._update_stats()

    # ── Cleanup ───────────────────────────────────
    def closeEvent(self, event):
        self.session.close()
        logging.info("Application closed.")
        event.accept()


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = JobAutomatorApp()
    window.show()
    sys.exit(app.exec())
