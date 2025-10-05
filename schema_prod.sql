

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";





SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."account" (
    "id" integer NOT NULL,
    "name" character varying(100) NOT NULL
);


ALTER TABLE "public"."account" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."account_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."account_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."account_id_seq" OWNED BY "public"."account"."id";



CREATE TABLE IF NOT EXISTS "public"."asset" (
    "id" integer NOT NULL,
    "name" character varying(150) NOT NULL,
    "ticker" character varying(20),
    "current_value" double precision NOT NULL,
    "quantity" double precision,
    "purchase_price_per_unit" double precision,
    "currency" character varying(10) NOT NULL,
    "last_updated" timestamp without time zone,
    "portfolio_id" integer NOT NULL,
    "asset_category_id" integer NOT NULL,
    "invested_amount" double precision
);


ALTER TABLE "public"."asset" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."asset_category" (
    "id" integer NOT NULL,
    "name" character varying(100) NOT NULL
);


ALTER TABLE "public"."asset_category" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."asset_category_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."asset_category_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."asset_category_id_seq" OWNED BY "public"."asset_category"."id";



CREATE SEQUENCE IF NOT EXISTS "public"."asset_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."asset_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."asset_id_seq" OWNED BY "public"."asset"."id";



CREATE TABLE IF NOT EXISTS "public"."asset_value_history" (
    "id" integer NOT NULL,
    "asset_id" integer NOT NULL,
    "date" "date" NOT NULL,
    "value" double precision NOT NULL
);


ALTER TABLE "public"."asset_value_history" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."asset_value_history_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."asset_value_history_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."asset_value_history_id_seq" OWNED BY "public"."asset_value_history"."id";



CREATE TABLE IF NOT EXISTS "public"."category" (
    "id" integer NOT NULL,
    "name" character varying(100) NOT NULL,
    "is_shared_expense" boolean,
    "color" character varying
);


ALTER TABLE "public"."category" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."category_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."category_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."category_id_seq" OWNED BY "public"."category"."id";



CREATE TABLE IF NOT EXISTS "public"."import_task" (
    "id" character varying(36) NOT NULL,
    "status" character varying(50),
    "progress" integer,
    "total_rows" integer,
    "summary" "text",
    "error_message" "text",
    "created_at" timestamp without time zone
);


ALTER TABLE "public"."import_task" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."portfolio" (
    "id" integer NOT NULL,
    "name" character varying(100) NOT NULL,
    "description" character varying(255),
    "created_at" timestamp without time zone,
    "target_allocation" "text"
);


ALTER TABLE "public"."portfolio" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."portfolio_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."portfolio_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."portfolio_id_seq" OWNED BY "public"."portfolio"."id";



CREATE TABLE IF NOT EXISTS "public"."portfolio_snapshot" (
    "id" integer NOT NULL,
    "portfolio_id" integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    "total_value" double precision NOT NULL,
    "currency" character varying(10) NOT NULL
);


ALTER TABLE "public"."portfolio_snapshot" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."portfolio_snapshot_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."portfolio_snapshot_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."portfolio_snapshot_id_seq" OWNED BY "public"."portfolio_snapshot"."id";



CREATE TABLE IF NOT EXISTS "public"."savings_goal" (
    "year" integer NOT NULL,
    "goal_total" double precision,
    "goal_tomek" double precision,
    "goal_tocka" double precision
);


ALTER TABLE "public"."savings_goal" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."savings_goal_year_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."savings_goal_year_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."savings_goal_year_seq" OWNED BY "public"."savings_goal"."year";



CREATE TABLE IF NOT EXISTS "public"."temp_transaction" (
    "id" integer NOT NULL,
    "task_id" character varying(36) NOT NULL,
    "raw_data" "text",
    "transaction_type" character varying(10),
    "amount" double precision,
    "description" character varying(200),
    "date" "date",
    "suggested_category_name" character varying(100),
    "status" character varying(50),
    "final_category_id" integer,
    "final_account_id" integer,
    "final_person" character varying(50)
);


ALTER TABLE "public"."temp_transaction" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."temp_transaction_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."temp_transaction_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."temp_transaction_id_seq" OWNED BY "public"."temp_transaction"."id";



CREATE TABLE IF NOT EXISTS "public"."transaction" (
    "id" integer NOT NULL,
    "description" character varying(200),
    "amount" double precision NOT NULL,
    "date" "date" NOT NULL,
    "is_income" boolean,
    "category_id" integer,
    "account_id" integer NOT NULL,
    "person" character varying(50) NOT NULL
);


ALTER TABLE "public"."transaction" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."transaction_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."transaction_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."transaction_id_seq" OWNED BY "public"."transaction"."id";



ALTER TABLE ONLY "public"."account" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."account_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."asset" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."asset_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."asset_category" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."asset_category_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."asset_value_history" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."asset_value_history_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."category" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."category_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."portfolio" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."portfolio_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."portfolio_snapshot" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."portfolio_snapshot_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."savings_goal" ALTER COLUMN "year" SET DEFAULT "nextval"('"public"."savings_goal_year_seq"'::"regclass");



ALTER TABLE ONLY "public"."temp_transaction" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."temp_transaction_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."transaction" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."transaction_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."account"
    ADD CONSTRAINT "account_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."account"
    ADD CONSTRAINT "account_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."asset_category"
    ADD CONSTRAINT "asset_category_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."asset_category"
    ADD CONSTRAINT "asset_category_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."asset"
    ADD CONSTRAINT "asset_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."asset_value_history"
    ADD CONSTRAINT "asset_value_history_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."category"
    ADD CONSTRAINT "category_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."category"
    ADD CONSTRAINT "category_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."import_task"
    ADD CONSTRAINT "import_task_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."portfolio"
    ADD CONSTRAINT "portfolio_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."portfolio"
    ADD CONSTRAINT "portfolio_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."portfolio_snapshot"
    ADD CONSTRAINT "portfolio_snapshot_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."savings_goal"
    ADD CONSTRAINT "savings_goal_pkey" PRIMARY KEY ("year");



ALTER TABLE ONLY "public"."temp_transaction"
    ADD CONSTRAINT "temp_transaction_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."transaction"
    ADD CONSTRAINT "transaction_pkey" PRIMARY KEY ("id");



CREATE INDEX "ix_asset_ticker" ON "public"."asset" USING "btree" ("ticker");



CREATE INDEX "ix_portfolio_snapshot_timestamp" ON "public"."portfolio_snapshot" USING "btree" ("timestamp");



ALTER TABLE ONLY "public"."asset"
    ADD CONSTRAINT "asset_asset_category_id_fkey" FOREIGN KEY ("asset_category_id") REFERENCES "public"."asset_category"("id");



ALTER TABLE ONLY "public"."asset"
    ADD CONSTRAINT "asset_portfolio_id_fkey" FOREIGN KEY ("portfolio_id") REFERENCES "public"."portfolio"("id");



ALTER TABLE ONLY "public"."asset_value_history"
    ADD CONSTRAINT "asset_value_history_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "public"."asset"("id");



ALTER TABLE ONLY "public"."portfolio_snapshot"
    ADD CONSTRAINT "portfolio_snapshot_portfolio_id_fkey" FOREIGN KEY ("portfolio_id") REFERENCES "public"."portfolio"("id");



ALTER TABLE ONLY "public"."temp_transaction"
    ADD CONSTRAINT "temp_transaction_final_account_id_fkey" FOREIGN KEY ("final_account_id") REFERENCES "public"."account"("id");



ALTER TABLE ONLY "public"."temp_transaction"
    ADD CONSTRAINT "temp_transaction_final_category_id_fkey" FOREIGN KEY ("final_category_id") REFERENCES "public"."category"("id");



ALTER TABLE ONLY "public"."temp_transaction"
    ADD CONSTRAINT "temp_transaction_task_id_fkey" FOREIGN KEY ("task_id") REFERENCES "public"."import_task"("id");



ALTER TABLE ONLY "public"."transaction"
    ADD CONSTRAINT "transaction_account_id_fkey" FOREIGN KEY ("account_id") REFERENCES "public"."account"("id");



ALTER TABLE ONLY "public"."transaction"
    ADD CONSTRAINT "transaction_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "public"."category"("id");





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";








































































































































































GRANT ALL ON TABLE "public"."account" TO "anon";
GRANT ALL ON TABLE "public"."account" TO "authenticated";
GRANT ALL ON TABLE "public"."account" TO "service_role";



GRANT ALL ON SEQUENCE "public"."account_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."account_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."account_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."asset" TO "anon";
GRANT ALL ON TABLE "public"."asset" TO "authenticated";
GRANT ALL ON TABLE "public"."asset" TO "service_role";



GRANT ALL ON TABLE "public"."asset_category" TO "anon";
GRANT ALL ON TABLE "public"."asset_category" TO "authenticated";
GRANT ALL ON TABLE "public"."asset_category" TO "service_role";



GRANT ALL ON SEQUENCE "public"."asset_category_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."asset_category_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."asset_category_id_seq" TO "service_role";



GRANT ALL ON SEQUENCE "public"."asset_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."asset_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."asset_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."asset_value_history" TO "anon";
GRANT ALL ON TABLE "public"."asset_value_history" TO "authenticated";
GRANT ALL ON TABLE "public"."asset_value_history" TO "service_role";



GRANT ALL ON SEQUENCE "public"."asset_value_history_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."asset_value_history_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."asset_value_history_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."category" TO "anon";
GRANT ALL ON TABLE "public"."category" TO "authenticated";
GRANT ALL ON TABLE "public"."category" TO "service_role";



GRANT ALL ON SEQUENCE "public"."category_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."category_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."category_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."import_task" TO "anon";
GRANT ALL ON TABLE "public"."import_task" TO "authenticated";
GRANT ALL ON TABLE "public"."import_task" TO "service_role";



GRANT ALL ON TABLE "public"."portfolio" TO "anon";
GRANT ALL ON TABLE "public"."portfolio" TO "authenticated";
GRANT ALL ON TABLE "public"."portfolio" TO "service_role";



GRANT ALL ON SEQUENCE "public"."portfolio_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."portfolio_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."portfolio_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."portfolio_snapshot" TO "anon";
GRANT ALL ON TABLE "public"."portfolio_snapshot" TO "authenticated";
GRANT ALL ON TABLE "public"."portfolio_snapshot" TO "service_role";



GRANT ALL ON SEQUENCE "public"."portfolio_snapshot_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."portfolio_snapshot_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."portfolio_snapshot_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."savings_goal" TO "anon";
GRANT ALL ON TABLE "public"."savings_goal" TO "authenticated";
GRANT ALL ON TABLE "public"."savings_goal" TO "service_role";



GRANT ALL ON SEQUENCE "public"."savings_goal_year_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."savings_goal_year_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."savings_goal_year_seq" TO "service_role";



GRANT ALL ON TABLE "public"."temp_transaction" TO "anon";
GRANT ALL ON TABLE "public"."temp_transaction" TO "authenticated";
GRANT ALL ON TABLE "public"."temp_transaction" TO "service_role";



GRANT ALL ON SEQUENCE "public"."temp_transaction_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."temp_transaction_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."temp_transaction_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."transaction" TO "anon";
GRANT ALL ON TABLE "public"."transaction" TO "authenticated";
GRANT ALL ON TABLE "public"."transaction" TO "service_role";



GRANT ALL ON SEQUENCE "public"."transaction_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."transaction_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."transaction_id_seq" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






























RESET ALL;
