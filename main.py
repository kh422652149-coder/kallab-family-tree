from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_db_connection

app = FastAPI(title="بوابة شجرة العائلة الرقمية - Backend API")

# تفعيل الـ CORS لتوصيل الواجهة الأمامية بالخلفية بدون قيود أمنية
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/add-member/")
def add_family_member(
        first_name: str,
        spouse_name: str = None,
        parent_id: int = None,
        branch_id: int = None,
        sub_branch: str = None,
        user_role: str = "branch_admin",
        user_branch: int = None
):
    """
    إضافة عضو جديد في شجرة العائلة بحالة معلقة بانتظار المدقق.
    """
    if user_role == "branch_admin" and user_branch is not None and int(user_branch) != int(branch_id):
        raise HTTPException(
            status_code=403,
            detail="خطأ أمني: غير مسموح لك بالإضافة لفرع عائلي آخر خارج نطاق صلاحيتك!"
        )

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="فشل الاتصال بقاعدة البيانات.")

    try:
        cursor = conn.cursor()
        final_spouse = spouse_name.strip() if spouse_name and spouse_name.strip() != "" else None
        final_sub_branch = sub_branch.strip() if sub_branch and sub_branch.strip() != "" else None

        query = """
        INSERT INTO family_members (first_name, spouse_name, parent_id, branch_id, sub_branch_name, is_verified)
        VALUES (%s, %s, %s, %s, %s, FALSE) RETURNING member_id;
        """
        cursor.execute(query, (first_name.strip(), final_spouse, parent_id, branch_id, final_sub_branch))
        result = cursor.fetchone()
        new_id = result['member_id']
        conn.commit()
        return {"status": "success", "member_id": new_id,
                "message": "تم إرسال طلب الإضافة بنجاح وبانتظار تدقيق الإدارة."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء الإدخال: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.put("/edit-member/{member_id}")
def edit_member(
        member_id: int,
        first_name: str,
        spouse_name: str = None,
        parent_id: int = None,
        branch_id: int = None,
        sub_branch: str = None,
        user_role: str = "admin"
):
    """
    تحديث بيانات عضو تم إدخاله مسبقاً. مسموح فقط للمسؤول العام (أنت).
    """
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="خطأ: التعديل متاح فقط للمسؤول العام!")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="فشل الاتصال بقاعدة البيانات.")

    try:
        cursor = conn.cursor()
        final_spouse = spouse_name.strip() if spouse_name and spouse_name.strip() != "" else None
        final_sub_branch = sub_branch.strip() if sub_branch and sub_branch.strip() != "" else None

        query = """
        UPDATE family_members 
        SET first_name = %s, spouse_name = %s, parent_id = %s, branch_id = %s, sub_branch_name = %s
        WHERE member_id = %s;
        """
        cursor.execute(query, (first_name.strip(), final_spouse, parent_id, branch_id, final_sub_branch, member_id))
        conn.commit()
        return {"status": "success", "message": "تم تحديث البيانات بنجاح."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء التحديث: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.put("/verify-member/{member_id}")
def verify_member(member_id: int, user_role: str):
    """
    اعتماد بيانات الفرد المعلق ليظهر مباشرة في المخطط المفاهيمي العام للشجرة.
    """
    if user_role != "auditor" and user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="خطأ في الصلاحيات: يجب أن تكون مدققاً معتمداً أو مسؤولاً عاماً لتتمكن من الاعتماد."
        )

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="فشل الاتصال بقاعدة البيانات.")

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE family_members SET is_verified = TRUE WHERE member_id = %s;", (member_id,))
        conn.commit()
        return {"status": "success", "message": "تم الاعتماد وتثبيته في شجرة العائلة الرسمية."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء التحديث: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.delete("/delete-member/{member_id}")
def delete_member(member_id: int, user_role: str):
    """
    حذف أو رفض فرد من الشجرة.
    """
    if user_role not in ["admin", "branch_admin", "auditor"]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بإجراء عملية الحذف.")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="فشل الاتصال بقاعدة البيانات.")

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM family_members WHERE member_id = %s;", (member_id,))
        conn.commit()
        return {"status": "success", "message": "تم حذف/رفض السجل بنجاح."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء الحذف: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.get("/family-tree/")
def get_family_tree():
    """
    جلب كافة الأفراد المعتمدين والموثقين لعرضهم في المخطط المفاهيمي التفاعلي.
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT member_id as id, first_name as name, spouse_name as spouse, parent_id as parent, branch_id as branch, sub_branch_name as subbranch
            FROM family_members 
            WHERE is_verified = TRUE
            ORDER BY member_id ASC;
        """)
        members = cursor.fetchall()
        return members
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل جلب الشجرة: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.get("/pending-members/")
def get_pending_members():
    """
    جلب جميع الطلبات التي بانتظار الموافقة والاعتماد.
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT member_id as id, first_name as name, spouse_name as spouse, branch_id as branch, sub_branch_name as subbranch
            FROM family_members 
            WHERE is_verified = FALSE
            ORDER BY member_id DESC;
        """)
        pending = cursor.fetchall()
        return pending
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل جلب الطلبات المعلقة: {str(e)}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Kallab Family Tree Server on Cloud Database...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)