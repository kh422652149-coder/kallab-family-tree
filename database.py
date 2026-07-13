import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """
    دالة الاتصال بقاعدة البيانات السحابية برابط Neon الفعلي الخاص بعائلة كلاب
    """
    try:
        conn = psycopg2.connect(
            "postgresql://neondb_owner:npg_8FamSIwYZX0V@ep-orange-breeze-atl7eaad.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require",
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ فشل الاتصال بقاعدة البيانات السحابية Neon: {str(e)}")
        return None