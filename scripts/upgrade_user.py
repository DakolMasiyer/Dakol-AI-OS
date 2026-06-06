import sys
import pg8000.dbapi

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/upgrade_user.py <user_email>")
        sys.exit(1)

    email = sys.argv[1].strip()

    db_url = "aws-1-eu-central-1.pooler.supabase.com"
    user = "postgres.vlxludzuyyzefmhzruof"
    password = "9h3PTWk9PJJKCXV8"
    database = "postgres"
    port = 5432

    print(f"Connecting to database to upgrade user: {email}...")
    try:
        conn = pg8000.dbapi.connect(
            host=db_url,
            port=port,
            user=user,
            password=password,
            database=database
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # 1. Look up the user's UUID from the auth.users table
        cursor.execute("SELECT id FROM auth.users WHERE email = %s", (email,))
        auth_row = cursor.fetchone()
        
        if not auth_row:
            print(f"Error: No user found with email '{email}' in auth.users. Make sure the user has signed up via Google or email/password.")
            return

        user_id = auth_row[0]
        print(f"Found user in auth.users with ID: {user_id}")

        # 2. Check if the user exists in public.users
        cursor.execute("SELECT id FROM public.users WHERE id = %s", (user_id,))
        public_row = cursor.fetchone()

        if public_row:
            # Update existing user
            cursor.execute(
                "UPDATE public.users SET tier = 'pro', expires_at = '2030-12-31 23:59:59+00', email = %s, updated_at = NOW() WHERE id = %s",
                (email, user_id)
            )
            print(f"Success! Existing user '{email}' has been upgraded to 'pro'.")
        else:
            # Insert new user row
            cursor.execute(
                "INSERT INTO public.users (id, email, tier, daily_limit, daily_usage, expires_at, created_at, updated_at) VALUES (%s, %s, 'pro', 3, 0, '2030-12-31 23:59:59+00', NOW(), NOW())",
                (user_id, email)
            )
            print(f"Success! Created new profile row and upgraded user '{email}' to 'pro'.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
