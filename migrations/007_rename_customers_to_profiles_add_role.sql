-- Migration: Rename customers -> profiles, add role column, drop admin_users
-- Run this in the Supabase SQL Editor BEFORE deploying backend changes.
-- This is a clean-slate migration (assumes data can be reset).

BEGIN;

-- 1. Rename table
ALTER TABLE IF EXISTS public.customers RENAME TO profiles;

-- 2. Add role column (user, seller, verified_seller, admin)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user' NOT NULL
  CHECK (role IN ('user', 'seller', 'verified_seller', 'admin'));

-- 3. Drop is_seller and seller_verified_at (replaced by role)
ALTER TABLE public.profiles DROP COLUMN IF EXISTS is_seller;
ALTER TABLE public.profiles DROP COLUMN IF EXISTS seller_verified_at;

-- 4. Drop admin_users table
DROP TABLE IF EXISTS public.admin_users CASCADE;

-- 5. Update the trigger that syncs auth.users -> profiles
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.profiles (id, email, first_name, last_name, name, is_active, role)
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
        true,
        'user'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

-- 6. Update RLS policies
DROP POLICY IF EXISTS "Users can view own customer" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own customer" ON public.profiles;
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Service role full access" ON public.profiles;

CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY "Service role full access" ON public.profiles FOR ALL USING (auth.role() = 'service_role');

-- 7. Update seller_applications.reviewed_by FK (was admin_users, now profiles)
ALTER TABLE public.seller_applications DROP CONSTRAINT IF EXISTS seller_applications_reviewed_by_fkey;

COMMIT;
