import json
from pathlib import Path
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="小苏 Mock 内部 API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"


def load(filename: str) -> list[dict]:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/employees")
def list_employees(dept: str = Query(None)):
    employees = load("employees.json")
    if dept:
        employees = [e for e in employees if e["dept"] == dept]
    return employees


@app.get("/api/employees/{emp_id}")
def get_employee(emp_id: str):
    for emp in load("employees.json"):
        if emp["id"] == emp_id:
            return emp
    raise HTTPException(status_code=404, detail=f"员工 {emp_id} 不存在")


@app.get("/api/attendance")
def get_attendance(
    emp_id: str = Query(None),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
):
    records = load("attendance.json")
    if emp_id:
        records = [r for r in records if r["emp_id"] == emp_id]
    if start_date:
        records = [r for r in records if r["date"] >= start_date]
    if end_date:
        records = [r for r in records if r["date"] <= end_date]

    summary = {
        "total_days": len(records),
        "normal": sum(1 for r in records if r["status"] == "normal"),
        "late": sum(1 for r in records if r["status"] == "late"),
        "absent": sum(1 for r in records if r["status"] == "absent"),
        "overtime": sum(1 for r in records if r["status"] == "overtime"),
        "leave": sum(1 for r in records if r["status"] == "leave"),
        "records": records,
    }
    return summary


@app.get("/api/orders")
def get_orders(
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    status: str = Query(None, description="completed | pending | refunded"),
    sales_rep: str = Query(None),
):
    orders = load("orders.json")
    if start_date:
        orders = [o for o in orders if o["date"] >= start_date]
    if end_date:
        orders = [o for o in orders if o["date"] <= end_date]
    if status:
        orders = [o for o in orders if o["status"] == status]
    if sales_rep:
        orders = [o for o in orders if o["sales_rep"] == sales_rep]

    completed = [o for o in orders if o["status"] == "completed"]
    summary = {
        "total_count": len(orders),
        "completed_count": len(completed),
        "total_amount": round(sum(o["amount"] for o in completed), 2),
        "orders": orders,
    }
    return summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
