import jwt
import json
import base64
import os

# Read the JWT secret
with open('jwt_secret.txt', 'r') as f:
    jwt_secret = f.read().strip()

# Generate anon key
anon_payload = {
    "role": "anon",
    "iss": "supabase",
    "iat": 0,
    "exp": 9999999999
}

# Generate service role key
service_payload = {
    "role": "service_role",
    "iss": "supabase",
    "iat": 0,
    "exp": 9999999999
}

# Generate the keys
anon_key = jwt.encode(anon_payload, jwt_secret, algorithm="HS256")
service_role_key = jwt.encode(service_payload, jwt_secret, algorithm="HS256")

# Generate secret key base (32 random bytes)
secret_key_base = base64.b64encode(os.urandom(32)).decode('utf-8')

# Print all keys
print("\nGenerated Keys:")
print("==============")
print(f"JWT_SECRET={jwt_secret}")
print(f"ANON_KEY={anon_key}")
print(f"SERVICE_ROLE_KEY={service_role_key}")
print(f"SUPABASE_SERVICE_KEY={service_role_key}")
print(f"SECRET_KEY_BASE={secret_key_base}")

# Save to a file
with open('supabase_keys.txt', 'w') as f:
    f.write(f"JWT_SECRET={jwt_secret}\n")
    f.write(f"ANON_KEY={anon_key}\n")
    f.write(f"SERVICE_ROLE_KEY={service_role_key}\n")
    f.write(f"SUPABASE_SERVICE_KEY={service_role_key}\n")
    f.write(f"SECRET_KEY_BASE={secret_key_base}\n") 