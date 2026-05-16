create table if not exists enquiries (
  id bigserial primary key,
  tracking_id text unique not null,
  full_name text not null,
  email text not null,
  phone_number text not null,
  policy_type text not null,
  flow_type text not null,
  status text not null,
  created_at timestamptz default now()
);

create table if not exists purchases (
  id bigserial primary key,
  tracking_id text unique not null,
  policy_id text not null,
  full_name text not null,
  email text not null,
  phone_number text not null,
  policy_type text not null,
  flow_type text not null,
  payment_status text not null,
  cashback_amount integer not null,
  created_at timestamptz default now()
);

create table if not exists kyc_requests (
  id bigserial primary key,
  tracking_id text unique not null,
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
  created_at timestamptz default now()
);

create table if not exists app_sessions (
  id bigserial primary key,
  session_id text unique not null,
  username text not null,
  password text not null,
  created_at timestamptz default now()
);

create table if not exists app_enquiries (
  id bigserial primary key,
  reference_id text unique not null,
  session_id text not null,
  username text not null,
  full_name text not null,
  email text not null,
  phone_number text not null,
  policy_type text not null,
  flow_type text not null,
  status text not null,
  created_at timestamptz default now()
);

create table if not exists app_kyc (
  id bigserial primary key,
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
  created_at timestamptz default now()
);

create table if not exists app_quotes (
  id bigserial primary key,
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
  created_at timestamptz default now()
);

create table if not exists app_cashback_actions (
  id bigserial primary key,
  action_id text unique not null,
  quote_id text not null,
  session_id text not null,
  username text not null,
  cashback_amount integer not null,
  action text not null,
  status text not null,
  projected_value numeric,
  created_at timestamptz default now()
);

create table if not exists app_payments (
  id bigserial primary key,
  payment_id text unique not null,
  quote_id text not null,
  policy_id text not null,
  policy_type text not null,
  session_id text not null,
  username text not null,
  status text not null,
  created_at timestamptz default now()
);

create table if not exists app_cashback_pool (
  id bigserial primary key,
  cashback_id text unique not null,
  quote_id text not null,
  payment_id text not null,
  policy_id text not null,
  policy_type text not null,
  session_id text not null,
  username text not null,
  cashback_amount integer not null,
  status text not null,
  created_at timestamptz default now(),
  claimed_at timestamptz
);

create table if not exists app_wallet_ledger (
  id bigserial primary key,
  entry_id text unique not null,
  session_id text not null,
  username text not null,
  entry_type text not null,
  source text not null,
  amount integer not null,
  created_at timestamptz default now()
);

create table if not exists app_investments (
  id bigserial primary key,
  investment_id text unique not null,
  session_id text not null,
  username text not null,
  amount integer not null,
  source text not null,
  status text not null,
  annual_rate numeric not null,
  created_at timestamptz default now()
);

create table if not exists app_user_events (
  id bigserial primary key,
  event_id text unique not null,
  session_id text,
  username text,
  event_type text not null,
  entity_type text,
  entity_id text,
  status text not null,
  details text,
  created_at timestamptz default now()
);

-- Enforce one active session row per username (logout deletes the row).
create unique index if not exists ux_app_sessions_username on app_sessions (username);
