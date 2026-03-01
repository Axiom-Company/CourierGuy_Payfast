-- ============================================================
-- Run this in Supabase SQL Editor
-- Wires the existing public.customers table to auth.users
-- Safe to re-run (all statements are idempotent)
-- ============================================================

-- 1. Drop the password_hash column (Supabase Auth handles passwords now)
ALTER TABLE public.customers DROP COLUMN IF EXISTS password_hash;

-- 2. Fix country default to South Africa
ALTER TABLE public.customers ALTER COLUMN country SET DEFAULT 'ZA';

-- 3. Remove orphan customers (no matching auth.users entry)
DELETE FROM public.customers c
WHERE NOT EXISTS (SELECT 1 FROM auth.users u WHERE u.id = c.id);

-- 4. Add FK (skip if already exists)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'customers_id_fkey' AND table_name = 'customers'
    ) THEN
        ALTER TABLE public.customers
            ADD CONSTRAINT customers_id_fkey
            FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 5. Trigger: auto-create customer row on Supabase Auth signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.customers (id, email, first_name, last_name, name, is_active)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data ->> 'first_name', ''),
        COALESCE(NEW.raw_user_meta_data ->> 'last_name', ''),
        COALESCE(
            TRIM(
                COALESCE(NEW.raw_user_meta_data ->> 'first_name', '') || ' ' ||
                COALESCE(NEW.raw_user_meta_data ->> 'last_name', '')
            ),
            ''
        ),
        true
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- 6. Auto-update updated_at on customer change
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_customer_updated ON public.customers;
CREATE TRIGGER on_customer_updated
    BEFORE UPDATE ON public.customers
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 7. Row Level Security
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'customers' AND policyname = 'Users can view own customer') THEN
        CREATE POLICY "Users can view own customer" ON public.customers FOR SELECT USING (auth.uid() = id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'customers' AND policyname = 'Users can update own customer') THEN
        CREATE POLICY "Users can update own customer" ON public.customers FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'customers' AND policyname = 'Service role full access') THEN
        CREATE POLICY "Service role full access" ON public.customers FOR ALL USING (auth.role() = 'service_role');
    END IF;
END $$;
