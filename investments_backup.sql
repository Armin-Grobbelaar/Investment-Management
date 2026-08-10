--
-- PostgreSQL database dump
--

\restrict 6Xnl4jViyRSrQQoKwK3LzsN8gQV326nhuQPk7qtLBPtABvzY4896mU3VwK4vDqL

-- Dumped from database version 18.1 (Debian 18.1-1.pgdg13+2)
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: configuration; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.configuration (
    id bigint NOT NULL,
    setting_key character varying(100) NOT NULL,
    setting_value text,
    setting_description text,
    setting_category character varying(50) DEFAULT 'general'::character varying,
    is_editable boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.configuration OWNER TO postgres;

--
-- Name: configuration_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.configuration_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.configuration_id_seq OWNER TO postgres;

--
-- Name: configuration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.configuration_id_seq OWNED BY public.configuration.id;


--
-- Name: dividends; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dividends (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    dividend_date date NOT NULL,
    dividend_frequency integer NOT NULL,
    dividend_recieved double precision NOT NULL,
    dividend_percentage double precision NOT NULL
);


ALTER TABLE public.dividends OWNER TO postgres;

--
-- Name: dividends_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dividends_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dividends_id_seq OWNER TO postgres;

--
-- Name: dividends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dividends_id_seq OWNED BY public.dividends.id;


--
-- Name: factsheets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.factsheets (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    factsheet_date date NOT NULL,
    factsheet_type character varying(50) DEFAULT 'MDD'::character varying,
    factsheet_year integer NOT NULL,
    factsheet_month integer NOT NULL,
    source_url text,
    file_path text,
    file_name character varying(300),
    file_size_bytes integer,
    downloaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.factsheets OWNER TO postgres;

--
-- Name: factsheets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.factsheets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.factsheets_id_seq OWNER TO postgres;

--
-- Name: factsheets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.factsheets_id_seq OWNED BY public.factsheets.id;


--
-- Name: fees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fees (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    fee_date date NOT NULL,
    fee_type character varying(50) NOT NULL,
    fee_paid double precision NOT NULL,
    fee_frequency double precision NOT NULL,
    number_of_units double precision NOT NULL,
    investment_fee double precision NOT NULL
);


ALTER TABLE public.fees OWNER TO postgres;

--
-- Name: fees_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.fees_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fees_id_seq OWNER TO postgres;

--
-- Name: fees_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.fees_id_seq OWNED BY public.fees.id;


--
-- Name: inflation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inflation (
    id integer NOT NULL,
    inflation_date date NOT NULL,
    inflation_rate double precision NOT NULL,
    country character varying(100) NOT NULL,
    currency character varying(5) NOT NULL,
    source character varying(200),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.inflation OWNER TO postgres;

--
-- Name: inflation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inflation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inflation_id_seq OWNER TO postgres;

--
-- Name: inflation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inflation_id_seq OWNED BY public.inflation.id;


--
-- Name: investment_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.investment_metrics (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    metrics_date date NOT NULL,
    local_net_growth double precision,
    local_total_return double precision,
    local_return_multiple double precision,
    local_cagr double precision,
    local_irr double precision,
    local_total_fee_ratio double precision,
    local_total_tax_ratio double precision,
    local_total_cost_ratio double precision,
    local_dividend_yield double precision,
    local_fee_ratio_annualized double precision,
    local_tax_ratio_annualized double precision,
    local_cost_ratio_annualized double precision,
    local_dividend_yield_annualized double precision,
    local_total_contributions double precision,
    local_total_fees double precision,
    local_total_tax double precision,
    local_total_dividends double precision,
    local_number_of_contributions integer,
    local_average_contributions double precision,
    local_investment_period double precision,
    local_real_net_growth double precision,
    local_real_total_return double precision,
    local_real_return_multiple double precision,
    local_real_cagr double precision,
    local_real_irr double precision,
    local_real_total_fee_ratio double precision,
    local_real_total_tax_ratio double precision,
    local_real_total_cost_ratio double precision,
    local_real_dividend_yield double precision,
    local_real_fee_ratio_annualized double precision,
    local_real_tax_ratio_annualized double precision,
    local_real_cost_ratio_annualized double precision,
    local_real_dividend_yield_annualized double precision,
    local_real_total_contributions double precision,
    local_real_total_fees double precision,
    local_real_total_tax double precision,
    local_real_total_dividends double precision,
    local_real_number_of_contributions integer,
    local_real_average_contributions double precision,
    local_real_investment_period double precision,
    foreign_net_growth double precision,
    foreign_total_return double precision,
    foreign_return_multiple double precision,
    foreign_cagr double precision,
    foreign_irr double precision,
    foreign_total_fee_ratio double precision,
    foreign_total_tax_ratio double precision,
    foreign_total_cost_ratio double precision,
    foreign_dividend_yield double precision,
    foreign_fee_ratio_annualized double precision,
    foreign_tax_ratio_annualized double precision,
    foreign_cost_ratio_annualized double precision,
    foreign_dividend_yield_annualized double precision,
    foreign_total_contributions double precision,
    foreign_total_fees double precision,
    foreign_total_tax double precision,
    foreign_total_dividends double precision,
    foreign_number_of_contributions integer,
    foreign_average_contributions double precision,
    foreign_investment_period double precision,
    foreign_real_net_growth double precision,
    foreign_real_total_return double precision,
    foreign_real_return_multiple double precision,
    foreign_real_cagr double precision,
    foreign_real_irr double precision,
    foreign_real_total_fee_ratio double precision,
    foreign_real_total_tax_ratio double precision,
    foreign_real_total_cost_ratio double precision,
    foreign_real_dividend_yield double precision,
    foreign_real_fee_ratio_annualized double precision,
    foreign_real_tax_ratio_annualized double precision,
    foreign_real_cost_ratio_annualized double precision,
    foreign_real_dividend_yield_annualized double precision,
    foreign_real_total_contributions double precision,
    foreign_real_total_fees double precision,
    foreign_real_total_tax double precision,
    foreign_real_total_dividends double precision,
    foreign_real_number_of_contributions integer,
    foreign_real_average_contributions double precision,
    foreign_real_investment_period double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.investment_metrics OWNER TO postgres;

--
-- Name: investment_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.investment_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.investment_metrics_id_seq OWNER TO postgres;

--
-- Name: investment_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.investment_metrics_id_seq OWNED BY public.investment_metrics.id;


--
-- Name: investment_source_meta; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.investment_source_meta (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    source character varying(50) DEFAULT 'yfinance'::character varying NOT NULL,
    source_ticker character varying(200),
    profiledata_manager character varying(200),
    profiledata_fund character varying(200),
    profiledata_class character varying(50),
    last_fetched timestamp without time zone,
    backfill_complete boolean DEFAULT false,
    backfill_cursor date
);


ALTER TABLE public.investment_source_meta OWNER TO postgres;

--
-- Name: investment_source_meta_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.investment_source_meta_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.investment_source_meta_id_seq OWNER TO postgres;

--
-- Name: investment_source_meta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.investment_source_meta_id_seq OWNED BY public.investment_source_meta.id;


--
-- Name: investments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.investments (
    id bigint NOT NULL,
    institution_name character varying(200) NOT NULL,
    initial_investment_date date NOT NULL,
    investment_type character varying(50) NOT NULL,
    investment_name character varying(200),
    investment_ticker character varying(50) NOT NULL,
    unit_currency character varying(5) NOT NULL,
    initial_unit_price double precision NOT NULL,
    unit_price double precision NOT NULL,
    number_of_units_held double precision NOT NULL,
    total_dividends_received double precision NOT NULL,
    total_tax_paid double precision NOT NULL,
    total_fees_paid double precision NOT NULL,
    investment_fee double precision NOT NULL,
    investment_status character varying(20) NOT NULL,
    investment_subtype character varying(50),
    source_account character varying(100),
    price_source_investment_id bigint
);


ALTER TABLE public.investments OWNER TO postgres;

--
-- Name: investments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.investments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.investments_id_seq OWNER TO postgres;

--
-- Name: investments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.investments_id_seq OWNED BY public.investments.id;


--
-- Name: portfolio_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.portfolio_metrics (
    id bigint NOT NULL,
    metrics_date date NOT NULL,
    dimension_type character varying(50) NOT NULL,
    dimension_value character varying(200) NOT NULL,
    total_contributions double precision,
    total_current_value double precision,
    total_return_amount double precision,
    total_return_pct double precision,
    cagr double precision,
    irr double precision,
    total_fees double precision,
    total_dividends double precision,
    total_tax double precision,
    investment_count integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.portfolio_metrics OWNER TO postgres;

--
-- Name: portfolio_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.portfolio_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.portfolio_metrics_id_seq OWNER TO postgres;

--
-- Name: portfolio_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.portfolio_metrics_id_seq OWNED BY public.portfolio_metrics.id;


--
-- Name: prediction_accuracy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prediction_accuracy (
    id bigint NOT NULL,
    prediction_id bigint NOT NULL,
    actual_date date NOT NULL,
    predicted_value double precision NOT NULL,
    actual_value double precision NOT NULL,
    prediction_error double precision NOT NULL,
    percentage_error double precision NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.prediction_accuracy OWNER TO postgres;

--
-- Name: prediction_accuracy_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.prediction_accuracy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prediction_accuracy_id_seq OWNER TO postgres;

--
-- Name: prediction_accuracy_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.prediction_accuracy_id_seq OWNED BY public.prediction_accuracy.id;


--
-- Name: predictions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.predictions (
    id bigint NOT NULL,
    prediction_date date NOT NULL,
    model_name character varying(100) NOT NULL,
    scope character varying(50) NOT NULL,
    prediction_horizon_days integer NOT NULL,
    confidence_level double precision NOT NULL,
    prediction_data jsonb NOT NULL,
    historical_context jsonb,
    accuracy_score double precision,
    risk_level double precision,
    actual_outcomes jsonb,
    model_metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.predictions OWNER TO postgres;

--
-- Name: predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.predictions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.predictions_id_seq OWNER TO postgres;

--
-- Name: predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.predictions_id_seq OWNED BY public.predictions.id;


--
-- Name: property_investments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.property_investments (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    property_name character varying(300) NOT NULL,
    property_url text,
    property_address text,
    property_type character varying(100),
    purchase_price double precision,
    transfer_costs double precision,
    transfer_duty double precision,
    bond_registration_costs double precision,
    other_acquisition_costs double precision,
    total_acquisition_cost double precision,
    deposit_amount double precision,
    bond_amount double precision,
    bond_interest_rate double precision,
    bond_term_years integer,
    bond_monthly_repayment double precision,
    monthly_levy double precision DEFAULT 0,
    monthly_rates double precision DEFAULT 0,
    monthly_insurance double precision DEFAULT 0,
    monthly_maintenance_reserve double precision DEFAULT 0,
    monthly_management_fee_pct double precision DEFAULT 0,
    monthly_other_costs double precision DEFAULT 0,
    monthly_rental_income double precision DEFAULT 0,
    rental_growth_rate_pa double precision DEFAULT 0.05,
    vacancy_rate_pct double precision DEFAULT 0.05,
    property_growth_rate_pa double precision DEFAULT 0.07,
    inflation_rate double precision DEFAULT 0.05,
    gross_rental_yield double precision,
    net_rental_yield double precision,
    monthly_shortfall_surplus double precision,
    irr_10yr double precision,
    irr_20yr double precision,
    break_even_years double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.property_investments OWNER TO postgres;

--
-- Name: property_investments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.property_investments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.property_investments_id_seq OWNER TO postgres;

--
-- Name: property_investments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.property_investments_id_seq OWNED BY public.property_investments.id;


--
-- Name: returns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.returns (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    returns_date date NOT NULL,
    monthly_return double precision NOT NULL,
    quarterly_return double precision NOT NULL,
    half_yearly_return double precision NOT NULL,
    yearly_return double precision NOT NULL,
    yearly_3_return double precision NOT NULL,
    yearly_5_return double precision NOT NULL,
    return_since_inception double precision NOT NULL
);


ALTER TABLE public.returns OWNER TO postgres;

--
-- Name: returns_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.returns_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.returns_id_seq OWNER TO postgres;

--
-- Name: returns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.returns_id_seq OWNED BY public.returns.id;


--
-- Name: tax; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tax (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    tax_date date NOT NULL,
    tax_type character varying(50) NOT NULL,
    tax_paid double precision NOT NULL,
    tax_percentage double precision NOT NULL
);


ALTER TABLE public.tax OWNER TO postgres;

--
-- Name: tax_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tax_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tax_id_seq OWNER TO postgres;

--
-- Name: tax_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tax_id_seq OWNED BY public.tax.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transactions (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    transaction_date date NOT NULL,
    transaction_type character varying(20) NOT NULL,
    transaction_amount double precision NOT NULL,
    unit_price double precision NOT NULL,
    number_of_units double precision NOT NULL
);


ALTER TABLE public.transactions OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: unit_prices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unit_prices (
    id bigint NOT NULL,
    investment_id bigint NOT NULL,
    unit_price_date date NOT NULL,
    unit_price double precision NOT NULL,
    unit_price_change double precision NOT NULL,
    percentage_unit_price_change double precision NOT NULL
);


ALTER TABLE public.unit_prices OWNER TO postgres;

--
-- Name: unit_prices_backup_20260808; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unit_prices_backup_20260808 (
    id bigint,
    investment_id bigint,
    unit_price_date date,
    unit_price double precision,
    unit_price_change double precision,
    percentage_unit_price_change double precision
);


ALTER TABLE public.unit_prices_backup_20260808 OWNER TO postgres;

--
-- Name: unit_prices_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.unit_prices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.unit_prices_id_seq OWNER TO postgres;

--
-- Name: unit_prices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.unit_prices_id_seq OWNED BY public.unit_prices.id;


--
-- Name: v_investment_prices; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_investment_prices AS
 SELECT up.investment_id,
    up.unit_price_date,
    up.unit_price,
    up.unit_price_change,
    up.percentage_unit_price_change
   FROM public.unit_prices up
UNION ALL
 SELECT i.id AS investment_id,
    up.unit_price_date,
    up.unit_price,
    up.unit_price_change,
    up.percentage_unit_price_change
   FROM (public.investments i
     JOIN public.unit_prices up ON ((up.investment_id = i.price_source_investment_id)))
  WHERE (i.price_source_investment_id IS NOT NULL);


ALTER VIEW public.v_investment_prices OWNER TO postgres;

--
-- Name: configuration id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.configuration ALTER COLUMN id SET DEFAULT nextval('public.configuration_id_seq'::regclass);


--
-- Name: dividends id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dividends ALTER COLUMN id SET DEFAULT nextval('public.dividends_id_seq'::regclass);


--
-- Name: factsheets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.factsheets ALTER COLUMN id SET DEFAULT nextval('public.factsheets_id_seq'::regclass);


--
-- Name: fees id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fees ALTER COLUMN id SET DEFAULT nextval('public.fees_id_seq'::regclass);


--
-- Name: inflation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inflation ALTER COLUMN id SET DEFAULT nextval('public.inflation_id_seq'::regclass);


--
-- Name: investment_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_metrics ALTER COLUMN id SET DEFAULT nextval('public.investment_metrics_id_seq'::regclass);


--
-- Name: investment_source_meta id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_source_meta ALTER COLUMN id SET DEFAULT nextval('public.investment_source_meta_id_seq'::regclass);


--
-- Name: investments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investments ALTER COLUMN id SET DEFAULT nextval('public.investments_id_seq'::regclass);


--
-- Name: portfolio_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.portfolio_metrics ALTER COLUMN id SET DEFAULT nextval('public.portfolio_metrics_id_seq'::regclass);


--
-- Name: prediction_accuracy id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction_accuracy ALTER COLUMN id SET DEFAULT nextval('public.prediction_accuracy_id_seq'::regclass);


--
-- Name: predictions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predictions ALTER COLUMN id SET DEFAULT nextval('public.predictions_id_seq'::regclass);


--
-- Name: property_investments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.property_investments ALTER COLUMN id SET DEFAULT nextval('public.property_investments_id_seq'::regclass);


--
-- Name: returns id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.returns ALTER COLUMN id SET DEFAULT nextval('public.returns_id_seq'::regclass);


--
-- Name: tax id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tax ALTER COLUMN id SET DEFAULT nextval('public.tax_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: unit_prices id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unit_prices ALTER COLUMN id SET DEFAULT nextval('public.unit_prices_id_seq'::regclass);


--
-- Data for Name: configuration; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.configuration (id, setting_key, setting_value, setting_description, setting_category, is_editable, created_at, updated_at) FROM stdin;
1	native_currency	R	Default native currency for the application (symbol)	currency	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
2	pdf_report_frequency	monthly	How often PDF reports should be generated (daily, weekly, monthly, quarterly, annually)	reporting	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
3	base_currency	ZAR	Base currency for portfolio calculations and display	currency	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
4	risk_tolerance	medium	Default risk tolerance level for recommendations (low, medium, high)	risk	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
5	email_notifications	true	Whether to send email notifications for reports	communication	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
6	auto_update_prices	true	Whether to automatically update investment prices from external sources	automation	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
7	report_timezone	Africa/Johannesburg	Timezone for report timestamps and scheduling	reporting	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
8	chart_theme	default	Color theme for charts (default, dark, colorful)	display	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
9	performance_calculation_method	time_weighted	Method for calculating portfolio returns (time_weighted, money_weighted)	calculation	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
10	max_chart_period_days	3650	Maximum days to show in historical charts (default 10 years)	display	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
11	cgt_inclusion_rate	0.40	Capital Gains Tax inclusion rate for individuals (fraction)	tax	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
12	cgt_marginal_tax_rate	0.45	Assumed marginal income tax rate for CGT calc (fraction)	tax	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
13	cgt_annual_exclusion	40000	Annual CGT exclusion for individuals (in base currency)	tax	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
14	cgt_primary_residence_exclusion	2000000	CGT exclusion for the sale of a primary residence (in base currency)	tax	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
15	default_projection_years	20	Default property projection horizon in years	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
16	monte_carlo_simulations	1000	Default number of Monte Carlo simulations	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
17	default_bond_interest_rate	11.75	Default property bond interest rate (percent)	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
18	default_rental_growth_rate	5.0	Default annual rental growth rate (percent)	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
19	default_vacancy_rate	5.0	Default vacancy rate (percent)	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
20	default_property_growth_rate	7.0	Default annual property value growth (percent)	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
21	default_inflation_rate	5.0	Default long-term inflation rate (percent)	property	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
22	scheduler_daily_hour	11	Hour (SAST) for daily price fetch scheduler	automation	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
23	scheduler_daily_minute	30	Minute for daily price fetch scheduler	automation	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
24	scheduler_factsheet_day	20	Day of month for monthly factsheet download	automation	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
25	prediction_horizon_days	30	Default prediction horizon in days	predictions	t	2026-08-09 09:15:02.595396	2026-08-09 09:15:02.595396
51	portfolio_risk_baseline	1.0	Baseline risk score for the total portfolio	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
52	individual_risk_multiplier	1.5	Risk score multiplier for individual investments vs portfolio	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
53	currency_risk_multiplier	1.2	Risk score multiplier for currency-segregated views	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
54	type_risk_multiplier	1.3	Risk score multiplier for investment-type-segregated views	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
55	institution_risk_multiplier	1.4	Risk score multiplier for institution-segregated views	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
56	portfolio_dividend_baseline	0.04	Baseline dividend yield (fraction) used for portfolio-wide estimates	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
57	individual_dividend_base	0.04	Baseline dividend yield (fraction) used for individual investment estimates	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
58	correction_probability_portfolio	0.02	Probability of a market correction event in portfolio simulation (fraction)	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
59	correction_probability_individual	0.04	Probability of a market correction event in individual investment simulation (fraction)	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
60	market_correction_min	0.05	Minimum magnitude of a simulated market correction (fraction)	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
61	market_correction_max	0.15	Maximum magnitude of a simulated market correction (fraction)	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
62	volatility_baseline_portfolio	0.15	Default annualised volatility for portfolio-level Monte Carlo when history is absent	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
63	volatility_baseline_1y	0.15	Default annualised volatility for 1-year rolling simulation	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
64	volatility_baseline_3y	0.20	Default annualised volatility for 3-year rolling simulation	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
65	volatility_baseline_5y	0.25	Default annualised volatility for 5-year rolling simulation	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
66	std_dev_monthly	0.03	Default monthly standard deviation used in risk calculations	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
67	cagr_excellent_threshold	0.15	CAGR threshold above which performance is rated Excellent (fraction)	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
68	cagr_good_threshold	0.08	CAGR threshold above which performance is rated Good (fraction)	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
69	excellent_sharpe_ratio	1.2	Sharpe ratio threshold for Excellent rating	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
70	good_sharpe_ratio	0.8	Sharpe ratio threshold for Good rating	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
71	excellent_return_threshold	50.0	Total return % threshold for Excellent rating	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
72	good_return_threshold	20.0	Total return % threshold for Good rating	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
73	good_volatility_threshold	0.15	Annualised volatility below which is considered Good (fraction)	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
74	property_growth_std	2.5	Standard deviation for property growth rate in Monte Carlo (percentage points)	property	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
75	rental_growth_std	2.0	Standard deviation for rental growth rate in Monte Carlo (percentage points)	property	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
76	interest_rate_std	1.5	Standard deviation for bond interest rate in Monte Carlo (percentage points)	property	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
77	monte_carlo_fallback_value	100000	Initial portfolio value used as fallback in Monte Carlo when DB has no data	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
78	monte_carlo_fallback_contribution	5000	Monthly contribution used as fallback in Monte Carlo when DB has no data	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
79	monte_carlo_fallback_mu	0.10	Expected annual return used as fallback in Monte Carlo when DB has no data (fraction)	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
80	dashboard_default_value	100000	Default value shown on dashboard when no real data is available	display	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
81	fallback_contribution_divisor	1.27	Divisor used to derive an implied monthly contribution from contribution history	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
82	fallback_investment_time_years	1.5	Assumed holding period (years) used when estimating IRR from limited history	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
83	fallback_portfolio_irr	9.5	Default portfolio IRR (percent) used when no return history is available	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
84	daily_growth_baseline	0.001	Baseline daily growth rate (fraction) used in projection fallbacks	simulation	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
85	drawdown_data_points	200	Number of data points sampled for drawdown analysis	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
86	performance_data_points	48	Number of data points sampled for performance charts	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
87	rolling_1y_periods	12	Number of monthly periods used for the 1-year rolling return window	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
88	rolling_3y_periods	20	Number of monthly periods used for the 3-year rolling return window	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
89	rolling_5y_periods	10	Number of monthly periods used for the 5-year rolling return window	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
90	volatility_periods	24	Number of monthly periods used for annualised volatility calculation	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
91	sharpe_periods	16	Number of monthly periods used for the Sharpe ratio calculation	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
92	contribution_periods	60	Number of periods used to estimate average monthly contributions	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
93	dividend_periods	60	Number of periods used to estimate average dividend yields	performance	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
94	area_chart_days	30	Number of days shown on the dashboard area chart	display	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
95	area_chart_top_n	5	Number of top investments shown on the dashboard area chart	display	t	2026-08-09 11:31:17.678197	2026-08-09 11:31:17.678197
586	gzip_min_size	1000	Minimum size in bytes for GZip compression	performance	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
587	tf_api_timeout	5	Timeout in seconds for TensorFlow health check	predictions	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
588	tf_training_timeout	600	Timeout in seconds for remote LSTM training	predictions	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
589	xgboost_random_state	42	Random state for XGBoost model	predictions	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
590	gp_random_state	42	Random state for GP Regressor	predictions	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
591	synthetic_data_seed	42	Seed for synthetic data generation	simulation	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
592	monte_carlo_seed	42	Seed for Monte Carlo	simulation	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
593	transfer_duty_brackets	[{"lower": 0, "upper": 1100000, "base": 0, "rate": 0.0}, {"lower": 1100000, "upper": 1512500, "base": 0, "rate": 0.03, "excess_from": 1100000}, {"lower": 1512500, "upper": 2117500, "base": 12375, "rate": 0.06, "excess_from": 1512500}, {"lower": 2117500, "upper": 2722500, "base": 48675, "rate": 0.08, "excess_from": 2117500}, {"lower": 2722500, "upper": 12100000, "base": 97075, "rate": 0.11, "excess_from": 2722500}, {"lower": 12100000, "upper": 999999999999, "base": 1128600, "rate": 0.13, "excess_from": 12100000}]	SA Transfer Duty brackets (JSON)	tax	t	2026-08-10 13:09:16.029028	2026-08-10 13:09:16.029028
\.


--
-- Data for Name: dividends; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dividends (id, investment_id, dividend_date, dividend_frequency, dividend_recieved, dividend_percentage) FROM stdin;
1	1	2023-03-15	4	336.2460067360808	0.02
2	1	2023-06-15	4	408.05271571826495	0.02
3	1	2023-09-15	4	314.8071619606804	0.02
4	1	2023-12-15	4	272.45552941354646	0.02
5	2	2023-03-15	4	462.3811961623313	0.02
6	2	2023-06-15	4	361.312193861762	0.02
7	2	2023-09-15	4	295.11134964911605	0.02
8	2	2023-12-15	4	489.255316958932	0.02
9	3	2023-03-15	4	261.81956570156865	0.02
10	3	2023-06-15	4	197.5590687273613	0.02
11	3	2023-09-15	4	242.57988971013052	0.02
12	3	2023-12-15	4	476.7108840685735	0.02
13	4	2023-03-15	4	465.51766197201556	0.02
14	4	2023-06-15	4	366.98687803740347	0.02
15	4	2023-09-15	4	139.8471363828927	0.02
16	4	2023-12-15	4	480.9127250084847	0.02
17	5	2023-03-15	4	169.15618118368334	0.02
18	5	2023-06-15	4	338.5175373395009	0.02
19	5	2023-09-15	4	492.01097595627346	0.02
20	5	2023-12-15	4	224.36835513371835	0.02
21	6	2023-03-15	4	337.38060972797706	0.02
22	6	2023-06-15	4	442.7818158687186	0.02
23	6	2023-09-15	4	444.7171375474298	0.02
24	6	2023-12-15	4	353.1885002634564	0.02
\.


--
-- Data for Name: factsheets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.factsheets (id, investment_id, factsheet_date, factsheet_type, factsheet_year, factsheet_month, source_url, file_path, file_name, file_size_bytes, downloaded_at) FROM stdin;
\.


--
-- Data for Name: fees; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.fees (id, investment_id, fee_date, fee_type, fee_paid, fee_frequency, number_of_units, investment_fee) FROM stdin;
\.


--
-- Data for Name: inflation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.inflation (id, inflation_date, inflation_rate, country, currency, source, created_at) FROM stdin;
\.


--
-- Data for Name: investment_metrics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.investment_metrics (id, investment_id, metrics_date, local_net_growth, local_total_return, local_return_multiple, local_cagr, local_irr, local_total_fee_ratio, local_total_tax_ratio, local_total_cost_ratio, local_dividend_yield, local_fee_ratio_annualized, local_tax_ratio_annualized, local_cost_ratio_annualized, local_dividend_yield_annualized, local_total_contributions, local_total_fees, local_total_tax, local_total_dividends, local_number_of_contributions, local_average_contributions, local_investment_period, local_real_net_growth, local_real_total_return, local_real_return_multiple, local_real_cagr, local_real_irr, local_real_total_fee_ratio, local_real_total_tax_ratio, local_real_total_cost_ratio, local_real_dividend_yield, local_real_fee_ratio_annualized, local_real_tax_ratio_annualized, local_real_cost_ratio_annualized, local_real_dividend_yield_annualized, local_real_total_contributions, local_real_total_fees, local_real_total_tax, local_real_total_dividends, local_real_number_of_contributions, local_real_average_contributions, local_real_investment_period, foreign_net_growth, foreign_total_return, foreign_return_multiple, foreign_cagr, foreign_irr, foreign_total_fee_ratio, foreign_total_tax_ratio, foreign_total_cost_ratio, foreign_dividend_yield, foreign_fee_ratio_annualized, foreign_tax_ratio_annualized, foreign_cost_ratio_annualized, foreign_dividend_yield_annualized, foreign_total_contributions, foreign_total_fees, foreign_total_tax, foreign_total_dividends, foreign_number_of_contributions, foreign_average_contributions, foreign_investment_period, foreign_real_net_growth, foreign_real_total_return, foreign_real_return_multiple, foreign_real_cagr, foreign_real_irr, foreign_real_total_fee_ratio, foreign_real_total_tax_ratio, foreign_real_total_cost_ratio, foreign_real_dividend_yield, foreign_real_fee_ratio_annualized, foreign_real_tax_ratio_annualized, foreign_real_cost_ratio_annualized, foreign_real_dividend_yield_annualized, foreign_real_total_contributions, foreign_real_total_fees, foreign_real_total_tax, foreign_real_total_dividends, foreign_real_number_of_contributions, foreign_real_average_contributions, foreign_real_investment_period, created_at) FROM stdin;
\.


--
-- Data for Name: investment_source_meta; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.investment_source_meta (id, investment_id, source, source_ticker, profiledata_manager, profiledata_fund, profiledata_class, last_fetched, backfill_complete, backfill_cursor) FROM stdin;
\.


--
-- Data for Name: investments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.investments (id, institution_name, initial_investment_date, investment_type, investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status, investment_subtype, source_account, price_source_investment_id) FROM stdin;
1	Allan Gray	2021-01-15	Unit Trust	AG Equity Fund	AGEF	ZAR	150	176.19040214181143	1000	0	0	0	0.02	Active	\N	\N	\N
2	PSG Wealth	2020-06-01	Unit Trust	PSG Balanced Fund	PSGBF	ZAR	100	116.2661122449225	500	0	0	0	0.015	Active	\N	\N	\N
3	Standard Bank	2022-03-10	ETF	Satrix Top 40 ETF	STX40	ZAR	80	66.9635050577894	1500	0	0	0	0.002	Active	\N	\N	\N
4	Alexander Forbes	2021-08-20	Unit Trust	AF Global Equity	AFGE	USD	120	105.31608923000705	300	0	0	0	0.012	Active	\N	\N	\N
5	Discretionary	2023-01-01	Equity	Tech Growth Stock	TGS	ZAR	100	88.6625115312634	200	0	0	0	0.005	Active	\N	\N	\N
6	Retirement Annuity	2019-01-01	Unit Trust	Sanlam Wealth Fund	SWF	ZAR	50	51.79458882456548	5000	0	0	0	0.008	Active	\N	\N	\N
\.


--
-- Data for Name: portfolio_metrics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.portfolio_metrics (id, metrics_date, dimension_type, dimension_value, total_contributions, total_current_value, total_return_amount, total_return_pct, cagr, irr, total_fees, total_dividends, total_tax, investment_count, created_at) FROM stdin;
\.


--
-- Data for Name: prediction_accuracy; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.prediction_accuracy (id, prediction_id, actual_date, predicted_value, actual_value, prediction_error, percentage_error, created_at) FROM stdin;
\.


--
-- Data for Name: predictions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.predictions (id, prediction_date, model_name, scope, prediction_horizon_days, confidence_level, prediction_data, historical_context, accuracy_score, risk_level, actual_outcomes, model_metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: property_investments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.property_investments (id, investment_id, property_name, property_url, property_address, property_type, purchase_price, transfer_costs, transfer_duty, bond_registration_costs, other_acquisition_costs, total_acquisition_cost, deposit_amount, bond_amount, bond_interest_rate, bond_term_years, bond_monthly_repayment, monthly_levy, monthly_rates, monthly_insurance, monthly_maintenance_reserve, monthly_management_fee_pct, monthly_other_costs, monthly_rental_income, rental_growth_rate_pa, vacancy_rate_pct, property_growth_rate_pa, inflation_rate, gross_rental_yield, net_rental_yield, monthly_shortfall_surplus, irr_10yr, irr_20yr, break_even_years, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: returns; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.returns (id, investment_id, returns_date, monthly_return, quarterly_return, half_yearly_return, yearly_return, yearly_3_return, yearly_5_return, return_since_inception) FROM stdin;
\.


--
-- Data for Name: tax; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tax (id, investment_id, tax_date, tax_type, tax_paid, tax_percentage) FROM stdin;
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transactions (id, investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) FROM stdin;
1	1	2023-01-01	buy	31400.459612426563	100	314.0045961242656
2	1	2023-04-01	buy	31400.459612426563	100	314.0045961242656
3	1	2023-06-30	buy	31400.459612426563	100	314.0045961242656
4	1	2023-09-28	buy	31400.459612426563	100	314.0045961242656
5	1	2023-12-27	buy	31400.459612426563	100	314.0045961242656
6	1	2024-03-26	buy	31400.459612426563	100	314.0045961242656
7	1	2024-06-24	buy	31400.459612426563	100	314.0045961242656
8	1	2024-09-22	buy	31400.459612426563	100	314.0045961242656
9	1	2024-12-21	buy	31400.459612426563	100	314.0045961242656
10	1	2025-03-21	buy	31400.459612426563	100	314.0045961242656
11	2	2023-01-01	buy	9304.405425334518	100	93.04405425334518
12	2	2023-04-01	buy	9304.405425334518	100	93.04405425334518
13	2	2023-06-30	buy	9304.405425334518	100	93.04405425334518
14	2	2023-09-28	buy	9304.405425334518	100	93.04405425334518
15	2	2023-12-27	buy	9304.405425334518	100	93.04405425334518
16	2	2024-03-26	buy	9304.405425334518	100	93.04405425334518
17	2	2024-06-24	buy	9304.405425334518	100	93.04405425334518
18	2	2024-09-22	buy	9304.405425334518	100	93.04405425334518
19	2	2024-12-21	buy	9304.405425334518	100	93.04405425334518
20	2	2025-03-21	buy	9304.405425334518	100	93.04405425334518
21	3	2023-01-01	buy	29424.28064298088	100	294.2428064298088
22	3	2023-04-01	buy	29424.28064298088	100	294.2428064298088
23	3	2023-06-30	buy	29424.28064298088	100	294.2428064298088
24	3	2023-09-28	buy	29424.28064298088	100	294.2428064298088
25	3	2023-12-27	buy	29424.28064298088	100	294.2428064298088
26	3	2024-03-26	buy	29424.28064298088	100	294.2428064298088
27	3	2024-06-24	buy	29424.28064298088	100	294.2428064298088
28	3	2024-09-22	buy	29424.28064298088	100	294.2428064298088
29	3	2024-12-21	buy	29424.28064298088	100	294.2428064298088
30	3	2025-03-21	buy	29424.28064298088	100	294.2428064298088
31	4	2023-01-01	buy	9414.545901651203	100	94.14545901651204
32	4	2023-04-01	buy	9414.545901651203	100	94.14545901651204
33	4	2023-06-30	buy	9414.545901651203	100	94.14545901651204
34	4	2023-09-28	buy	9414.545901651203	100	94.14545901651204
35	4	2023-12-27	buy	9414.545901651203	100	94.14545901651204
36	4	2024-03-26	buy	9414.545901651203	100	94.14545901651204
37	4	2024-06-24	buy	9414.545901651203	100	94.14545901651204
38	4	2024-09-22	buy	9414.545901651203	100	94.14545901651204
39	4	2024-12-21	buy	9414.545901651203	100	94.14545901651204
40	4	2025-03-21	buy	9414.545901651203	100	94.14545901651204
41	5	2023-01-01	buy	18445.399365152356	100	184.45399365152355
42	5	2023-04-01	buy	18445.399365152356	100	184.45399365152355
43	5	2023-06-30	buy	18445.399365152356	100	184.45399365152355
44	5	2023-09-28	buy	18445.399365152356	100	184.45399365152355
45	5	2023-12-27	buy	18445.399365152356	100	184.45399365152355
46	5	2024-03-26	buy	18445.399365152356	100	184.45399365152355
47	5	2024-06-24	buy	18445.399365152356	100	184.45399365152355
48	5	2024-09-22	buy	18445.399365152356	100	184.45399365152355
49	5	2024-12-21	buy	18445.399365152356	100	184.45399365152355
50	5	2025-03-21	buy	18445.399365152356	100	184.45399365152355
51	6	2023-01-01	buy	47251.117409170525	100	472.51117409170524
52	6	2023-04-01	buy	47251.117409170525	100	472.51117409170524
53	6	2023-06-30	buy	47251.117409170525	100	472.51117409170524
54	6	2023-09-28	buy	47251.117409170525	100	472.51117409170524
55	6	2023-12-27	buy	47251.117409170525	100	472.51117409170524
56	6	2024-03-26	buy	47251.117409170525	100	472.51117409170524
57	6	2024-06-24	buy	47251.117409170525	100	472.51117409170524
58	6	2024-09-22	buy	47251.117409170525	100	472.51117409170524
59	6	2024-12-21	buy	47251.117409170525	100	472.51117409170524
60	6	2025-03-21	buy	47251.117409170525	100	472.51117409170524
\.


--
-- Data for Name: unit_prices; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unit_prices (id, investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) FROM stdin;
1	1	2023-01-01	147.25284017156892	-2.7471598284310885	-0.018656073629753328
2	1	2023-01-04	146.7174327164906	-0.5354074550783212	-0.0036492422554374685
3	1	2023-01-07	144.67785989110178	-2.0395728253888215	-0.014097338921960807
4	1	2023-01-10	145.88095676541494	1.2030968743131527	0.008247113955029802
5	1	2023-01-13	149.86198194094897	3.9810251755340396	0.026564610476743244
6	1	2023-01-16	151.1062319671368	1.2442500261878546	0.008234273398190878
7	1	2023-01-19	153.92219069485907	2.81595872772227	0.018294689771566005
8	1	2023-01-22	153.42572177923032	-0.4964689156287642	-0.003235891021866274
9	1	2023-01-25	155.46546488102484	2.0397431017945378	0.013120232865578986
10	1	2023-01-28	149.721062064865	-5.744402816159821	-0.03836736620042891
11	1	2023-01-31	150.33767806620094	0.6166160013359312	0.004101540008249997
12	1	2023-02-03	152.18113142148673	1.8434533552857975	0.012113547442225923
13	1	2023-02-06	151.21627687011542	-0.9648545513713171	-0.0063806262880024625
14	1	2023-02-09	151.98181613138394	0.7655392612685287	0.005037045093649505
15	1	2023-02-12	153.0006709786529	1.018854847268952	0.0066591528047030965
16	1	2023-02-15	153.42465945932724	0.42398848067435013	0.0027634963125777647
17	1	2023-02-18	155.6974638055139	2.2728043461866747	0.014597568198192995
18	1	2023-02-21	158.5822220840529	2.8847582785389805	0.01819093111843256
19	1	2023-02-24	157.97062633326678	-0.6115957507861198	-0.0038715789446567817
20	1	2023-02-27	157.03498538503231	-0.9356409482344604	-0.005958168786021617
21	1	2023-03-02	154.51320194602775	-2.5217834390045546	-0.01632082829974248
22	1	2023-03-05	152.37168055618488	-2.14152138984287	-0.014054589291303475
23	1	2023-03-08	153.672673560948	1.3009930047631049	0.008466000978678353
24	1	2023-03-11	150.7137895205507	-2.9588840403972907	-0.01963247059084683
25	1	2023-03-14	152.03605875556966	1.3222692350189384	0.008697076508308912
26	1	2023-03-17	149.86832085095725	-2.167737904612421	-0.014464283661176252
27	1	2023-03-20	152.05867207691838	2.190351225961128	0.014404645233605264
28	1	2023-03-23	152.14844469362515	0.08977261670676889	0.0005900330883272596
29	1	2023-03-26	152.93667649991136	0.7882318062862089	0.005153974993608978
30	1	2023-03-29	152.28962917379891	-0.6470473261124429	-0.004248794416420878
31	1	2023-04-01	153.21123176785076	0.9216025940518549	0.006015241724890565
32	1	2023-04-04	155.46976392670393	2.258532158853164	0.014527147284522455
33	1	2023-04-07	155.54755093984397	0.07778701314003118	0.0005000851036871311
34	1	2023-04-10	158.26061948368576	2.7130685438417865	0.017143042613462424
35	1	2023-04-13	161.01886998500703	2.7582505013212764	0.017129982973909243
36	1	2023-04-16	166.28391655665877	5.265046571651723	0.03166299351541757
37	1	2023-04-19	167.71124457444415	1.427328017785372	0.008510628022629725
38	1	2023-04-22	169.7746433184819	2.063398744037764	0.012153751017853792
39	1	2023-04-25	170.00654387669843	0.23190055821651726	0.001364068423064403
40	1	2023-04-28	167.95512199535517	-2.051421881343268	-0.012214107298257927
41	1	2023-05-01	171.66680717189467	3.71168517653951	0.02162144935114275
42	1	2023-05-04	172.81553838483103	1.1487312129363596	0.006647152354890271
43	1	2023-05-07	173.34342162887356	0.5278832440425234	0.0030453030122638046
44	1	2023-05-10	176.74382027913126	3.400398650257695	0.019239137441339958
45	1	2023-05-13	180.50944336308257	3.765623083951304	0.020861086344258494
46	1	2023-05-16	181.13631632800846	0.6268729649258961	0.0034607801330724364
47	1	2023-05-19	181.65104059242097	0.5147242644125	0.0028335883060940517
48	1	2023-05-22	181.06516896919317	-0.5858716232278075	-0.003235694786375446
49	1	2023-05-25	175.47763865512843	-5.5875303140647326	-0.03184183669718782
50	1	2023-05-28	175.0720832208312	-0.40555543429723	-0.0023165054464204518
51	1	2023-05-31	174.42314299121594	-0.6489402296152367	-0.00372049384322766
52	1	2023-06-03	176.54362995504204	2.12048696382609	0.012011121354908618
53	1	2023-06-06	177.9357687076786	1.3921387526365432	0.007823827456095212
54	1	2023-06-09	176.72594503410562	-1.2098236735729606	-0.006845761517017106
55	1	2023-06-12	174.9777466453792	-1.748198388726422	-0.009990975551133539
56	1	2023-06-15	175.8349888905145	0.8572422451353012	0.004875265443722763
57	1	2023-06-18	173.31806737241092	-2.5169215181035645	-0.014521980058174896
58	1	2023-06-21	168.77470126456654	-4.543366107844381	-0.026919710559714316
59	1	2023-06-24	171.52191025137196	2.74720898680541	0.01601666505917098
60	1	2023-06-27	171.67048568596573	0.1485754345937787	0.0008654687146721629
61	1	2023-06-30	173.40591394925102	1.735428263285294	0.010007895485001651
62	1	2023-07-03	172.20408414657894	-1.2018298026720768	-0.0069791016201978555
63	1	2023-07-06	174.98604239434934	2.7819582477703904	0.015898172275369007
64	1	2023-07-09	180.3828179340007	5.396775539651383	0.029918456765798945
65	1	2023-07-12	179.71204370013098	-0.6707742338697269	-0.00373249460669974
66	1	2023-07-15	184.62501913061143	4.912975430480459	0.026610561524193072
67	1	2023-07-18	184.8415626838334	0.21654355322194743	0.001171508994393969
68	1	2023-07-21	189.74810053247734	4.906537848643945	0.025858165825507907
69	1	2023-07-24	193.9761575451873	4.228057012709973	0.021796787121762813
70	1	2023-07-27	189.10577373586844	-4.87038380931886	-0.02575481283887989
71	1	2023-07-30	187.2404711338337	-1.8653026020347505	-0.009962069582176441
72	1	2023-08-02	183.92255364192118	-3.317917491912511	-0.01803975328861606
73	1	2023-08-05	183.6608081817237	-0.2617454601974802	-0.0014251568573002
74	1	2023-08-08	183.9464816103368	0.2856734286131166	0.001553024695619203
75	1	2023-08-11	179.90211069289055	-4.044370917446256	-0.022480953124281954
76	1	2023-08-14	181.31420975670636	1.4120990638158177	0.0077881323571418965
77	1	2023-08-17	184.15198803254472	2.837778275838365	0.01540997904044811
78	1	2023-08-20	184.0097127723494	-0.1422752601953259	-0.000773194295299749
79	1	2023-08-23	184.27392602518327	0.2642132528338701	0.0014338070422277873
80	1	2023-08-26	179.51192113130293	-4.762004893880357	-0.026527513403397967
81	1	2023-08-29	174.4622807893922	-5.049640341910728	-0.02894402342479155
82	1	2023-09-01	173.59506548958564	-0.8672152998065475	-0.004995621836143572
83	1	2023-09-04	172.02169429555101	-1.5733711940346082	-0.009146353315945105
84	1	2023-09-07	169.67026108913706	-2.3514332064139656	-0.013858841209530699
85	1	2023-09-10	169.7536861926603	0.08342510352324851	0.0004914479643674188
86	1	2023-09-13	171.3377359962398	1.5840498035794899	0.009245189300355023
87	1	2023-09-16	175.61612636578374	4.2783903695439465	0.024362172529831683
88	1	2023-09-19	174.49319585777104	-1.1229305080126997	-0.006435382780930882
89	1	2023-09-22	178.83742234138754	4.3442264836164926	0.024291484560338174
90	1	2023-09-25	176.19040214181143	-2.647020199576091	-0.01502363447383228
91	2	2023-01-01	102.61721726530371	2.6172172653037085	0.0255046602807132
92	2	2023-01-04	104.19363275913247	1.5764154938287656	0.01512967205465436
93	2	2023-01-07	105.69999576591594	1.506363006783475	0.014251306216884611
94	2	2023-01-10	107.70184457540186	2.0018488094859195	0.018586950087790082
95	2	2023-01-13	107.96125059349724	0.2594060180953821	0.002402769666610427
96	2	2023-01-16	108.01042947684768	0.04917888335042879	0.00045531606150099065
97	2	2023-01-19	110.89922435847421	2.888794881626533	0.026048828549861625
98	2	2023-01-22	111.4010667967516	0.5018424382773954	0.004504826144914699
99	2	2023-01-25	114.03399831848985	2.6329315217382376	0.023089004687747806
100	2	2023-01-28	115.36577461231005	1.331776293820198	0.011543946185908862
101	2	2023-01-31	117.80180002440129	2.4360254120912384	0.020679016887574245
102	2	2023-02-03	115.93581332287387	-1.8659867015274125	-0.016094998154976996
103	2	2023-02-06	116.05496634497348	0.11915302209960803	0.0010266947279569715
104	2	2023-02-09	114.88015363323386	-1.1748127117396212	-0.010226420095940382
105	2	2023-02-12	120.22693280173326	5.346779168499401	0.044472391035017066
106	2	2023-02-15	118.24335901036424	-1.9835737913690046	-0.01677535049723292
107	2	2023-02-18	118.13578106000283	-0.10757795036141611	-0.0009106296957293214
108	2	2023-02-21	117.07233227004966	-1.063448789953164	-0.009083690136966919
109	2	2023-02-24	117.29905934545924	0.22672707540958453	0.0019328976436362305
110	2	2023-02-27	118.99992064706366	1.7008613016044156	0.014292961645318413
111	2	2023-03-02	120.3412678304943	1.3413471834306452	0.011146194548323928
112	2	2023-03-05	116.48625745619437	-3.855010374299936	-0.033094121645633995
113	2	2023-03-08	114.65855253829183	-1.827704917902542	-0.01594041506229685
114	2	2023-03-11	116.4878845981412	1.8293320598493792	0.01570405425560084
115	2	2023-03-14	114.60974603697147	-1.8781385611697292	-0.01638725000371145
116	2	2023-03-17	116.1306471978441	1.5209011608726202	0.01309646676024772
117	2	2023-03-20	118.45390851033311	2.323261312489015	0.019613209405296657
118	2	2023-03-23	115.16105225834602	-3.2928562519870828	-0.028593488748262466
119	2	2023-03-26	115.57545408407702	0.41440182573099926	0.0035855522179435843
120	2	2023-03-29	116.51737939913352	0.9419253150564996	0.008083989872703095
121	2	2023-04-01	119.22928046534808	2.7119010662145704	0.022745260691250564
122	2	2023-04-04	117.81395045002508	-1.4153300153230088	-0.012013263369208308
123	2	2023-04-07	119.55281102363989	1.7388605736148126	0.014544706717694637
124	2	2023-04-10	117.2799051711758	-2.2729058524640897	-0.019380181533628218
125	2	2023-04-13	113.50984180882426	-3.770063362351543	-0.03321353727812576
126	2	2023-04-16	113.93410687650625	0.4242650676819881	0.003723775779818515
127	2	2023-04-19	112.96312276108927	-0.9709841154169883	-0.008595584927928787
128	2	2023-04-22	115.35979021120778	2.396667450118508	0.020775587799965155
129	2	2023-04-25	114.94315333432544	-0.4166368768823293	-0.003624721132110347
130	2	2023-04-28	116.24896280334231	1.3058094690168665	0.011232869846984328
131	2	2023-05-01	120.08373208546297	3.8347692821206634	0.03193412809148435
132	2	2023-05-04	117.15733442739614	-2.926397658066833	-0.02497835643299275
133	2	2023-05-07	116.56556145203727	-0.5917729753588585	-0.005076739372995281
134	2	2023-05-10	111.77461597596108	-4.790945476076193	-0.042862553668773624
135	2	2023-05-13	111.46109972141929	-0.31351625454179566	-0.002812786302354666
136	2	2023-05-16	111.27269418455599	-0.18840553686330155	-0.0016931875177823381
137	2	2023-05-19	113.1667781316327	1.8940839470767141	0.016737102339995615
138	2	2023-05-22	110.89513524903087	-2.2716428826018245	-0.02048460356264074
139	2	2023-05-25	110.40028223023798	-0.494853018792902	-0.0044823528418242095
140	2	2023-05-28	110.55451990540223	0.1542376751642573	0.0013951277188506924
141	2	2023-05-31	108.40253079745155	-2.1519891079506857	-0.019851834566221006
142	2	2023-06-03	108.12246304947233	-0.2800677479792234	-0.0025902827227592485
143	2	2023-06-06	105.03412952655312	-3.088333522919211	-0.02940314292925583
144	2	2023-06-09	106.01888480120287	0.9847552746497555	0.009288489277134734
145	2	2023-06-12	106.01221289871867	-0.0066719024841958175	-6.293522511948675e-05
146	2	2023-06-15	106.12848597351862	0.11627307479994453	0.0010955878031554808
147	2	2023-06-18	108.62458683588139	2.4961008623627636	0.02297915172864197
148	2	2023-06-21	109.4630587497821	0.8384719139007232	0.007659861906630598
149	2	2023-06-24	110.62438632901886	1.1613275792367548	0.010497934657759242
150	2	2023-06-27	111.32816752185023	0.7037811928313691	0.006321681282441291
151	2	2023-06-30	109.58946882788416	-1.7386986939660671	-0.015865563658281637
152	2	2023-07-03	106.96937514273046	-2.620093685153702	-0.02449386734902098
153	2	2023-07-06	104.8732127039533	-2.0961624387771516	-0.019987586770078367
154	2	2023-07-09	104.04324844519854	-0.8299642587547543	-0.007977108281004043
155	2	2023-07-12	103.53142177442137	-0.5118266707771623	-0.004943684361761705
156	2	2023-07-15	104.16317225102088	0.6317504765995041	0.006065008034481328
157	2	2023-07-18	103.4196300003117	-0.7435422507091776	-0.007189565952875065
158	2	2023-07-21	102.33235434783278	-1.0872756524789202	-0.010624945154522841
159	2	2023-07-24	103.60941628302179	1.277061935189014	0.012325732361048761
160	2	2023-07-27	106.09946837717006	2.4900520941482713	0.02346903459776494
161	2	2023-07-30	104.87513804584334	-1.2243303313267098	-0.011674171344513765
162	2	2023-08-02	103.35393671957873	-1.5212013262646136	-0.014718368497099024
163	2	2023-08-05	103.11137760444134	-0.24255911513738831	-0.0023523991316254174
164	2	2023-08-08	105.40598484535134	2.2946072409099987	0.021769231076172582
165	2	2023-08-11	106.40416459821643	0.9981797528650905	0.00938102147255449
166	2	2023-08-14	107.60414995654936	1.1999853583329425	0.011151850173227496
167	2	2023-08-17	109.5906134776437	1.9864635210943318	0.018126219555286704
168	2	2023-08-20	109.90309353135527	0.3124800537115614	0.0028432325576205103
169	2	2023-08-23	110.82206238709925	0.9189688557439828	0.008292291588420752
170	2	2023-08-26	109.60261821234407	-1.21944417475518	-0.011126049675133028
171	2	2023-08-29	109.29701718935196	-0.3056010229921071	-0.0027960600467501107
172	2	2023-09-01	107.7555260430271	-1.5414911463248604	-0.014305448666357384
173	2	2023-09-04	106.91016995560791	-0.8453560874191921	-0.007907162506337868
174	2	2023-09-07	108.59331753460258	1.6831475789946657	0.01549955022286101
175	2	2023-09-10	111.25985725283081	2.6665397182282318	0.023966772779230636
176	2	2023-09-13	112.45682372619235	1.1969664733615397	0.010643786954857359
177	2	2023-09-16	115.60699262901485	3.1501689028225055	0.02724894775985965
178	2	2023-09-19	115.97353673344668	0.36654410443182867	0.003160583998350355
179	2	2023-09-22	114.05617521457827	-1.9173615188684	-0.016810676977911925
180	2	2023-09-25	116.2661122449225	2.2099370303442254	0.019007576564432138
181	3	2023-01-01	81.41657977115301	1.4165797711530168	0.0173991559843801
182	3	2023-01-04	82.66384923451434	1.2472694633613308	0.015088451298981644
183	3	2023-01-07	83.85677788755463	1.192928653040288	0.014225786908243863
184	3	2023-01-10	82.03971724951747	-1.8170606380371614	-0.022148548275839515
185	3	2023-01-13	82.82116186918492	0.7814446196674498	0.009435325489658461
186	3	2023-01-16	83.55549295802466	0.7343310888397323	0.00878854355163262
187	3	2023-01-19	85.1659456606267	1.6104527026020394	0.01890958516470242
188	3	2023-01-22	84.91154583163497	-0.2543998289917402	-0.002996056973172664
189	3	2023-01-25	84.95284924933017	0.041303417695201336	0.00048619225911986704
190	3	2023-01-28	82.7629287424804	-2.1899205068497687	-0.026460162057142505
191	3	2023-01-31	82.72436655075867	-0.03856219172171897	-0.0004661527592122168
192	3	2023-02-03	82.10241982895273	-0.6219467218059377	-0.007575254457806046
193	3	2023-02-06	81.75467386806427	-0.3477459608884575	-0.004253530036088825
194	3	2023-02-09	82.18213002571856	0.4274561576542961	0.005201327314350765
195	3	2023-02-12	81.40867346803368	-0.7734565576848833	-0.009500910956233581
196	3	2023-02-15	80.3802073628192	-1.0284661052144828	-0.012795016820150823
197	3	2023-02-18	80.63994974973741	0.25974238691820556	0.0032210137496898844
198	3	2023-02-21	78.96231065753939	-1.6776390921980222	-0.021246073958929163
199	3	2023-02-24	79.39159660294177	0.42928594540238835	0.005407196274806767
200	3	2023-02-27	80.4382690844776	1.046672481535826	0.013012120890326384
201	3	2023-03-02	80.92302001312254	0.48475092864494795	0.005990272342361177
202	3	2023-03-05	78.66342875756338	-2.2595912555591515	-0.02872479996420058
203	3	2023-03-08	77.02466953656844	-1.6387592209949484	-0.021275770877756596
204	3	2023-03-11	78.67084704939101	1.6461775128225729	0.020924873375128047
205	3	2023-03-14	76.22232776033528	-2.4485192890557346	-0.03212338642759084
206	3	2023-03-17	75.24891942187567	-0.9734083384596037	-0.01293584473954085
207	3	2023-03-20	73.12809617251831	-2.1208232493573584	-0.029001483155722686
208	3	2023-03-23	74.0954748088037	0.9673786362853871	0.0130558396282852
209	3	2023-03-26	74.53039584776596	0.4349210389622571	0.005835485428664791
210	3	2023-03-29	75.95343918779591	1.4230433400299471	0.01873573277585829
211	3	2023-04-01	77.08108373255598	1.1276445447600751	0.014629329144782158
212	3	2023-04-04	76.28539375907043	-0.7956899734855513	-0.010430436736009411
213	3	2023-04-07	76.35031293004388	0.06491917097345672	0.0008502803522618045
214	3	2023-04-10	76.36162275342625	0.01130982338235712	0.00014810873544262996
215	3	2023-04-13	78.18818283735041	1.826560083924161	0.023361076030169806
216	3	2023-04-16	78.7313200199011	0.5431371825506958	0.006898616489770598
217	3	2023-04-19	78.32291251048129	-0.40840750941982173	-0.005214406568003559
218	3	2023-04-22	78.1440264064345	-0.17888610404678157	-0.0022891846283473794
219	3	2023-04-25	79.42851369067073	1.2844872842362232	0.016171614254782318
220	3	2023-04-28	79.30417599538136	-0.1243376952893729	-0.001567858107454698
221	3	2023-05-01	78.11707686981384	-1.1870991255675098	-0.015196409967386158
222	3	2023-05-04	80.56684338785512	2.449766518041279	0.030406633982765226
223	3	2023-05-07	79.80720317716435	-0.7596402106907679	-0.009518441700111195
224	3	2023-05-10	81.05008270946492	1.2428795323005684	0.015334710227944364
225	3	2023-05-13	79.19127246735158	-1.8588102421133295	-0.023472412858117245
226	3	2023-05-16	78.48203425660782	-0.709238210743763	-0.009036949888745378
227	3	2023-05-19	77.98453809916361	-0.4974961574442027	-0.0063794204539827665
228	3	2023-05-22	79.46997244499744	1.4854343458338166	0.01869176872889835
229	3	2023-05-25	77.92003629899287	-1.5499361460045733	-0.01989136837741189
230	3	2023-05-28	79.0906549810094	1.17061868201653	0.014800973418384378
231	3	2023-05-31	79.68127194372198	0.5906169627125858	0.007412243157083789
232	3	2023-06-03	79.39942266847963	-0.2818492752423515	-0.003549764793872253
233	3	2023-06-06	78.89181497071641	-0.5076076977632236	-0.006434225121473511
234	3	2023-06-09	77.61762332891692	-1.2741916417994896	-0.016416267171695035
235	3	2023-06-12	75.77845574086452	-1.839167588052409	-0.024270322878335113
236	3	2023-06-15	75.41193384154613	-0.3665218993183915	-0.00486026389521477
237	3	2023-06-18	75.61347556894584	0.20154172739971402	0.002665420758445951
238	3	2023-06-21	75.75796226332301	0.1444866943771644	0.001907214635406255
239	3	2023-06-24	73.98813170697167	-1.7698305563513352	-0.02392046556008076
240	3	2023-06-27	72.56484695732505	-1.423284749646623	-0.019613970253167464
241	3	2023-06-30	73.90703710271112	1.342190145386073	0.01816051891676818
242	3	2023-07-03	75.01450299476085	1.1074658920497358	0.014763357055462773
243	3	2023-07-06	75.57421337827569	0.559710383514841	0.007406102670408125
244	3	2023-07-09	73.41599010345898	-2.1582232748166996	-0.029397182708770897
245	3	2023-07-12	73.00537945818903	-0.4106106452699579	-0.005624388891850347
246	3	2023-07-15	73.4344202222842	0.429040764095176	0.005842502232556342
247	3	2023-07-18	74.20939632785291	0.7749761055687069	0.010443099444508433
248	3	2023-07-21	71.79413639487115	-2.4152599329817677	-0.03364146508703335
249	3	2023-07-24	70.87794130554076	-0.9161950893303908	-0.012926378397206197
250	3	2023-07-27	69.63828956106798	-1.2396517444727735	-0.0178012951249425
251	3	2023-07-30	70.10070813114595	0.462418570077968	0.00659648928528461
252	3	2023-08-02	68.86923147941232	-1.2314766517336297	-0.01788137641846295
253	3	2023-08-05	69.59564611846366	0.7264146390513432	0.010437644875296675
254	3	2023-08-08	68.63722871215553	-0.9584174063081335	-0.013963521317672306
255	3	2023-08-11	67.5931811120722	-1.044047600083336	-0.015446049185823395
256	3	2023-08-14	66.85011486945719	-0.7430662426150129	-0.011115407117340777
257	3	2023-08-17	65.64033400821195	-1.209780861245242	-0.018430449502190104
258	3	2023-08-20	65.51589952955746	-0.12443447865448687	-0.0018993019945997738
259	3	2023-08-23	65.19193008105155	-0.32396944850590176	-0.004969471652444073
260	3	2023-08-26	64.4202492083635	-0.7716808726880504	-0.01197885575065216
261	3	2023-08-29	65.2011217634877	0.7808725551242068	0.011976366878422197
262	3	2023-09-01	64.88878828206626	-0.3123334814214542	-0.004813365909435172
263	3	2023-09-04	64.63379199010555	-0.2549962919607076	-0.003945247278695077
264	3	2023-09-07	64.12139591497622	-0.5123960751293256	-0.007991031196650074
265	3	2023-09-10	64.0702976718643	-0.051098243111924034	-0.0007975340363427594
266	3	2023-09-13	64.51778626011777	0.44748858825348226	0.006935894955374518
267	3	2023-09-16	64.7056857026928	0.1878994425750364	0.0029039093015471554
268	3	2023-09-19	64.48290370060684	-0.22278200208596885	-0.003454900280550987
269	3	2023-09-22	66.53343144700227	2.0505277463954292	0.030819509858420472
270	3	2023-09-25	66.9635050577894	0.43007361078713346	0.006422507460085618
271	4	2023-01-01	120.33289448400951	0.3328944840095145	0.0027664462442873535
272	4	2023-01-04	118.83420592714701	-1.4986885568625026	-0.012611592303492942
273	4	2023-01-07	120.00834094124389	1.1741350140968823	0.009783778401467437
274	4	2023-01-10	120.62482573995493	0.6164847987110349	0.0051107621911932405
275	4	2023-01-13	120.85163470651977	0.22680896656484226	0.001876755470586996
276	4	2023-01-16	122.9197526676933	2.068117961173524	0.016824944049184394
277	4	2023-01-19	124.55771474416538	1.6379620764720813	0.013150225819704257
278	4	2023-01-22	127.22028480403772	2.6625700598723343	0.02092881700409328
279	4	2023-01-25	127.22343142857645	0.003146624538730092	2.4733058237755637e-05
280	4	2023-01-28	127.28244869008397	0.059017261507514594	0.00046367163827287664
281	4	2023-01-31	122.33092680993555	-4.951521880148413	-0.04047645194286436
282	4	2023-02-03	122.53156329815674	0.20063648822119906	0.0016374269846944592
283	4	2023-02-06	123.65219080785369	1.12062750969694	0.009062738819066392
284	4	2023-02-09	122.03468528221642	-1.6175055256372755	-0.013254473692431339
285	4	2023-02-12	122.54076721137955	0.5060819291631264	0.004129906648047573
286	4	2023-02-15	119.99878043341661	-2.541986777962939	-0.021183438438138164
287	4	2023-02-18	120.4089474145127	0.4101669810960774	0.0034064493536685517
288	4	2023-02-21	120.54204038327516	0.1330929687624643	0.0011041207560389904
289	4	2023-02-24	119.84476021220691	-0.6972801710682537	-0.00581819488673174
290	4	2023-02-27	118.24853251225613	-1.5962276999507778	-0.013498921855840649
291	4	2023-03-02	118.95476942860196	0.7062369163458341	0.005937020598150339
292	4	2023-03-05	120.17539459294554	1.2206251643435695	0.010157030634083077
293	4	2023-03-08	117.70627237444543	-2.4691222185001056	-0.020976980824313006
294	4	2023-03-11	115.52116498822957	-2.185107386215868	-0.018915212519182163
295	4	2023-03-14	115.67753230457821	0.1563673163486289	0.0013517518331642377
296	4	2023-03-17	117.06621548623616	1.3886831816579583	0.011862373579687729
297	4	2023-03-20	117.66143964669497	0.5952241604588172	0.005058786992969932
298	4	2023-03-23	120.24889711469476	2.587457467999777	0.021517515171318623
299	4	2023-03-26	120.51575412012663	0.26685700543187435	0.0022142914623915393
300	4	2023-03-29	122.17146376465648	1.6557096445298498	0.013552343513861028
301	4	2023-04-01	124.11736983285135	1.945906068194875	0.015677951207114873
302	4	2023-04-04	124.27570020773909	0.15833037488774562	0.001274025208653669
303	4	2023-04-07	126.29747199031517	2.0217717825760873	0.016008014655519962
304	4	2023-04-10	126.82681275237884	0.5293407620636742	0.004173729123802691
305	4	2023-04-13	126.68693482675248	-0.13987792562636323	-0.0011041227401835064
306	4	2023-04-16	125.68484144896154	-1.0020933777909369	-0.007973064740650286
307	4	2023-04-19	126.03476509566914	0.3499236467076047	0.002776405751555837
308	4	2023-04-22	123.93505702934883	-2.09970806632032	-0.01694200266372647
309	4	2023-04-25	124.13464826894788	0.1995912395990572	0.001607860838068566
310	4	2023-04-28	123.51595781411925	-0.618690454828635	-0.005008992083109701
311	4	2023-05-01	125.1017255294778	1.5857677153585579	0.012675826081910455
312	4	2023-05-04	126.46558449190707	1.363858962429268	0.01078442777858308
313	4	2023-05-07	127.15071657083321	0.6851320789261488	0.005388346187923171
314	4	2023-05-10	125.63092702300109	-1.5197895478321155	-0.012097256494444758
315	4	2023-05-13	125.49345194282155	-0.13747508017953464	-0.0010954761228671298
316	4	2023-05-16	125.01942461531362	-0.4740273275079293	-0.003791629412521434
317	4	2023-05-19	122.37264651956984	-2.646778095743779	-0.021628837579487227
318	4	2023-05-22	122.89261870833833	0.5199721887684868	0.004231110006716835
319	4	2023-05-25	124.75174079636461	1.859122088026283	0.014902574314060871
320	4	2023-05-28	121.7165159327967	-3.0352248635679193	-0.02493683655259864
321	4	2023-05-31	120.34591386832425	-1.3706020644724544	-0.011388854182220846
322	4	2023-06-03	119.80992999904393	-0.5359838692803103	-0.004473618082279051
323	4	2023-06-06	120.3960521353004	0.5861221362564603	0.0048682836842339275
324	4	2023-06-09	117.36173226370497	-3.0343198715954247	-0.025854423013947043
325	4	2023-06-12	117.58539595791368	0.22366369420870755	0.0019021383768504853
326	4	2023-06-15	118.83328395438394	1.2478879964702625	0.010501165624180547
327	4	2023-06-18	113.49838308114656	-5.334900873237395	-0.047004201543762655
328	4	2023-06-21	111.53682740509375	-1.961555676052812	-0.017586618892507875
329	4	2023-06-24	111.66314298936221	0.12631558426846717	0.0011312200327416974
330	4	2023-06-27	111.10680263529157	-0.5563403540706409	-0.005007257349460679
331	4	2023-06-30	108.29157643971126	-2.8152261955803124	-0.025996723735457136
332	4	2023-07-03	107.24607615028614	-1.0455002894251204	-0.009748611109650663
333	4	2023-07-06	107.57503178019809	0.3289556299119512	0.003057918036074462
334	4	2023-07-09	106.03528205091456	-1.5397497292835292	-0.014521107498390898
335	4	2023-07-12	106.54880454199666	0.5135224910820934	0.004819598805350146
336	4	2023-07-15	108.61527693205801	2.0664723900613433	0.019025614521555576
337	4	2023-07-18	109.09346686670773	0.47818993464971365	0.004383304962101666
338	4	2023-07-21	108.708964856865	-0.38450200984273786	-0.0035369852923262056
339	4	2023-07-24	109.91454953227449	1.2055846754094994	0.010968381170097054
340	4	2023-07-27	107.39528294354501	-2.519266588729477	-0.023457888649111264
341	4	2023-07-30	106.37711795308832	-1.0181649904566907	-0.009571278203886813
342	4	2023-08-02	102.72162904289935	-3.655488910188968	-0.03558636038241115
343	4	2023-08-05	101.8442036406545	-0.8774254022448589	-0.008615369072360298
344	4	2023-08-08	101.05807503383993	-0.7861286068145732	-0.007778978637296753
345	4	2023-08-11	98.52970561468584	-2.5283694191540915	-0.0256609862313162
346	4	2023-08-14	100.21651355830735	1.6868079436215209	0.01683163666075963
347	4	2023-08-17	98.93084996243476	-1.285663595872595	-0.012995578187802663
348	4	2023-08-20	98.70777298404164	-0.22307697839312673	-0.002259973775613317
349	4	2023-08-23	97.56431053142488	-1.143462452616762	-0.011720089512121952
350	4	2023-08-26	95.51429873550674	-2.0500117959181376	-0.0214628785748082
351	4	2023-08-29	96.49666636649852	0.9823676309917708	0.01018032713441826
352	4	2023-09-01	100.59101888826564	4.094352521767127	0.040702963018150226
353	4	2023-09-04	99.29818833659394	-1.2928305516716962	-0.01301967914348398
354	4	2023-09-07	99.82754903517504	0.5293606985810988	0.005302751632162924
355	4	2023-09-10	100.927538065037	1.0999890298619626	0.010898799782009319
356	4	2023-09-13	101.63676527754286	0.7092272125058667	0.006978057699584954
357	4	2023-09-16	101.96044589311352	0.3236806155706487	0.0031745704202781476
358	4	2023-09-19	103.1882015970514	1.2277557039378864	0.011898217867312549
359	4	2023-09-22	104.83660209278266	1.6484004957312486	0.015723520820260642
360	4	2023-09-25	105.31608923000705	0.4794871372243906	0.004552838419372046
361	5	2023-01-01	99.24821889880737	-0.7517811011926367	-0.007574756600510346
362	5	2023-01-04	101.34921727167529	2.1009983728679242	0.02073028711446303
363	5	2023-01-07	99.62074704709451	-1.7284702245807748	-0.0173505045466449
364	5	2023-01-10	104.43379902021634	4.813051973121827	0.04608710990385512
365	5	2023-01-13	102.58109361974334	-1.8527054004729928	-0.018060885637861932
366	5	2023-01-16	103.19366166225147	0.6125680425081264	0.005936101429495117
367	5	2023-01-19	102.55542729146578	-0.6382343707856981	-0.0062233115071698335
368	5	2023-01-22	105.17008822953308	2.614660938067298	0.024861260288769713
369	5	2023-01-25	106.02692854150958	0.8568403119764921	0.008081346161423877
370	5	2023-01-28	104.38307024827932	-1.6438582932302543	-0.01574832287764933
371	5	2023-01-31	104.85399962687849	0.4709293785991648	0.004491286744186779
372	5	2023-02-03	105.58949828797738	0.7354986610988845	0.006965642161618546
373	5	2023-02-06	104.45554988085188	-1.1339484071255084	-0.010855798551814207
374	5	2023-02-09	103.59309563678916	-0.8624542440627115	-0.00832540275740565
375	5	2023-02-12	102.83190018195371	-0.7611954548354515	-0.007402328008026405
376	5	2023-02-15	101.15514100172358	-1.6767591802301307	-0.01657611430942062
377	5	2023-02-18	99.18089034745948	-1.9742506542640998	-0.01990555486392314
378	5	2023-02-21	99.60248937957147	0.4215990321119782	0.004232816215118097
379	5	2023-02-24	101.03993701676337	1.4374476371919152	0.014226529426215205
380	5	2023-02-27	98.83199165571564	-2.2079453610477366	-0.02234039124435723
381	5	2023-03-02	98.9594198565049	0.12742820078925754	0.001287681364482871
382	5	2023-03-05	97.12482725134761	-1.8345926051572772	-0.018889017948104738
383	5	2023-03-08	97.47151694014666	0.34668968879904044	0.0035568307509970185
384	5	2023-03-11	96.69238816828812	-0.7791287718585348	-0.00805780875431995
385	5	2023-03-14	95.53486820661706	-1.1575199616710503	-0.012116204098043405
386	5	2023-03-17	95.08697599224128	-0.44789221437579024	-0.0047103423965479405
387	5	2023-03-20	91.67465772003996	-3.4123182722013157	-0.037222045405634355
388	5	2023-03-23	94.28667868175177	2.612020961711812	0.02770296926597906
389	5	2023-03-26	96.38278525994137	2.0961065781896067	0.021747727797411878
390	5	2023-03-29	94.34635734843101	-2.036427911510356	-0.0215845949832447
391	5	2023-04-01	92.25828677306345	-2.088070575367561	-0.02263287828554402
392	5	2023-04-04	92.43300062174266	0.17471384867921258	0.0018901674456526872
393	5	2023-04-07	91.54170352269954	-0.8912970990431334	-0.009736514230610959
394	5	2023-04-10	91.97628847940132	0.4345849567017832	0.004724967313712722
395	5	2023-04-13	94.00798641238364	2.031697932982326	0.02161197160494325
396	5	2023-04-16	94.0528927859895	0.04490637360585893	0.00047745871791567444
397	5	2023-04-19	94.89092017690089	0.8380273909113891	0.008831481340354717
398	5	2023-04-22	94.52920805725603	-0.3617121196448704	-0.003826458795949952
399	5	2023-04-25	91.3739066036309	-3.155301453625121	-0.034531756065902294
400	5	2023-04-28	94.06097961065527	2.687073007024362	0.02856735086267344
401	5	2023-05-01	94.78412608322817	0.7231464725729034	0.007629404864037276
402	5	2023-05-04	93.48369508309392	-1.3004310001342583	-0.013910778761776127
403	5	2023-05-07	91.26968339163774	-2.2140116914561823	-0.02425790918936214
404	5	2023-05-10	91.95038146495129	0.6806980733135484	0.007402884713132048
405	5	2023-05-13	91.63136901898366	-0.3190124459676298	-0.003481476369752138
406	5	2023-05-16	90.18232518949446	-1.4490438294892036	-0.01606793600014658
407	5	2023-05-19	89.78192008862229	-0.40040510087217185	-0.004459752035565049
408	5	2023-05-22	91.05129946973149	1.2693793811092093	0.013941364796569364
409	5	2023-05-25	90.03305824725857	-1.0182412224729172	-0.011309637174342257
410	5	2023-05-28	88.67766051756297	-1.3553977296955915	-0.01528454541746903
411	5	2023-05-31	89.28527506722155	0.6076145496585773	0.006805316433209321
412	5	2023-06-03	88.5911778404509	-0.6940972267706578	-0.007834834615481675
413	5	2023-06-06	88.7055940323626	0.11441619191170449	0.001289841899598371
414	5	2023-06-09	88.25215223272583	-0.4534417996367602	-0.005138025398417581
415	5	2023-06-12	88.17559200658307	-0.07656022614275888	-0.0008682700552443469
416	5	2023-06-15	89.36833121852683	1.1927392119437652	0.01334632968615285
417	5	2023-06-18	87.85055817731912	-1.5177730412077115	-0.017276760360978145
418	5	2023-06-21	87.28341884854571	-0.5671393287734066	-0.006497675460645135
419	5	2023-06-24	88.30988321254773	1.0264643640020308	0.011623437000041044
420	5	2023-06-27	89.53633333166609	1.2264501191183572	0.013697792543896834
421	5	2023-06-30	90.35033442852169	0.8140010968556091	0.009009386650356948
422	5	2023-07-03	93.11220829420722	2.761873865685535	0.029661780300160263
423	5	2023-07-06	91.77945893116528	-1.3327493630419451	-0.014521216169312014
424	5	2023-07-09	92.28424909338206	0.5047901622167854	0.005469949283609495
425	5	2023-07-12	92.58127851007659	0.2970294166945342	0.0032083097303760542
426	5	2023-07-15	91.0149436318109	-1.5663348782656883	-0.017209645095228453
427	5	2023-07-18	91.24756743266893	0.2326238008580359	0.0025493698890075916
428	5	2023-07-21	91.57951414771058	0.331946715041648	0.0036246830760233557
429	5	2023-07-24	91.95110720787109	0.37159306016050153	0.0040412026722033085
430	5	2023-07-27	92.52123804572197	0.5701308378508873	0.0061621617900221035
431	5	2023-07-30	93.42674789214053	0.9055098464185602	0.009692190586190102
432	5	2023-08-02	92.57758596460862	-0.8491619275319052	-0.0091724354084641
433	5	2023-08-05	90.35935286176677	-2.218233102841854	-0.02454901493413021
434	5	2023-08-08	91.47709612279283	1.1177432610260594	0.012218831908761888
435	5	2023-08-11	92.55470390578094	1.077607782988107	0.011642928317129
436	5	2023-08-14	93.12177312865867	0.56706922287774	0.006089544945565708
437	5	2023-08-17	94.37925210446097	1.257478975802301	0.013323680234406778
438	5	2023-08-20	94.84844836068896	0.469196256227993	0.004946799492636263
439	5	2023-08-23	94.72588803850648	-0.12256032218247456	-0.0012938418918031496
440	5	2023-08-26	92.31327162146772	-2.4126164170387567	-0.02613509817885921
441	5	2023-08-29	93.70655042269802	1.3932788012302937	0.014868531548172406
442	5	2023-09-01	92.17994160862256	-1.5266088140754552	-0.016561182264110432
443	5	2023-09-04	90.18317345645464	-1.9967681521679133	-0.022141249588339913
444	5	2023-09-07	88.14251342608146	-2.0406600303731772	-0.023151824823835165
445	5	2023-09-10	88.33248928878885	0.18997586270738495	0.002150690694182629
446	5	2023-09-13	88.97446859449349	0.641979305704641	0.007215320482896059
447	5	2023-09-16	88.1241802415583	-0.8502883529351792	-0.009648751915812924
448	5	2023-09-19	88.0642967953594	-0.05988344619891187	-0.0006799968702193449
449	5	2023-09-22	88.39957854725102	0.3352817518916336	0.0037927980811856476
450	5	2023-09-25	88.6625115312634	0.26293298401237647	0.0029655485669347783
451	6	2023-01-01	50.48375949028741	0.48375949028740806	0.009582477516962236
452	6	2023-01-04	50.03477112437441	-0.4489883659130009	-0.008973526925843706
453	6	2023-01-07	49.318969263359456	-0.7158018610149554	-0.014513723050306043
454	6	2023-01-10	49.37801862207146	0.059049358712003855	0.0011958632679037755
455	6	2023-01-13	49.41674918019877	0.038730558127315705	0.0007837536618623831
456	6	2023-01-16	49.684543052523715	0.2677938723249465	0.005389882967059792
457	6	2023-01-19	49.67652025815437	-0.008022794369343732	-0.00016150073168675288
458	6	2023-01-22	49.91834977816679	0.24182952001242072	0.004844501492679386
459	6	2023-01-25	50.11386125398297	0.1955114758161746	0.0039013452750188086
460	6	2023-01-28	49.442305100373524	-0.6715561536094465	-0.013582622255295558
461	6	2023-01-31	49.1004190209229	-0.3418860794506225	-0.006962997185521704
462	6	2023-02-03	47.958645563883486	-1.1417734570394156	-0.023807458355313896
463	6	2023-02-06	47.80711034010421	-0.15153522377927356	-0.0031697214640508064
464	6	2023-02-09	47.31593513878642	-0.49117520131779047	-0.010380756501527073
465	6	2023-02-12	47.52406067998056	0.20812554119413376	0.0043793720110665195
466	6	2023-02-15	47.13856140088639	-0.38549927909416914	-0.008178002629645806
467	6	2023-02-18	47.33932168459868	0.20076028371229077	0.004240877912232652
468	6	2023-02-21	47.62229211539858	0.28297043079989953	0.005941974193812515
469	6	2023-02-24	47.451767496905305	-0.17052461849327727	-0.0035936410272683415
470	6	2023-02-27	46.363343487962474	-1.0884240089428334	-0.02347596025350126
471	6	2023-03-02	46.439342792779755	0.07599930481727833	0.0016365284314293627
472	6	2023-03-05	46.0597933891432	-0.3795494036365494	-0.008240362704840385
473	6	2023-03-08	43.75490693384378	-2.3048864552994255	-0.05267721078196671
474	6	2023-03-11	43.06154188730485	-0.6933650465389267	-0.016101723629718435
475	6	2023-03-14	44.76213791476468	1.7005960274598295	0.037991841021938595
476	6	2023-03-17	46.2627857295702	1.5006478148055178	0.03243747195807829
477	6	2023-03-20	46.90796324791819	0.6451775183479939	0.013754114945006215
478	6	2023-03-23	47.55138135018325	0.6434181022650624	0.013531007596324703
479	6	2023-03-26	47.85308252332137	0.30170117313811706	0.006304738529457991
480	6	2023-03-29	48.46281407606997	0.6097315527485964	0.012581431028572284
481	6	2023-04-01	49.92080741214936	1.4579933360793906	0.02920612489381642
482	6	2023-04-04	49.679994136592235	-0.2408132755571212	-0.004847288727430587
483	6	2023-04-07	50.44524775804485	0.7652536214526161	0.01516998439819489
484	6	2023-04-10	47.771925830044125	-2.6733219280007257	-0.05596010379634838
485	6	2023-04-13	48.17332325998892	0.4013974299447945	0.008332359131182904
486	6	2023-04-16	47.367799573224204	-0.8055236867647125	-0.017005723171064385
487	6	2023-04-19	47.35284753044711	-0.014952042777100077	-0.0003157580495552281
488	6	2023-04-22	46.62968143160796	-0.7231660988391463	-0.01550870768653692
489	6	2023-04-25	46.071309081023415	-0.5583723505845464	-0.012119741368810761
490	6	2023-04-28	46.27534415131817	0.2040350702947565	0.004409152952543616
491	6	2023-05-01	45.88640175285611	-0.388942398462061	-0.008476201741790574
492	6	2023-05-04	45.796020423976636	-0.09038132887947375	-0.0019735629437389796
493	6	2023-05-07	46.72274655268865	0.9267261287120144	0.01983458159222205
494	6	2023-05-10	47.03057802928136	0.30783147659270715	0.006545347505638789
495	6	2023-05-13	47.68762572876813	0.6570476994867727	0.013778159206831737
496	6	2023-05-16	48.74051781897966	1.052892090211526	0.021601988188183086
497	6	2023-05-19	48.58714786824536	-0.15336995073429865	-0.0031565950557582573
498	6	2023-05-22	48.530896938820675	-0.056250929424687096	-0.0011590745890313649
499	6	2023-05-25	49.28085982369832	0.7499628848776478	0.015218137174566982
500	6	2023-05-28	49.014499763724636	-0.266360059973686	-0.0054343115049154825
501	6	2023-05-31	49.30632555127382	0.2918257875491847	0.005918627768068298
502	6	2023-06-03	49.093757931169876	-0.21256762010394634	-0.0043298298818755954
503	6	2023-06-06	49.522290847657985	0.4285329164881067	0.008653333865478336
504	6	2023-06-09	49.68752070460185	0.1652298569438704	0.003325379383008086
505	6	2023-06-12	49.37465134058917	-0.3128693640126863	-0.006336639460084397
506	6	2023-06-15	48.71974990747116	-0.654901433118005	-0.01344221664441623
507	6	2023-06-18	48.0014120279392	-0.7183378795319558	-0.014964932263114418
508	6	2023-06-21	48.26859311382946	0.26718108589025946	0.005535298807242618
509	6	2023-06-24	49.37809838633776	1.1095052725083008	0.02246958284678062
510	6	2023-06-27	50.05300217837241	0.6749037920346509	0.013483782443848546
511	6	2023-06-30	49.590660337018384	-0.46234184135402634	-0.009323163640329627
512	6	2023-07-03	50.19037338389941	0.5997130468810283	0.011948766395776814
513	6	2023-07-06	49.270344364758294	-0.9200290191411156	-0.018673078725205475
514	6	2023-07-09	48.86940474626092	-0.4009396184973719	-0.008204307389851081
515	6	2023-07-12	46.881358696310194	-1.988046049950722	-0.042405896612957836
516	6	2023-07-15	47.887907266468865	1.0065485701586694	0.02101884646071087
517	6	2023-07-18	47.58109645612131	-0.3068108103475563	-0.006448166040698398
518	6	2023-07-21	48.566380909131624	0.9852844530103174	0.020287376464262354
519	6	2023-07-24	48.8310867702718	0.26470586114018235	0.005420847223521848
520	6	2023-07-27	49.16949091842889	0.3384041481570897	0.006882400892018483
521	6	2023-07-30	48.33199724600568	-0.8374936724232147	-0.017327934290826935
522	6	2023-08-02	49.7538482473327	1.4218510013270222	0.028577709090135506
523	6	2023-08-05	49.48590912024078	-0.26793912709192313	-0.005414452959546224
524	6	2023-08-08	49.3129623495956	-0.17294677064517822	-0.003507125964550708
525	6	2023-08-11	49.32729722130658	0.014334871710975777	0.00029060728072455446
526	6	2023-08-14	49.06527779629231	-0.2620194250142758	-0.005340220962410931
527	6	2023-08-17	48.41561060207718	-0.6496671942151251	-0.01341854798764538
528	6	2023-08-20	47.96921941151273	-0.446391190564447	-0.00930578391812046
529	6	2023-08-23	48.818309911844146	0.8490905003314124	0.017392869639786705
530	6	2023-08-26	49.294235977477065	0.47592606563291956	0.009654801544147556
531	6	2023-08-29	48.586171277034644	-0.7080647004424196	-0.01457337925240268
532	6	2023-09-01	49.313904795280635	0.72773351824599	0.014757166792349294
533	6	2023-09-04	50.527688030978794	1.2137832356981586	0.024022140790490584
534	6	2023-09-07	48.28132525836985	-2.2463627726089492	-0.04652653506480809
535	6	2023-09-10	48.619750959766684	0.33842570139683714	0.006960662996338416
536	6	2023-09-13	49.06726131642312	0.447510356656438	0.009120345106904376
537	6	2023-09-16	49.33057830386363	0.2633169874405093	0.005337804592894586
538	6	2023-09-19	50.4808922776632	1.150313973799569	0.022787116508805456
539	6	2023-09-22	50.71285755950418	0.23196528184097934	0.004574092113993019
540	6	2023-09-25	51.79458882456548	1.0817312650613031	0.020885024663971314
\.


--
-- Data for Name: unit_prices_backup_20260808; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unit_prices_backup_20260808 (id, investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) FROM stdin;
\.


--
-- Name: configuration_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.configuration_id_seq', 593, true);


--
-- Name: dividends_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.dividends_id_seq', 24, true);


--
-- Name: factsheets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.factsheets_id_seq', 1, false);


--
-- Name: fees_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.fees_id_seq', 1, false);


--
-- Name: inflation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.inflation_id_seq', 1, false);


--
-- Name: investment_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.investment_metrics_id_seq', 1, false);


--
-- Name: investment_source_meta_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.investment_source_meta_id_seq', 1, false);


--
-- Name: investments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.investments_id_seq', 6, true);


--
-- Name: portfolio_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.portfolio_metrics_id_seq', 1, false);


--
-- Name: prediction_accuracy_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.prediction_accuracy_id_seq', 1, false);


--
-- Name: predictions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.predictions_id_seq', 1, false);


--
-- Name: property_investments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.property_investments_id_seq', 1, false);


--
-- Name: returns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.returns_id_seq', 1, false);


--
-- Name: tax_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tax_id_seq', 1, false);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.transactions_id_seq', 60, true);


--
-- Name: unit_prices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unit_prices_id_seq', 540, true);


--
-- Name: configuration configuration_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.configuration
    ADD CONSTRAINT configuration_pkey PRIMARY KEY (id);


--
-- Name: configuration configuration_setting_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.configuration
    ADD CONSTRAINT configuration_setting_key_key UNIQUE (setting_key);


--
-- Name: dividends dividends_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dividends
    ADD CONSTRAINT dividends_pkey PRIMARY KEY (id);


--
-- Name: factsheets factsheets_investment_id_factsheet_year_factsheet_month_fac_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.factsheets
    ADD CONSTRAINT factsheets_investment_id_factsheet_year_factsheet_month_fac_key UNIQUE (investment_id, factsheet_year, factsheet_month, factsheet_type);


--
-- Name: factsheets factsheets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.factsheets
    ADD CONSTRAINT factsheets_pkey PRIMARY KEY (id);


--
-- Name: fees fees_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fees
    ADD CONSTRAINT fees_pkey PRIMARY KEY (id);


--
-- Name: inflation inflation_inflation_date_country_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inflation
    ADD CONSTRAINT inflation_inflation_date_country_key UNIQUE (inflation_date, country);


--
-- Name: inflation inflation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inflation
    ADD CONSTRAINT inflation_pkey PRIMARY KEY (id);


--
-- Name: investment_metrics investment_metrics_investment_id_metrics_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_metrics
    ADD CONSTRAINT investment_metrics_investment_id_metrics_date_key UNIQUE (investment_id, metrics_date);


--
-- Name: investment_metrics investment_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_metrics
    ADD CONSTRAINT investment_metrics_pkey PRIMARY KEY (id);


--
-- Name: investment_source_meta investment_source_meta_investment_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_source_meta
    ADD CONSTRAINT investment_source_meta_investment_id_key UNIQUE (investment_id);


--
-- Name: investment_source_meta investment_source_meta_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_source_meta
    ADD CONSTRAINT investment_source_meta_pkey PRIMARY KEY (id);


--
-- Name: investments investments_investment_ticker_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_investment_ticker_key UNIQUE (investment_ticker);


--
-- Name: investments investments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_pkey PRIMARY KEY (id);


--
-- Name: portfolio_metrics portfolio_metrics_metrics_date_dimension_type_dimension_val_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.portfolio_metrics
    ADD CONSTRAINT portfolio_metrics_metrics_date_dimension_type_dimension_val_key UNIQUE (metrics_date, dimension_type, dimension_value);


--
-- Name: portfolio_metrics portfolio_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.portfolio_metrics
    ADD CONSTRAINT portfolio_metrics_pkey PRIMARY KEY (id);


--
-- Name: prediction_accuracy prediction_accuracy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction_accuracy
    ADD CONSTRAINT prediction_accuracy_pkey PRIMARY KEY (id);


--
-- Name: prediction_accuracy prediction_accuracy_prediction_id_actual_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction_accuracy
    ADD CONSTRAINT prediction_accuracy_prediction_id_actual_date_key UNIQUE (prediction_id, actual_date);


--
-- Name: predictions predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (id);


--
-- Name: property_investments property_investments_investment_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.property_investments
    ADD CONSTRAINT property_investments_investment_id_key UNIQUE (investment_id);


--
-- Name: property_investments property_investments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.property_investments
    ADD CONSTRAINT property_investments_pkey PRIMARY KEY (id);


--
-- Name: returns returns_investment_id_returns_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.returns
    ADD CONSTRAINT returns_investment_id_returns_date_key UNIQUE (investment_id, returns_date);


--
-- Name: returns returns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.returns
    ADD CONSTRAINT returns_pkey PRIMARY KEY (id);


--
-- Name: tax tax_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tax
    ADD CONSTRAINT tax_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: unit_prices unit_prices_investment_id_unit_price_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unit_prices
    ADD CONSTRAINT unit_prices_investment_id_unit_price_date_key UNIQUE (investment_id, unit_price_date);


--
-- Name: unit_prices unit_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unit_prices
    ADD CONSTRAINT unit_prices_pkey PRIMARY KEY (id);


--
-- Name: dividends dividends_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dividends
    ADD CONSTRAINT dividends_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- Name: factsheets factsheets_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.factsheets
    ADD CONSTRAINT factsheets_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id) ON DELETE CASCADE;


--
-- Name: fees fees_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fees
    ADD CONSTRAINT fees_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- Name: investment_metrics investment_metrics_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_metrics
    ADD CONSTRAINT investment_metrics_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- Name: investment_source_meta investment_source_meta_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investment_source_meta
    ADD CONSTRAINT investment_source_meta_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id) ON DELETE CASCADE;


--
-- Name: investments investments_price_source_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investments
    ADD CONSTRAINT investments_price_source_investment_id_fkey FOREIGN KEY (price_source_investment_id) REFERENCES public.investments(id);


--
-- Name: prediction_accuracy prediction_accuracy_prediction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction_accuracy
    ADD CONSTRAINT prediction_accuracy_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES public.predictions(id);


--
-- Name: property_investments property_investments_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.property_investments
    ADD CONSTRAINT property_investments_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id) ON DELETE CASCADE;


--
-- Name: returns returns_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.returns
    ADD CONSTRAINT returns_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- Name: tax tax_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tax
    ADD CONSTRAINT tax_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- Name: transactions transactions_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- Name: unit_prices unit_prices_investment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unit_prices
    ADD CONSTRAINT unit_prices_investment_id_fkey FOREIGN KEY (investment_id) REFERENCES public.investments(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 6Xnl4jViyRSrQQoKwK3LzsN8gQV326nhuQPk7qtLBPtABvzY4896mU3VwK4vDqL

