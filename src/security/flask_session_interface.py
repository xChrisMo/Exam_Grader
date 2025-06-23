import json
from datetime import datetime, timedelta
import uuid
from typing import Optional, Dict, Any

from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

from src.security.session_manager import SecureSessionManager
from src.database.models import Session as SessionModel, db
from utils.logger import logger


class SecureFlaskSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=False):
        super().__init__(initial)
        self.sid = sid
        self.new = new
        self.modified = False


class SecureSessionInterface(SessionInterface):
    def __init__(self, session_manager: SecureSessionManager, app_secret_key: str):
        self.session_manager = session_manager
        self.app_secret_key = app_secret_key

    def open_session(self, app, request):
        self.session_cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
        sid = request.cookies.get(self.session_cookie_name)
        logger.debug(f"Attempting to open session. Cookie name: {self.session_cookie_name}, SID from cookie: {sid}")
        if not sid:
            logger.debug("No session ID found in cookie. Creating new session.")
            # No session ID in cookie, create a new session
            return SecureFlaskSession(new=True)

        # Try to load session from database using SecureSessionManager
        session_data = self.session_manager.get_session(sid)
        if session_data is None:
            # Session not found or invalid, create a new one
            logger.info(f"Session {sid} not found or invalid in DB. Creating new session.")
            return SecureFlaskSession(new=True)

        # Session found, decrypt and load data
        logger.debug(f"Session {sid} loaded from DB.")
        return SecureFlaskSession(session_data, sid=sid)

    def save_session(self, app, session: SecureFlaskSession, response):
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        samesite = self.get_cookie_samesite(app)

        if not session:
            # If session is empty, delete the cookie and invalidate the DB session
            if session.sid:
                self.session_manager.invalidate_session(session.sid)
                logger.info(f"Invalidated session {session.sid} in DB due to empty session.")
            response.delete_cookie(self.session_cookie_name, domain=domain, path=path)
            return

        if session.modified or session.new:
            # If session is new or modified, save it
            if session.new:
                # Create a new session in the database
                user_id = session.get('user_id') # Assuming user_id is stored in session
                logger.debug(f"New session user_id: {user_id}")
                # Create a new session in the database, even for anonymous users
                # The user_id can be None for anonymous sessions
                # Pass remember_me to create_session to determine session timeout
                sid = self.session_manager.create_session(
                    user_id,
                    dict(session),
                    remember_me=session.get('remember_me', False)
                )
                session.sid = sid

                logger.info(f"New session created and saved to DB: {sid} (user_id: {user_id})")
            else:
                # Update existing session in the database
                self.session_manager.update_session(session.sid, dict(session))
                logger.debug(f"Session {session.sid} updated in DB.")

            # Set the session cookie
            expires = datetime.utcnow() + timedelta(seconds=self.session_manager.session_timeout)
            response.set_cookie(
                self.session_cookie_name,
                session.sid,
                expires=expires,
                httponly=httponly,
                domain=domain,
                path=path,
                secure=secure,
                samesite=samesite,
            )
            logger.debug(f"Setting session cookie. Name: {self.session_cookie_name}, SID: {session.sid}, Expires: {expires}")
        elif session.sid and not session.modified:
            # Session not modified, but update last_accessed in DB to keep it alive
            self.session_manager.update_session_last_accessed(session.sid)
            logger.debug(f"Session {session.sid} last_accessed updated in DB.")


# Add update_session and update_session_last_accessed to SecureSessionManager
def _update_session(self, sid: str, session_data: Dict[str, Any]):
    try:
        session_record = SessionModel.query.filter_by(id=sid).first()
        if session_record:
            encrypted_data = self.encryption.encrypt_data(session_data)
            session_record.data = encrypted_data
            session_record.last_accessed = datetime.utcnow()
            session_record.expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
            db.session.commit()
            logger.debug(f"Session {sid} data updated in DB.")
        else:
            logger.warning(f"Attempted to update non-existent session: {sid}")
    except Exception as e:
        logger.error(f"Failed to update session {sid}: {str(e)}")
        db.session.rollback()

def _update_session_last_accessed(self, sid: str):
    try:
        session_record = SessionModel.query.filter_by(id=sid).first()
        if session_record:
            session_record.last_accessed = datetime.utcnow()
            session_record.expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
            db.session.commit()
            logger.debug(f"Session {sid} last_accessed updated in DB.")
        else:
            logger.warning(f"Attempted to update last_accessed for non-existent session: {sid}")
    except Exception as e:
        logger.error(f"Failed to update session last_accessed {sid}: {str(e)}")
        db.session.rollback()

SecureSessionManager.update_session = _update_session
SecureSessionManager.update_session_last_accessed = _update_session_last_accessed