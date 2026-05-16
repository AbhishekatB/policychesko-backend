from datetime import datetime, timedelta, timezone
import importlib
import logging
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
import jwt

try:
    from app.config import settings
    from app.schemas.models import (
        CashbackActionCreate,
        CashbackClaimCreate,
        EnquiryCreate,
        InvestmentCreate,
        JourneyEnquiryCreate,
        JourneyKycCreate,
        KycCreate,
        Policy,
        PurchaseCreate,
        QuoteCreate,
        WalletRedeemCreate,
    )
except ModuleNotFoundError:
    from config import settings
    from schemas.models import (
        CashbackActionCreate,
        CashbackClaimCreate,
        EnquiryCreate,
        InvestmentCreate,
        JourneyEnquiryCreate,
        JourneyKycCreate,
        KycCreate,
        Policy,
        PurchaseCreate,
        QuoteCreate,
        WalletRedeemCreate,
    )


class DataService:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._use_postgres = bool(settings.database_url)
        self._pg_conn: Any | None = None
        self._use_supabase = bool(settings.supabase_url and settings.supabase_service_key)
        self._client: Any | None = None
        self._sqlite_conn = self._init_sqlite()

        # Publishable/anon keys cannot be used for trusted server-side inserts.
        if settings.supabase_service_key.startswith("sb_publishable_"):
            self._logger.warning(
                "Supabase disabled: SUPABASE_SERVICE_KEY/SUPABASE_KEY is publishable. "
                "Use service_role key for backend writes."
            )
            self._use_supabase = False

        self._policies = [
            Policy(
                id="POL-MOTOR-001",
                name="Only Motor",
                policy_type="motor",
                flow_supported=["new", "renewal"],
                description="Comprehensive motor protection for city and highway rides.",
            ),
            Policy(
                id="POL-HEALTH-001",
                name="Health Policy",
                policy_type="health",
                flow_supported=["new", "renewal"],
                description="Cashless hospitalization support and annual health coverage.",
            ),
        ]
        self._status_store: dict[str, dict[str, Any]] = {}

        if self._use_postgres:
            try:
                psycopg = importlib.import_module("psycopg")
                self._pg_conn = psycopg.connect(settings.database_url, autocommit=True)
            except Exception:
                self._pg_conn = None
                self._use_postgres = False

        if self._use_supabase:
            try:
                supabase = importlib.import_module("supabase")
                create_client = getattr(supabase, "create_client")
                self._client = create_client(settings.supabase_url, settings.supabase_service_key)
            except Exception:
                self._client = None
                self._use_supabase = False
                self._logger.exception("Failed to initialize Supabase client")

    def _init_sqlite(self) -> sqlite3.Connection:
        db_dir = Path(__file__).resolve().parents[2] / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_dir / "policychesko.db", check_same_thread=False)
        conn.execute(
            """
            create table if not exists app_users (
                id integer primary key autoincrement,
                username text unique not null,
                password text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_sessions (
                id integer primary key autoincrement,
                session_id text unique not null,
                username text not null,
                password text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_enquiries (
                id integer primary key autoincrement,
                reference_id text unique not null,
                session_id text not null,
                username text not null,
                full_name text not null,
                email text not null,
                phone_number text not null,
                policy_type text not null,
                flow_type text not null,
                status text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_kyc (
                id integer primary key autoincrement,
                reference_id text unique not null,
                session_id text not null,
                username text not null,
                full_name text not null,
                aadhaar_number text not null,
                pan_number text not null,
                email text not null,
                phone_number text not null,
                nominee_name text not null,
                nominee_age integer not null,
                previous_year_policy_copy_url text,
                rc_copy_url text,
                flow_type text not null,
                policy_type text not null,
                status text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_quotes (
                id integer primary key autoincrement,
                quote_id text unique not null,
                session_id text not null,
                username text not null,
                policy_id text not null,
                policy_type text not null,
                flow_type text not null,
                insured_amount integer not null,
                tenure_years integer not null,
                premium_amount integer not null,
                cashback_amount integer not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_cashback_actions (
                id integer primary key autoincrement,
                action_id text unique not null,
                quote_id text not null,
                session_id text not null,
                username text not null,
                cashback_amount integer not null,
                action text not null,
                status text not null,
                projected_value real,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_payments (
                id integer primary key autoincrement,
                payment_id text unique not null,
                quote_id text not null,
                policy_id text not null,
                policy_type text not null,
                session_id text not null,
                username text not null,
                status text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_cashback_pool (
                id integer primary key autoincrement,
                cashback_id text unique not null,
                quote_id text not null,
                payment_id text not null,
                policy_id text not null,
                policy_type text not null,
                session_id text not null,
                username text not null,
                cashback_amount integer not null,
                status text not null,
                created_at text not null,
                claimed_at text
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_wallet_ledger (
                id integer primary key autoincrement,
                entry_id text unique not null,
                session_id text not null,
                username text not null,
                entry_type text not null,
                source text not null,
                amount integer not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_investments (
                id integer primary key autoincrement,
                investment_id text unique not null,
                session_id text not null,
                username text not null,
                amount integer not null,
                source text not null,
                status text not null,
                annual_rate real not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_user_events (
                id integer primary key autoincrement,
                event_id text unique not null,
                session_id text,
                username text,
                event_type text not null,
                entity_type text,
                entity_id text,
                status text not null,
                details text,
                created_at text not null
            )
            """
        )
        conn.commit()
        return conn

    def _safe_pg_execute(self, query: str, params: tuple[Any, ...]) -> None:
        if not self._pg_conn:
            return
        try:
            with self._pg_conn.cursor() as cur:
                cur.execute(query, params)
        except Exception:
            return

    def _safe_pg_fetchone(self, query: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
        if not self._pg_conn:
            return None
        try:
            with self._pg_conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
        except Exception:
            return None

    def _safe_insert(self, table_name: str, payload: dict[str, Any]) -> None:
        if not self._client:
            return
        try:
            self._client.table(table_name).insert(payload).execute()
        except Exception as exc:
            self._logger.warning("Supabase insert failed for table '%s': %s", table_name, exc)
            # Keep prototype flows available even if DB/table setup is incomplete.
            return

    def _sqlite_execute(self, query: str, params: tuple[Any, ...]) -> None:
        try:
            self._sqlite_conn.execute(query, params)
            self._sqlite_conn.commit()
        except Exception:
            return

    def _sqlite_fetchone(self, query: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
        try:
            cur = self._sqlite_conn.execute(query, params)
            return cur.fetchone()
        except Exception:
            return None

    def _sqlite_fetchall(self, query: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        try:
            cur = self._sqlite_conn.execute(query, params)
            return cur.fetchall()
        except Exception:
            return []

    def _policy_cashback(self, policy_type: str) -> int:
        return 1200 if policy_type == "motor" else 800

    def _storage_backends(self) -> list[str]:
        backends = ["sqlite"]
        if self._pg_conn:
            backends.append("postgres")
        if self._client:
            backends.append("supabase")
        return backends

    def _normalize_pagination(self, page: int, page_size: int) -> tuple[int, int, int]:
        safe_page = max(1, int(page or 1))
        safe_size = min(100, max(1, int(page_size or 20)))
        offset = (safe_page - 1) * safe_size
        return safe_page, safe_size, offset

    def _date_bounds(self, start_date: str | None, end_date: str | None) -> tuple[str | None, str | None]:
        start_bound = None
        end_bound = None
        if start_date:
            start_bound = f"{start_date}T00:00:00"
        if end_date:
            end_bound = f"{end_date}T23:59:59"
        return start_bound, end_bound

    def _assert_active_session(self, session_id: str, username: str) -> None:
        row = self._sqlite_fetchone(
            """
            select 1 from app_sessions
            where session_id = ? and username = ?
            limit 1
            """,
            (session_id, username),
        )
        if not row:
            raise ValueError("Session expired. Please login again.")

    def _log_event(
        self,
        event_type: str,
        status: str,
        session_id: str | None = None,
        username: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        event_id = f"EVT-{uuid4().hex[:12].upper()}"
        self._sqlite_execute(
            """
            insert into app_user_events
            (event_id, session_id, username, event_type, entity_type, entity_id, status, details, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, session_id, username, event_type, entity_type, entity_id, status, details, now),
        )

    def create_login_session(self, username: str, password: str) -> dict[str, str]:
        user_row = self._sqlite_fetchone(
            "select password from app_users where username = ?",
            (username,),
        )
        user_existed = bool(user_row)
        if user_existed:
            stored_password = str(user_row[0])
            if stored_password != password:
                raise ValueError("Invalid username or password.")
        else:
            today_utc = datetime.now(timezone.utc).date().isoformat()
            created_today_row = self._sqlite_fetchone(
                "select count(*) from app_users where substr(created_at, 1, 10) = ?",
                (today_utc,),
            )
            created_today = int((created_today_row or (0,))[0] or 0)
            if created_today >= 10:
                raise ValueError("Daily user creation limit reached. Please try again tomorrow.")
            now_for_user = datetime.now(timezone.utc).isoformat()
            self._sqlite_execute(
                "insert into app_users (username, password, created_at) values (?, ?, ?)",
                (username, password, now_for_user),
            )

        active_session = self._sqlite_fetchone(
            "select session_id from app_sessions where username = ? order by created_at desc limit 1",
            (username,),
        )

        # If a user row was just created, any pre-existing session row for this username is orphaned stale data.
        if active_session and not user_existed:
            self._sqlite_execute("delete from app_sessions where username = ?", (username,))
            active_session = None

        if active_session:
            raise ValueError("User already logged in on another device. Please logout first.")

        session_id = f"SES-{uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        self._sqlite_execute(
            """
            insert into app_sessions (session_id, username, password, created_at)
            values (?, ?, ?, ?)
            """,
            (session_id, username, password, now),
        )
        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into app_sessions (session_id, username, password, created_at)
                values (%s, %s, %s, %s)
                """,
                (session_id, username, password, now),
            )
        if self._client:
            self._safe_insert(
                "app_sessions",
                {
                    "session_id": session_id,
                    "username": username,
                    "password": password,
                    "created_at": now,
                },
            )
        exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_exp_hours)
        access_token = jwt.encode(
            {
                "sub": username,
                "session_id": session_id,
                "exp": exp,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )
        self._log_event(
            event_type="auth.login",
            status="success",
            session_id=session_id,
            username=username,
            entity_type="session",
            entity_id=session_id,
            details="User login successful",
        )
        return {
            "session_id": session_id,
            "username": username,
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Login successful.",
        }

    def logout_session(self, session_id: str, username: str) -> dict[str, str]:
        self._assert_active_session(session_id, username)
        self._sqlite_execute(
            "delete from app_sessions where session_id = ? and username = ?",
            (session_id, username),
        )
        self._log_event(
            event_type="auth.logout",
            status="success",
            session_id=session_id,
            username=username,
            entity_type="session",
            entity_id=session_id,
            details="User logout successful",
        )
        return {
            "status": "logged_out",
            "message": "Logout successful.",
        }

    def create_journey_enquiry(self, payload: JourneyEnquiryCreate) -> dict[str, str]:
        self._assert_active_session(payload.session_id, payload.username)
        reference_id = f"ENQ-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        self._sqlite_execute(
            """
            insert into app_enquiries
            (reference_id, session_id, username, full_name, email, phone_number, policy_type, flow_type, status, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference_id,
                payload.session_id,
                payload.username,
                payload.full_name,
                payload.email,
                payload.phone_number,
                payload.policy_type,
                payload.flow_type,
                "enquiry_received",
                now,
            ),
        )
        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into app_enquiries
                (reference_id, session_id, username, full_name, email, phone_number, policy_type, flow_type, status, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    reference_id,
                    payload.session_id,
                    payload.username,
                    payload.full_name,
                    payload.email,
                    payload.phone_number,
                    payload.policy_type,
                    payload.flow_type,
                    "enquiry_received",
                    now,
                ),
            )
        if self._client:
            self._safe_insert(
                "app_enquiries",
                {
                    "reference_id": reference_id,
                    "session_id": payload.session_id,
                    "username": payload.username,
                    "full_name": payload.full_name,
                    "email": payload.email,
                    "phone_number": payload.phone_number,
                    "policy_type": payload.policy_type,
                    "flow_type": payload.flow_type,
                    "status": "enquiry_received",
                    "created_at": now,
                },
            )
        self._log_event(
            event_type="journey.enquiry",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="enquiry",
            entity_id=reference_id,
            details=f"policy_type={payload.policy_type}, flow_type={payload.flow_type}",
        )
        return {
            "reference_id": reference_id,
            "status": "enquiry_received",
            "message": "Enquiry sent successfully.",
        }

    def create_journey_kyc(self, payload: JourneyKycCreate) -> dict[str, str]:
        self._assert_active_session(payload.session_id, payload.username)
        reference_id = f"KYC-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        self._sqlite_execute(
            """
            insert into app_kyc
            (reference_id, session_id, username, full_name, aadhaar_number, pan_number, email, phone_number,
             nominee_name, nominee_age, previous_year_policy_copy_url, rc_copy_url, flow_type, policy_type, status, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference_id,
                payload.session_id,
                payload.username,
                payload.full_name,
                payload.aadhaar_number,
                payload.pan_number,
                payload.email,
                payload.phone_number,
                payload.nominee_name,
                payload.nominee_age,
                payload.previous_year_policy_copy_url,
                payload.rc_copy_url,
                payload.flow_type,
                payload.policy_type,
                "kyc_verified",
                now,
            ),
        )
        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into app_kyc
                (reference_id, session_id, username, full_name, aadhaar_number, pan_number, email, phone_number,
                 nominee_name, nominee_age, previous_year_policy_copy_url, rc_copy_url, flow_type, policy_type, status, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    reference_id,
                    payload.session_id,
                    payload.username,
                    payload.full_name,
                    payload.aadhaar_number,
                    payload.pan_number,
                    payload.email,
                    payload.phone_number,
                    payload.nominee_name,
                    payload.nominee_age,
                    payload.previous_year_policy_copy_url,
                    payload.rc_copy_url,
                    payload.flow_type,
                    payload.policy_type,
                    "kyc_verified",
                    now,
                ),
            )
        if self._client:
            self._safe_insert(
                "app_kyc",
                {
                    "reference_id": reference_id,
                    "session_id": payload.session_id,
                    "username": payload.username,
                    "full_name": payload.full_name,
                    "aadhaar_number": payload.aadhaar_number,
                    "pan_number": payload.pan_number,
                    "email": payload.email,
                    "phone_number": payload.phone_number,
                    "nominee_name": payload.nominee_name,
                    "nominee_age": payload.nominee_age,
                    "previous_year_policy_copy_url": payload.previous_year_policy_copy_url,
                    "rc_copy_url": payload.rc_copy_url,
                    "flow_type": payload.flow_type,
                    "policy_type": payload.policy_type,
                    "status": "kyc_verified",
                    "created_at": now,
                },
            )
        self._log_event(
            event_type="journey.kyc",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="kyc",
            entity_id=reference_id,
            details=f"policy_type={payload.policy_type}, flow_type={payload.flow_type}",
        )
        return {
            "reference_id": reference_id,
            "status": "kyc_verified",
            "message": "KYC verified successfully.",
        }

    def create_quote(self, payload: QuoteCreate) -> dict[str, Any]:
        self._assert_active_session(payload.session_id, payload.username)
        quote_id = f"QTE-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        base_rate = 0.028 if payload.policy_type == "motor" else 0.022
        premium_amount = int(payload.insured_amount * base_rate * payload.tenure_years)
        cashback_amount = int(premium_amount * 0.4)

        self._sqlite_execute(
            """
            insert into app_quotes
            (quote_id, session_id, username, policy_id, policy_type, flow_type, insured_amount, tenure_years,
             premium_amount, cashback_amount, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quote_id,
                payload.session_id,
                payload.username,
                payload.policy_id,
                payload.policy_type,
                payload.flow_type,
                payload.insured_amount,
                payload.tenure_years,
                premium_amount,
                cashback_amount,
                now,
            ),
        )
        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into app_quotes
                (quote_id, session_id, username, policy_id, policy_type, flow_type, insured_amount, tenure_years,
                 premium_amount, cashback_amount, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    quote_id,
                    payload.session_id,
                    payload.username,
                    payload.policy_id,
                    payload.policy_type,
                    payload.flow_type,
                    payload.insured_amount,
                    payload.tenure_years,
                    premium_amount,
                    cashback_amount,
                    now,
                ),
            )
        if self._client:
            self._safe_insert(
                "app_quotes",
                {
                    "quote_id": quote_id,
                    "session_id": payload.session_id,
                    "username": payload.username,
                    "policy_id": payload.policy_id,
                    "policy_type": payload.policy_type,
                    "flow_type": payload.flow_type,
                    "insured_amount": payload.insured_amount,
                    "tenure_years": payload.tenure_years,
                    "premium_amount": premium_amount,
                    "cashback_amount": cashback_amount,
                    "created_at": now,
                },
            )
        self._log_event(
            event_type="journey.quote",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="quote",
            entity_id=quote_id,
            details=f"premium={premium_amount}, cashback={cashback_amount}",
        )
        return {
            "quote_id": quote_id,
            "premium_amount": premium_amount,
            "cashback_amount": cashback_amount,
            "message": "Quote generated successfully.",
        }

    def apply_cashback_action(self, payload: CashbackActionCreate) -> dict[str, Any]:
        self._assert_active_session(payload.session_id, payload.username)
        action_id = f"CBK-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        is_invest = payload.action == "invest"
        projected_value = round(payload.cashback_amount * 1.12, 2) if is_invest else None
        status = "invested" if is_invest else "redeemed"
        message = (
            "Congrats! Investment created. You can earn 12% annual growth."
            if is_invest
            else "Cashback redeemed successfully to your wallet."
        )

        self._sqlite_execute(
            """
            insert into app_cashback_actions
            (action_id, quote_id, session_id, username, cashback_amount, action, status, projected_value, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                payload.quote_id,
                payload.session_id,
                payload.username,
                payload.cashback_amount,
                payload.action,
                status,
                projected_value,
                now,
            ),
        )
        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into app_cashback_actions
                (action_id, quote_id, session_id, username, cashback_amount, action, status, projected_value, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    action_id,
                    payload.quote_id,
                    payload.session_id,
                    payload.username,
                    payload.cashback_amount,
                    payload.action,
                    status,
                    projected_value,
                    now,
                ),
            )
        if self._client:
            self._safe_insert(
                "app_cashback_actions",
                {
                    "action_id": action_id,
                    "quote_id": payload.quote_id,
                    "session_id": payload.session_id,
                    "username": payload.username,
                    "cashback_amount": payload.cashback_amount,
                    "action": payload.action,
                    "status": status,
                    "projected_value": projected_value,
                    "created_at": now,
                },
            )
        self._log_event(
            event_type="journey.cashback_action",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="cashback_action",
            entity_id=action_id,
            details=f"action={payload.action}, amount={payload.cashback_amount}",
        )
        return {
            "action_id": action_id,
            "action": payload.action,
            "status": status,
            "cashback_amount": payload.cashback_amount,
            "projected_value": projected_value,
            "message": message,
        }

    def get_dashboard(self, session_id: str, username: str) -> dict[str, Any]:
        self._assert_active_session(session_id, username)
        new_row = self._sqlite_fetchone(
            "select count(*) from app_enquiries where username = ? and flow_type = ?",
            (username, "new"),
        )
        renewal_row = self._sqlite_fetchone(
            "select count(*) from app_enquiries where username = ? and flow_type = ?",
            (username, "renewal"),
        )
        quotes_row = self._sqlite_fetchone(
            "select count(*) from app_quotes where username = ?",
            (username,),
        )
        invested_row = self._sqlite_fetchone(
            "select coalesce(sum(cashback_amount), 0) from app_cashback_actions where username = ? and action = ?",
            (username, "invest"),
        )
        redeemed_row = self._sqlite_fetchone(
            "select coalesce(sum(cashback_amount), 0) from app_cashback_actions where username = ? and action = ?",
            (username, "redeem"),
        )
        projected_row = self._sqlite_fetchone(
            "select coalesce(sum(projected_value), 0) from app_cashback_actions where username = ? and action = ?",
            (username, "invest"),
        )
        available_row = self._sqlite_fetchone(
            "select coalesce(sum(cashback_amount), 0) from app_quotes where username = ?",
            (username,),
        )

        invested_amount = int((invested_row or (0,))[0] or 0)
        redeemed_amount = int((redeemed_row or (0,))[0] or 0)
        available_total = int((available_row or (0,))[0] or 0)

        return {
            "session_id": session_id,
            "username": username,
            "new_policies": int((new_row or (0,))[0] or 0),
            "renewal_policies": int((renewal_row or (0,))[0] or 0),
            "total_quotes": int((quotes_row or (0,))[0] or 0),
            "invested_amount": invested_amount,
            "redeemed_amount": redeemed_amount,
            "projected_returns": round(float((projected_row or (0,))[0] or 0), 2),
            "current_cashback_balance": max(0, available_total - invested_amount - redeemed_amount),
            "storage_backends": self._storage_backends(),
        }

    def create_payment(self, session_id: str, username: str, quote_id: str, policy_id: str, policy_type: str, agree_tnc: bool) -> dict[str, Any]:
        self._assert_active_session(session_id, username)
        if not agree_tnc:
            raise ValueError("Please agree to terms and conditions before payment.")

        quote_row = self._sqlite_fetchone(
            "select cashback_amount from app_quotes where quote_id = ? and session_id = ? and username = ?",
            (quote_id, session_id, username),
        )
        if not quote_row:
            raise ValueError("Quote not found for this user.")

        cashback_amount = int(quote_row[0])
        payment_id = f"PAY-{uuid4().hex[:10].upper()}"
        cashback_id = f"CSH-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        self._sqlite_execute(
            """
            insert into app_payments
            (payment_id, quote_id, policy_id, policy_type, session_id, username, status, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payment_id, quote_id, policy_id, policy_type, session_id, username, "payment_success", now),
        )
        self._sqlite_execute(
            """
            insert into app_cashback_pool
            (cashback_id, quote_id, payment_id, policy_id, policy_type, session_id, username, cashback_amount, status, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cashback_id, quote_id, payment_id, policy_id, policy_type, session_id, username, cashback_amount, "pending", now),
        )

        self._log_event(
            event_type="journey.payment",
            status="success",
            session_id=session_id,
            username=username,
            entity_type="payment",
            entity_id=payment_id,
            details=f"quote_id={quote_id}, cashback_id={cashback_id}, cashback={cashback_amount}",
        )

        return {
            "payment_id": payment_id,
            "cashback_id": cashback_id,
            "status": "payment_success",
            "cashback_amount": cashback_amount,
            "message": "Payment successful. Cashback moved to pending queue.",
        }

    def list_pending_cashback(
        self,
        session_id: str,
        username: str,
        page: int = 1,
        page_size: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        return self.list_cashback(session_id, username, "pending", page, page_size, start_date, end_date)

    def list_cashback(
        self,
        session_id: str,
        username: str,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        safe_page, safe_size, offset = self._normalize_pagination(page, page_size)
        start_bound, end_bound = self._date_bounds(start_date, end_date)

        where_clauses = ["username = ?"]
        params: list[Any] = [username]
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if start_bound:
            where_clauses.append("created_at >= ?")
            params.append(start_bound)
        if end_bound:
            where_clauses.append("created_at <= ?")
            params.append(end_bound)

        where_sql = " and ".join(where_clauses)
        total_row = self._sqlite_fetchone(
            f"select count(*) from app_cashback_pool where {where_sql}",
            tuple(params),
        )
        total = int((total_row or (0,))[0] or 0)

        rows = self._sqlite_fetchall(
            f"""
            select cashback_id, quote_id, policy_id, policy_type, cashback_amount, status, created_at
            from app_cashback_pool
            where {where_sql}
            order by created_at desc
            limit ? offset ?
            """,
            tuple([*params, safe_size, offset]),
        )

        items = []
        for cashback_id, quote_id, policy_id, policy_type, cashback_amount, status, created_at in rows:
            items.append(
                {
                    "cashback_id": cashback_id,
                    "quote_id": quote_id,
                    "policy_id": policy_id,
                    "policy_type": policy_type,
                    "cashback_amount": int(cashback_amount),
                    "status": status,
                    "created_at": created_at,
                }
            )
        return {
            "items": items,
            "page": safe_page,
            "page_size": safe_size,
            "total": total,
            "has_next": (offset + safe_size) < total,
        }

    def claim_cashback_to_wallet(self, payload: CashbackClaimCreate) -> dict[str, Any]:
        self._assert_active_session(payload.session_id, payload.username)
        row = self._sqlite_fetchone(
            """
            select cashback_amount, status
            from app_cashback_pool
            where cashback_id = ? and username = ?
            """,
            (payload.cashback_id, payload.username),
        )
        if not row:
            raise ValueError("Cashback item not found.")
        amount, status = row
        if status != "pending":
            raise ValueError("Cashback already claimed.")

        now = datetime.now(timezone.utc).isoformat()
        wallet_entry_id = f"WLT-{uuid4().hex[:10].upper()}"

        self._sqlite_execute(
            "update app_cashback_pool set status = ?, claimed_at = ? where cashback_id = ?",
            ("available", now, payload.cashback_id),
        )
        self._sqlite_execute(
            """
            insert into app_wallet_ledger (entry_id, session_id, username, entry_type, source, amount, created_at)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (wallet_entry_id, payload.session_id, payload.username, "credit", "cashback", int(amount), now),
        )

        summary = self.get_wallet_summary(payload.session_id, payload.username)
        self._log_event(
            event_type="journey.cashback_claim",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="cashback",
            entity_id=payload.cashback_id,
            details=f"amount={int(amount)}",
        )
        return {
            "cashback_id": payload.cashback_id,
            "status": "available",
            "wallet_balance": summary["available_balance"],
            "message": "Cashback credited to wallet.",
        }

    def get_policy_history(
        self,
        session_id: str,
        username: str,
        page: int = 1,
        page_size: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        safe_page, safe_size, offset = self._normalize_pagination(page, page_size)
        start_bound, end_bound = self._date_bounds(start_date, end_date)

        where_clauses = ["q.username = ?"]
        params: list[Any] = [username]
        if start_bound:
            where_clauses.append("q.created_at >= ?")
            params.append(start_bound)
        if end_bound:
            where_clauses.append("q.created_at <= ?")
            params.append(end_bound)
        where_sql = " and ".join(where_clauses)

        total_row = self._sqlite_fetchone(
            f"select count(*) from app_quotes q where {where_sql}",
            tuple(params),
        )
        total = int((total_row or (0,))[0] or 0)

        rows = self._sqlite_fetchall(
            f"""
            select q.quote_id, q.policy_id, q.policy_type, q.flow_type, q.premium_amount, q.cashback_amount,
                   coalesce(p.status, 'quote_generated') as payment_status,
                   q.created_at
            from app_quotes q
            left join app_payments p on p.quote_id = q.quote_id and p.session_id = q.session_id and p.username = q.username
            where {where_sql}
            order by q.created_at desc
            limit ? offset ?
            """,
            tuple([*params, safe_size, offset]),
        )
        items = []
        for quote_id, policy_id, policy_type, flow_type, premium_amount, cashback_amount, payment_status, created_at in rows:
            items.append(
                {
                    "quote_id": quote_id,
                    "policy_id": policy_id,
                    "policy_type": policy_type,
                    "flow_type": flow_type,
                    "premium_amount": int(premium_amount),
                    "cashback_amount": int(cashback_amount),
                    "payment_status": payment_status,
                    "created_at": created_at,
                }
            )
        return {
            "items": items,
            "page": safe_page,
            "page_size": safe_size,
            "total": total,
            "has_next": (offset + safe_size) < total,
        }

    def get_wallet_summary(self, session_id: str, username: str) -> dict[str, Any]:
        credited = int((self._sqlite_fetchone(
            "select coalesce(sum(amount),0) from app_wallet_ledger where username = ? and entry_type = ?",
            (username, "credit"),
        ) or (0,))[0] or 0)
        debited = int((self._sqlite_fetchone(
            "select coalesce(sum(amount),0) from app_wallet_ledger where username = ? and entry_type = ?",
            (username, "debit"),
        ) or (0,))[0] or 0)
        redeemed = int((self._sqlite_fetchone(
            "select coalesce(sum(amount),0) from app_wallet_ledger where username = ? and entry_type = ? and source != ?",
            (username, "debit", "wallet_invest"),
        ) or (0,))[0] or 0)
        invested_wallet = int((self._sqlite_fetchone(
            "select coalesce(sum(amount),0) from app_wallet_ledger where username = ? and source = ?",
            (username, "wallet_invest"),
        ) or (0,))[0] or 0)

        return {
            "available_balance": max(0, credited - debited),
            "total_credited": credited,
            "total_redeemed": redeemed,
            "total_invested_from_wallet": invested_wallet,
        }

    def redeem_wallet(self, payload: WalletRedeemCreate) -> dict[str, Any]:
        self._assert_active_session(payload.session_id, payload.username)
        summary = self.get_wallet_summary(payload.session_id, payload.username)
        if payload.amount > summary["available_balance"]:
            raise ValueError("Insufficient wallet balance.")

        now = datetime.now(timezone.utc).isoformat()
        redeem_id = f"RDM-{uuid4().hex[:10].upper()}"
        self._sqlite_execute(
            """
            insert into app_wallet_ledger (entry_id, session_id, username, entry_type, source, amount, created_at)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (redeem_id, payload.session_id, payload.username, "debit", payload.channel, payload.amount, now),
        )
        next_summary = self.get_wallet_summary(payload.session_id, payload.username)
        self._log_event(
            event_type="journey.wallet_redeem",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="wallet_redeem",
            entity_id=redeem_id,
            details=f"channel={payload.channel}, amount={payload.amount}",
        )
        return {
            "redeem_id": redeem_id,
            "status": "redeemed",
            "channel": payload.channel,
            "amount": payload.amount,
            "available_balance": next_summary["available_balance"],
            "message": f"Redeemed to {payload.channel} successfully.",
        }

    def create_investment(self, payload: InvestmentCreate) -> dict[str, Any]:
        self._assert_active_session(payload.session_id, payload.username)
        if payload.source == "wallet":
            summary = self.get_wallet_summary(payload.session_id, payload.username)
            if payload.amount > summary["available_balance"]:
                raise ValueError("Insufficient wallet balance for investment.")

        now = datetime.now(timezone.utc).isoformat()
        investment_id = f"INV-{uuid4().hex[:10].upper()}"
        self._sqlite_execute(
            """
            insert into app_investments (investment_id, session_id, username, amount, source, status, annual_rate, created_at)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (investment_id, payload.session_id, payload.username, payload.amount, payload.source, "invested", 0.12, now),
        )
        if payload.source == "wallet":
            self._sqlite_execute(
                """
                insert into app_wallet_ledger (entry_id, session_id, username, entry_type, source, amount, created_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"WLT-{uuid4().hex[:10].upper()}", payload.session_id, payload.username, "debit", "wallet_invest", payload.amount, now),
            )

        self._log_event(
            event_type="journey.investment",
            status="success",
            session_id=payload.session_id,
            username=payload.username,
            entity_type="investment",
            entity_id=investment_id,
            details=f"source={payload.source}, amount={payload.amount}",
        )

        return {
            "investment_id": investment_id,
            "status": "invested",
            "source": payload.source,
            "amount": payload.amount,
            "message": "Investment created successfully at 12% annual return.",
        }

    def investment_projection(self, session_id: str, username: str) -> dict[str, Any]:
        principal = int((self._sqlite_fetchone(
            "select coalesce(sum(amount),0) from app_investments where username = ? and status = ?",
            (username, "invested"),
        ) or (0,))[0] or 0)
        rate = 0.12
        points = []
        for year in range(1, 6):
            value = round(principal * ((1 + rate) ** year), 2)
            points.append({"year": year, "value": value})
        return {
            "principal": principal,
            "annual_rate": rate,
            "points": points,
        }

    def get_wallet_transactions(
        self,
        session_id: str,
        username: str,
        page: int = 1,
        page_size: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        safe_page, safe_size, offset = self._normalize_pagination(page, page_size)
        start_bound, end_bound = self._date_bounds(start_date, end_date)

        where_clauses = ["username = ?"]
        params: list[Any] = [username]
        if start_bound:
            where_clauses.append("created_at >= ?")
            params.append(start_bound)
        if end_bound:
            where_clauses.append("created_at <= ?")
            params.append(end_bound)
        where_sql = " and ".join(where_clauses)

        total_row = self._sqlite_fetchone(
            f"select count(*) from app_wallet_ledger where {where_sql}",
            tuple(params),
        )
        total = int((total_row or (0,))[0] or 0)

        rows = self._sqlite_fetchall(
            f"""
            select entry_id, entry_type, source, amount, created_at
            from app_wallet_ledger
            where {where_sql}
            order by created_at desc
            limit ? offset ?
            """,
            tuple([*params, safe_size, offset]),
        )
        items: list[dict[str, Any]] = []
        for entry_id, entry_type, source, amount, created_at in rows:
            endpoint = "/api/journey/cashback/claim" if source == "cashback" else "/api/journey/wallet/redeem"
            method = "POST"
            if source == "wallet_invest":
                endpoint = "/api/journey/invest"
            note = "Cashback claimed to wallet" if source == "cashback" else f"Wallet {entry_type} via {source}"
            items.append(
                {
                    "entry_id": entry_id,
                    "entry_type": entry_type,
                    "source": source,
                    "endpoint": endpoint,
                    "method": method,
                    "amount": int(amount),
                    "note": note,
                    "created_at": created_at,
                }
            )
        return {
            "items": items,
            "page": safe_page,
            "page_size": safe_size,
            "total": total,
            "has_next": (offset + safe_size) < total,
        }

    def list_investments(
        self,
        session_id: str,
        username: str,
        page: int = 1,
        page_size: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        safe_page, safe_size, offset = self._normalize_pagination(page, page_size)
        start_bound, end_bound = self._date_bounds(start_date, end_date)

        where_clauses = ["username = ?"]
        params: list[Any] = [username]
        if start_bound:
            where_clauses.append("created_at >= ?")
            params.append(start_bound)
        if end_bound:
            where_clauses.append("created_at <= ?")
            params.append(end_bound)
        where_sql = " and ".join(where_clauses)

        total_row = self._sqlite_fetchone(
            f"select count(*) from app_investments where {where_sql}",
            tuple(params),
        )
        total = int((total_row or (0,))[0] or 0)

        rows = self._sqlite_fetchall(
            f"""
            select investment_id, source, status, amount, annual_rate, created_at
            from app_investments
            where {where_sql}
            order by created_at desc
            limit ? offset ?
            """,
            tuple([*params, safe_size, offset]),
        )
        now_ts = datetime.now(timezone.utc)
        items: list[dict[str, Any]] = []
        for investment_id, source, status, amount, annual_rate, created_at in rows:
            created_dt = datetime.fromisoformat(str(created_at))
            years_elapsed = max(0.0, (now_ts - created_dt).total_seconds() / (365 * 24 * 3600))
            principal = float(amount)
            rate = float(annual_rate)
            current_value = principal * ((1 + rate) ** years_elapsed)
            items.append(
                {
                    "investment_id": investment_id,
                    "source": source,
                    "status": status,
                    "amount": int(amount),
                    "annual_rate": rate,
                    "current_value": round(current_value, 2),
                    "returns": round(max(0.0, current_value - principal), 2),
                    "created_at": created_at,
                }
            )
        return {
            "items": items,
            "page": safe_page,
            "page_size": safe_size,
            "total": total,
            "has_next": (offset + safe_size) < total,
        }

    def list_policies(self) -> list[Policy]:
        return self._policies

    def create_enquiry(self, payload: EnquiryCreate) -> dict[str, Any]:
        tracking_id = f"ENQ-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc)

        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into enquiries
                (tracking_id, full_name, email, phone_number, policy_type, flow_type, status, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tracking_id,
                    payload.full_name,
                    payload.email,
                    payload.phone_number,
                    payload.policy_type,
                    payload.flow_type,
                    "received",
                    now,
                ),
            )
        elif self._client:
            self._safe_insert(
                "enquiries",
                {
                    "tracking_id": tracking_id,
                    "full_name": payload.full_name,
                    "email": payload.email,
                    "phone_number": payload.phone_number,
                    "policy_type": payload.policy_type,
                    "flow_type": payload.flow_type,
                    "status": "received",
                    "created_at": now.isoformat(),
                },
            )

        self._status_store[tracking_id] = {
            "status": "received",
            "category": "enquiry",
            "summary": "Enquiry received. Agent will contact soon.",
            "updated_at": now,
            "metadata": {
                "cashback_eligible_on_purchase": True,
                "payment_gateway": "simulated",
            },
        }
        return {"tracking_id": tracking_id, "status": "received"}

    def create_purchase(self, payload: PurchaseCreate) -> dict[str, Any]:
        tracking_id = f"PUR-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc)
        cashback = 500 if payload.policy_type == "motor" else 300

        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into purchases
                (tracking_id, policy_id, full_name, email, phone_number, policy_type, flow_type, payment_status, cashback_amount, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tracking_id,
                    payload.policy_id,
                    payload.full_name,
                    payload.email,
                    payload.phone_number,
                    payload.policy_type,
                    payload.flow_type,
                    "simulated_success",
                    cashback,
                    now,
                ),
            )
        elif self._client:
            self._safe_insert(
                "purchases",
                {
                    "tracking_id": tracking_id,
                    "policy_id": payload.policy_id,
                    "full_name": payload.full_name,
                    "email": payload.email,
                    "phone_number": payload.phone_number,
                    "policy_type": payload.policy_type,
                    "flow_type": payload.flow_type,
                    "payment_status": "simulated_success",
                    "cashback_amount": cashback,
                    "created_at": now.isoformat(),
                },
            )

        self._status_store[tracking_id] = {
            "status": "payment_simulated_success",
            "category": "policy_fund",
            "summary": "Policy fund request accepted. Cashback will be processed.",
            "updated_at": now,
            "metadata": {
                "cashback_amount": cashback,
                "currency": "INR",
            },
        }
        return {
            "tracking_id": tracking_id,
            "status": "payment_simulated_success",
            "cashback": cashback,
        }

    def submit_kyc(self, payload: KycCreate) -> dict[str, Any]:
        tracking_id = f"KYC-{uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc)

        if self._pg_conn:
            self._safe_pg_execute(
                """
                insert into kyc_requests
                (tracking_id, full_name, aadhaar_number, pan_number, email, phone_number, nominee_name,
                 nominee_age, previous_year_policy_copy_url, rc_copy_url, flow_type, policy_type, status, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tracking_id,
                    payload.full_name,
                    payload.aadhaar_number,
                    payload.pan_number,
                    payload.email,
                    payload.phone_number,
                    payload.nominee_name,
                    payload.nominee_age,
                    payload.previous_year_policy_copy_url,
                    payload.rc_copy_url,
                    payload.flow_type,
                    payload.policy_type,
                    "pending_verification",
                    now,
                ),
            )
        elif self._client:
            self._safe_insert(
                "kyc_requests",
                {
                    "tracking_id": tracking_id,
                    "full_name": payload.full_name,
                    "aadhaar_number": payload.aadhaar_number,
                    "pan_number": payload.pan_number,
                    "email": payload.email,
                    "phone_number": payload.phone_number,
                    "nominee_name": payload.nominee_name,
                    "nominee_age": payload.nominee_age,
                    "previous_year_policy_copy_url": payload.previous_year_policy_copy_url,
                    "rc_copy_url": payload.rc_copy_url,
                    "flow_type": payload.flow_type,
                    "policy_type": payload.policy_type,
                    "status": "pending_verification",
                    "created_at": now.isoformat(),
                },
            )

        self._status_store[tracking_id] = {
            "status": "pending_verification",
            "category": "kyc",
            "summary": "KYC submitted. Verification in progress.",
            "updated_at": now,
            "metadata": {
                "documents_required": ["aadhaar", "pan", "nominee_details"],
            },
        }
        return {"tracking_id": tracking_id, "status": "pending_verification"}

    def get_status(self, tracking_id: str) -> dict[str, Any] | None:
        if tracking_id in self._status_store:
            data = self._status_store[tracking_id]
            return {
                "tracking_id": tracking_id,
                "status": data["status"],
                "category": data["category"],
                "summary": data["summary"],
                "updated_at": data["updated_at"],
                "metadata": data["metadata"],
            }

        if self._pg_conn:
            enquiry_row = self._safe_pg_fetchone(
                "select status, created_at from enquiries where tracking_id = %s",
                (tracking_id,),
            )
            if enquiry_row:
                status, created_at = enquiry_row
                return {
                    "tracking_id": tracking_id,
                    "status": status,
                    "category": "enquiry",
                    "summary": "Enquiry received. Agent will contact soon.",
                    "updated_at": created_at,
                    "metadata": {
                        "cashback_eligible_on_purchase": True,
                        "payment_gateway": "simulated",
                    },
                }

            purchase_row = self._safe_pg_fetchone(
                "select payment_status, cashback_amount, created_at from purchases where tracking_id = %s",
                (tracking_id,),
            )
            if purchase_row:
                payment_status, cashback_amount, created_at = purchase_row
                return {
                    "tracking_id": tracking_id,
                    "status": payment_status,
                    "category": "policy_fund",
                    "summary": "Policy fund request accepted. Cashback will be processed.",
                    "updated_at": created_at,
                    "metadata": {
                        "cashback_amount": cashback_amount,
                        "currency": "INR",
                    },
                }

            kyc_row = self._safe_pg_fetchone(
                "select status, created_at from kyc_requests where tracking_id = %s",
                (tracking_id,),
            )
            if kyc_row:
                status, created_at = kyc_row
                return {
                    "tracking_id": tracking_id,
                    "status": status,
                    "category": "kyc",
                    "summary": "KYC submitted. Verification in progress.",
                    "updated_at": created_at,
                    "metadata": {
                        "documents_required": ["aadhaar", "pan", "nominee_details"],
                    },
                }

        if self._client:
            # Prototype mode keeps fast path in-memory; DB lookups can be expanded later.
            return None
        return None


data_service = DataService()
